# Face Recognition Platform - Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    React Frontend                                │   │
│  │              (http://localhost:3000)                            │   │
│  │                                                                  │   │
│  │  ┌─────────────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │ Registration Tab    │  │ Live Stream  │  │ Chat Widget  │   │   │
│  │  │ (Register faces)    │  │ (Recognize)  │  │ (Q&A)        │   │   │
│  │  └─────────────────────┘  └──────────────┘  └──────────────┘   │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                 │                                        │
│                    WebSocket & REST API Calls                            │
│                                 │                                        │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│          ┌────────────────────────────────────────────────────┐          │
│          │       Node.js Express Server                        │          │
│          │         (port 3001)                                │          │
│          │                                                    │          │
│          │  • WebSocket Handler (ws)                         │          │
│          │  • REST API Router                                │          │
│          │  • Request Proxy/Load Balancer                    │          │
│          │                                                    │          │
│          └────────────────────────────────────────────────────┘          │
│                    │                              │                      │
│    ┌───────────────┼──────────────────────────────┼───────────────┐    │
│    │               │                              │               │    │
│    ▼               ▼                              ▼               ▼    │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
                    │                              │                   
                    │                              │
┌───────────────────▼──────────────┐  ┌───────────▼────────────────────┐
│   FACE RECOGNITION SERVICE        │  │    RAG (LLM) SERVICE           │
│   (Python + FastAPI)              │  │    (Python + FastAPI)          │
│   Port: 8001                      │  │    Port: 8002                  │
├───────────────────────────────────┤  ├────────────────────────────────┤
│                                   │  │                                │
│  Endpoints:                       │  │  Endpoints:                    │
│  • POST /register                 │  │  • POST /query                 │
│  • POST /recognize                │  │  • POST /ingest                │
│  • GET /metadata/last             │  │  • GET /health                 │
│  • GET /metadata/count            │  │                                │
│  • DELETE /delete-all             │  │  Features:                     │
│                                   │  │  • Gemini AI Integration       │
│  Features:                        │  │  • Query Face Database         │
│  • Face Detection (OpenCV)        │  │  • Generate AI Responses       │
│  • Face Encoding (HOG)            │  │  • Context-aware Answers       │
│  • Face Matching (Euclidean)      │  │                                │
│  • CORS Support                   │  │  Dependencies:                 │
│                                   │  │  • google-genai                │
│  Dependencies:                    │  │  • python-dotenv               │
│  • opencv-python                  │  │  • sqlmodel                    │
│  • scipy                          │  │  • requests                    │
│  • numpy                          │  │                                │
│  • pillow                         │  │                                │
│  • sqlmodel                       │  │                                │
│                                   │  │                                │
└────────────┬──────────────────────┘  └────────────┬────────────────────┘
             │                                       │
             │                                       │
             ▼                                       ▼
    ┌─────────────────┐                    ┌──────────────────┐
    │  SQLite Database│                    │ Gemini API       │
    │  (face_encodings│                    │ (Cloud)          │
    │   .db)          │                    │                  │
    │                 │                    │ • Text Gen       │
    │ Stores:         │                    │ • Inference      │
    │ • Person ID     │                    │ • Context Aware  │
    │ • Name          │                    │                  │
    │ • Face Encoding │                    │ API Key Required:│
    │ • Registered_at │                    │ GEMINI_API_KEY   │
    │                 │                    │                  │
    └─────────────────┘                    └──────────────────┘
```

## Data Flow

### 1. **Registration Flow**
```
User Input (Image + Name)
    ↓
Frontend Form
    ↓
POST /register → Node Server (3001)
    ↓
POST /register → Face Recognition (8001)
    ↓
[OpenCV detects face] → [Extract encoding] → [Save to DB]
    ↓
Response with Person ID
    ↓
Notify RAG Service to update index
```

### 2. **Live Recognition Flow**
```
Camera/Video Frame
    ↓
WebSocket Send (frame as base64)
    ↓
Node Server receives frame
    ↓
POST /recognize → Face Recognition (8001)
    ↓
[OpenCV detects faces] → [Extract encodings] → [Compare with DB]
    ↓
[Euclidean distance matching] → [Find closest match]
    ↓
Return recognized names
    ↓
WebSocket Response to Frontend
    ↓
Display results on UI
```

### 3. **Chat/RAG Flow**
```
User Question
    ↓
Chat Widget (Frontend)
    ↓
WebSocket Send (chat message)
    ↓
Node Server receives message
    ↓
POST /query → RAG Service (8002)
    ↓
[Fetch registered people from Face DB]
    ↓
[Create context with person data]
    ↓
[Send to Gemini API with prompt]
    ↓
[Gemini generates response]
    ↓
Return answer
    ↓
WebSocket Response to Frontend
    ↓
Display chat response
```

## Technology Stack

### Frontend
- **React 18.2.0** - UI Framework
- **Socket.IO Client 4.6.1** - WebSocket communication
- **CSS** - Styling

### Backend (Node.js)
- **Express.js** - Web Framework
- **WS** - WebSocket Server
- **Axios** - HTTP Client
- **CORS** - Cross-Origin Support

### Services (Python)
- **FastAPI** - Web Framework
- **Uvicorn** - ASGI Server
- **OpenCV** - Face Detection & Processing
- **NumPy/SciPy** - Numerical Computing
- **Pillow** - Image Processing
- **SQLModel** - ORM & Database
- **Google GenAI** - LLM Integration

### Database
- **SQLite** - Lightweight SQL Database

### External APIs
- **Google Gemini** - AI/LLM

## Port Mapping

| Service | Port | Type | Protocol |
|---------|------|------|----------|
| Frontend | 3000 | React App | HTTP |
| Node Server | 3001 | Backend | HTTP/WebSocket |
| Face Recognition | 8001 | Python API | HTTP (REST) |
| RAG Service | 8002 | Python API | HTTP (REST) |

## Environment Variables

```
# RAG Service (.env in services/rag/)
GEMINI_API_KEY=your-api-key-here
```

## Key Components Explained

### Face Recognition Service
- Uses **Haar Cascade Classifier** for face detection
- Extracts **128x128 grayscale descriptors** as face encoding
- Performs **L2 normalization** on encodings
- Uses **Euclidean distance** (threshold: 0.7) for matching

### RAG Service
- Queries SQLite database directly
- Provides context from last 10 registered people
- Uses **Gemini 2.0 Flash** model for generation
- Maintains conversation context for natural responses

### Node Server
- Acts as a **proxy/gateway** between frontend and Python services
- Handles **WebSocket connections** for real-time updates
- Manages **concurrent requests** from multiple clients
- Provides **error handling and timeout management**

---

**Last Updated:** November 16, 2025
