from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import os
import sqlite3
import time
import logging
from google import genai
from dotenv import load_dotenv

# Load .env file (if present) so GEMINI_API_KEY can be set in development
load_dotenv()

app = FastAPI()

logger = logging.getLogger('rag_service')
logging.basicConfig(level=logging.INFO)

class QueryRequest(BaseModel):
    query: str


def _get_google_api_key() -> str | None:
    return os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')


def generate_with_gemini(prompt: str, model: str = 'gemini-2.0-flash') -> str:
    key = _get_google_api_key()
    if not key:
        raise EnvironmentError('GEMINI_API_KEY or GOOGLE_API_KEY not set')
    try:
        client = genai.Client()
        resp = client.models.generate_content(model=model, contents=prompt)
        # response may expose `text` or `candidates` depending on client version
        out = None
        if hasattr(resp, 'text') and resp.text:
            out = resp.text
        elif hasattr(resp, 'candidates') and resp.candidates:
            cand = resp.candidates[0]
            out = getattr(cand, 'content', None) or str(cand)
        else:
            # fallback to raw dict
            try:
                j = resp.to_dict()
                if 'candidates' in j and j['candidates']:
                    out = j['candidates'][0].get('content')
                else:
                    out = j.get('content')
            except Exception:
                out = str(resp)
        return out or ''
    except Exception as e:
        logger.exception('Error calling Gemini: %s', e)
        return f'Error: {str(e)}'


# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Assume face_recog DB is at ../face_recog/db/face_encodings.db
FACE_DB = os.path.abspath(os.path.join(BASE_DIR, '..', 'face_recog', 'db', 'face_encodings.db'))


def fetch_people_from_db() -> List[dict]:
    """Read registration metadata directly from face_recog sqlite DB.
    Returns list of dicts with keys: id, name, registered_at, timestamp
    """
    if not os.path.exists(FACE_DB):
        logger.warning('Face DB not found at %s', FACE_DB)
        return []
    try:
        conn = sqlite3.connect(FACE_DB)
        cur = conn.cursor()
        # Try common table name 'person' used by SQLModel
        cur.execute("SELECT id, name, registered_at FROM person ORDER BY registered_at ASC")
        rows = cur.fetchall()
        conn.close()
        
        from datetime import datetime
        result = []
        for r in rows:
            timestamp_readable = datetime.fromtimestamp(r[2]).strftime('%Y-%m-%d %H:%M:%S')
            result.append({
                'id': r[0], 
                'name': r[1], 
                'registered_at': r[2],
                'timestamp': timestamp_readable
            })
        return result
    except Exception as e:
        logger.error('Error reading DB: %s', e)
        return []


@app.get('/health')
def health():
    return {'ok': True, 'face_db_exists': os.path.exists(FACE_DB)}


@app.post('/ingest')
def ingest():
    """Ingest/index registration data from the face_recog database.
    This is a simplified version that just ensures the DB is accessible.
    """
    people = fetch_people_from_db()
    if not people:
        return {'status': 'no_data', 'count': 0}
    return {'status': 'ok', 'count': len(people), 'backend': 'simple'}


@app.post('/query')
def query(req: QueryRequest):
    """Query the registration database and use Gemini to answer questions.
    """
    logger.info('Processing query: %s', req.query)
    people = fetch_people_from_db()
    
    if not people:
        return {'answer': 'No registration data available.', 'sources_count': 0, 'backend': 'simple'}
    
    # Use the most recent entries as context
    last_n = people[-10:]
    docs_text = []
    for p in reversed(last_n):
        docs_text.append(f"ID: {p['id']} | Name: {p['name']} | Registered: {p['timestamp']}")
    joined = "\n".join(docs_text)
    
    system_prompt = "You are a friendly, helpful assistant that answers questions about face registrations. Include timestamps when asked about when people were registered. Keep responses concise and personable."
    prompt = f"{system_prompt}\n\nRegistration records:\n{joined}\n\nQuestion: {req.query}\n\nAnswer in a friendly way (one or two sentences)."
    
    try:
        answer = generate_with_gemini(prompt)
        return {'answer': answer, 'sources_count': len(last_n), 'backend': 'simple'}
    except Exception as e:
        logger.exception('Query failed: %s', e)
        return {'error': 'query_failed', 'message': str(e), 'answer': ''}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8002)
