# Face Recognition Platform with Real-Time AI Q&A (RAG)

This repository contains a scaffold for a browser-based face recognition platform with real-time recognition and a Retrieval-Augmented Generation (RAG) chat interface.

Goal
- Register faces via webcam
- Recognize faces in real-time (multi-face)
- Provide a chat-based query interface powered by RAG (LangChain + FAISS + LLM)

Project layout
- `frontend/` — React app (Registration, Live Recognition, Chat widget)
- `server/` — Node.js WebSocket/REST server to coordinate frontend and Python services
- `services/face_recog` — FastAPI face-recognition service (registration, recognition)
- `services/rag` — FastAPI RAG service using LangChain + FAISS + LLM
- `db/` — SQLite file storage for encodings and metadata
- `docs/` — architecture diagrams and demo assets

Quick setup (development)

1) Python services (in separate terminals)

```powershell
cd "c:/Users/asus/Desktop/face recog/services/face_recog"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

```powershell
cd "c:/Users/asus/Desktop/face recog/services/rag"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn rag_service:app --reload --port 8002
```
2) Python services (in separate terminals)

- Face recognition service
```powershell
cd "c:/Users/asus/Desktop/face recog/services/face_recog"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

- RAG service (Gemini / Google GenAI)
```powershell
cd "c:/Users/asus/Desktop/face recog/services/rag"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Set your Google GenAI / Gemini API key in the environment before running
# In PowerShell (current session):
$env:GEMINI_API_KEY = 'AIzaSyC43rODAQRe3IjAP7XgumyOrMZSKXmDrg0'
# Or set permanently:
setx GEMINI_API_KEY "AIzaSyC43rODAQRe3IjAP7XgumyOrMZSKXmDrg0"
uvicorn rag_service:app --reload --port 8002
```

2) Node server
```powershell
cd "c:/Users/asus/Desktop/face recog/server"
npm install
node index.js
```

3) Frontend
```powershell
cd "c:/Users/asus/Desktop/face recog/frontend"
npm install
npm start
```

Assumptions
- You have Python 3.10+, Node.js 18+, and npm installed.
- You will provide LLM API keys (OpenAI or other) for RAG.

Next steps
- Implement services and frontend components
- Add architecture diagram to `docs/`
- Add demo video and logging

"`Note:"` This is scaffolding with placeholders. See subfolders for starter files and further instructions.
