from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import requests
import threading
from pydantic import BaseModel
import base64, io, os, time
from sqlmodel import SQLModel, Field, Session, create_engine, select
import numpy as np
from typing import List
import cv2
from PIL import Image
from scipy import spatial
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = 'db/face_encodings.db'
if not os.path.exists('db'):
    os.makedirs('db')

engine = create_engine(f'sqlite:///{DB_PATH}')

class Person(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    encoding: bytes
    registered_at: float

SQLModel.metadata.create_all(engine)

# Load OpenCV face cascade classifier
cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

def get_face_descriptor(image_array, face_rect):
    """Extract a simple face descriptor from an image using HOG-like features"""
    x, y, w, h = face_rect
    face_roi = image_array[y:y+h, x:x+w]
    
    # Resize to 128x128 for consistent encoding
    face_roi = cv2.resize(face_roi, (128, 128))
    
    # Convert to grayscale
    if len(face_roi.shape) == 3:
        face_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    
    # Normalize and flatten
    face_descriptor = face_roi.astype(np.float32) / 255.0
    face_descriptor = face_descriptor.flatten()
    
    # L2 normalize the descriptor
    norm = np.linalg.norm(face_descriptor)
    if norm > 0:
        face_descriptor = face_descriptor / norm
    
    return face_descriptor

class RegisterRequest(BaseModel):
    name: str
    image: str  # base64

@app.post('/register')
def register(req: RegisterRequest):
    try:
        # decode image
        header, b64 = req.image.split(',', 1) if req.image.startswith('data:') else (None, req.image)
        img_bytes = base64.b64decode(b64)
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        
        # Detect faces
        boxes = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(boxes) == 0:
            return {'error': 'no_face_detected'}
        
        # Get descriptor for the first face
        x, y, w, h = boxes[0]
        encoding = get_face_descriptor(arr, (x, y, w, h))
        
        # store
        with Session(engine) as session:
            p = Person(name=req.name, encoding=encoding.tobytes(), registered_at=time.time())
            session.add(p)
            session.commit()
            session.refresh(p)
        
        # Notify RAG service to rebuild index (non-blocking)
        def _notify_rag():
            try:
                requests.post('http://localhost:8002/ingest', timeout=10)
            except Exception:
                pass

        try:
            threading.Thread(target=_notify_rag, daemon=True).start()
        except Exception:
            pass

        return {'id': p.id, 'name': p.name}
    except Exception as e:
        return {'error': str(e)}

class RecognizeRequest(BaseModel):
    image: str

@app.post('/recognize')
def recognize(req: RecognizeRequest):
    try:
        header, b64 = req.image.split(',', 1) if req.image.startswith('data:') else (None, req.image)
        img_bytes = base64.b64decode(b64)
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        
        # Detect faces
        boxes = face_cascade.detectMultiScale(gray, 1.3, 5)
        logger.info(f"Detected {len(boxes)} faces")
        
        results = []
        with Session(engine) as session:
            people = session.exec(select(Person)).all()
            logger.info(f"Found {len(people)} registered people")
            
            for i, (x, y, w, h) in enumerate(boxes):
                enc = get_face_descriptor(arr, (x, y, w, h))
                logger.info(f"Face {i}: descriptor size = {len(enc)}")
                name = 'Unknown'
                
                if people:
                    # Calculate distances to all known faces
                    min_distance = float('inf')
                    best_match_idx = -1
                    
                    for idx, person in enumerate(people):
                        try:
                            known_enc = np.frombuffer(person.encoding, dtype=np.float32)
                            logger.info(f"Person {idx} ({person.name}): stored descriptor size = {len(known_enc)}")
                            
                            # Ensure sizes match before comparing
                            if len(known_enc) != len(enc):
                                logger.warning(f"Size mismatch for {person.name}: {len(known_enc)} vs {len(enc)}")
                                continue
                            
                            distance = spatial.distance.euclidean(enc, known_enc)
                            logger.info(f"Distance to {person.name}: {distance:.4f}")
                            
                            if distance < min_distance:
                                min_distance = distance
                                best_match_idx = idx
                        except Exception as match_err:
                            logger.error(f"Error comparing with {person.name}: {match_err}")
                            continue
                    
                    # Use a threshold for recognition (0.7 is a reasonable threshold for normalized descriptors)
                    if best_match_idx >= 0 and min_distance < 0.7:
                        name = people[best_match_idx].name
                        logger.info(f"Recognized as {name} with distance {min_distance:.4f}")
                
                results.append({'box': [int(x), int(y), int(w), int(h)], 'name': name})
        
        return {'results': results}
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}"
        logger.error(f"Recognition error: {error_msg}\n{traceback.format_exc()}")
        return {'error': error_msg, 'results': []}

@app.get('/metadata/last')
def last_registered():
    with Session(engine) as session:
        r = session.exec(select(Person).order_by(Person.registered_at.desc()).limit(1)).first()
        if not r:
            return {'none': True}
        return {'id': r.id, 'name': r.name, 'registered_at': r.registered_at}

@app.get('/metadata/count')
def count():
    with Session(engine) as session:
        c = session.exec(select(Person)).all()
        return {'count': len(c)}
