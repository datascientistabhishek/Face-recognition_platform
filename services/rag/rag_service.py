from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import sqlite3
import time
import logging
from dotenv import load_dotenv

# Try optional imports for LangChain/FAISS/OpenAI. We'll fallback to simple LLM prompt if not available.
try:
    # Import common LangChain pieces; specific embedding classes may be imported later
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.llms import OpenAI
    from langchain.vectorstores import FAISS
    from langchain.chains import RetrievalQA
    LANGCHAIN_AVAILABLE = True
except Exception:
    LANGCHAIN_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_GENAI_AVAILABLE = True
except Exception:
    GOOGLE_GENAI_AVAILABLE = False

# Load .env file (if present)
load_dotenv()

app = FastAPI()

# Allow CORS for frontend / node proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger('rag_service')
logging.basicConfig(level=logging.INFO)

INDEX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'index_store'))
if not os.path.exists(INDEX_DIR):
    os.makedirs(INDEX_DIR, exist_ok=True)

class QueryRequest(BaseModel):
    query: str


def _get_google_api_key() -> str | None:
    return os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')


def _get_openai_key() -> str | None:
    return os.environ.get('OPENAI_API_KEY')


def get_embeddings_instance():
    """Return a LangChain embeddings instance. Prefer Google (Palm/Vertex) if configured,
    otherwise fall back to OpenAI embeddings when available.
    """
    if not LANGCHAIN_AVAILABLE:
        raise RuntimeError('LangChain not available')

    # Prefer Google embeddings if a Google API key is present
    google_key = _get_google_api_key()
    if google_key:
        # Try Google Palm embeddings (langchain wrapper) first
        try:
            from langchain.embeddings import GooglePalmEmbeddings
            return GooglePalmEmbeddings(api_key=google_key)
        except Exception:
            # Try VertexAI embeddings (requires google-cloud config)
            try:
                from langchain.embeddings import VertexAIEmbeddings
                return VertexAIEmbeddings()
            except Exception:
                logger.warning('Google embedding classes not available; falling back')

    # Fallback to OpenAI embeddings if key available
    openai_key = _get_openai_key()
    if openai_key:
        try:
            from langchain.embeddings import OpenAIEmbeddings
            return OpenAIEmbeddings(openai_api_key=openai_key)
        except Exception:
            logger.warning('OpenAIEmbeddings not available')

    raise RuntimeError('No embeddings provider available (configure GOOGLE or OPENAI keys and install required packages)')


def generate_with_gemini(prompt: str, model: str = 'gemini-2.0-flash') -> str:
    key = _get_google_api_key()
    if not key or not GOOGLE_GENAI_AVAILABLE:
        raise EnvironmentError('GEMINI_API_KEY/GOOGLE_API_KEY not set or google-genai package missing')
    try:
        genai.configure(api_key=key)
        model_obj = genai.GenerativeModel(model)
        resp = model_obj.generate_content(prompt)
        return resp.text if hasattr(resp, 'text') else str(resp)
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
    return {
        'ok': True,
        'face_db_exists': os.path.exists(FACE_DB),
        'langchain': LANGCHAIN_AVAILABLE,
        'openai': bool(_get_openai_key()),
        'google_genai': bool(_get_google_api_key()),
    }


def _build_documents(people: List[dict]) -> List[str]:
    docs = []
    for p in people:
        docs.append(f"ID: {p['id']}\nName: {p['name']}\nRegistered: {p['timestamp']}")
    return docs


@app.post('/ingest')
def ingest():
    """Ingest/index registration data from the face_recog database into a vector store.
    If LangChain + OpenAI embeddings are not available, return a simple status.
    """
    people = fetch_people_from_db()
    if not people:
        return {'status': 'no_data', 'count': 0}

    docs = _build_documents(people)

    # Try to obtain embeddings instance (prefers Google, falls back to OpenAI)
    try:
        embeddings = get_embeddings_instance()
    except Exception as e:
        logger.info('No embeddings provider available for ingest: %s', e)
        return {'status': 'ok', 'count': len(docs), 'backend': 'simple', 'message': str(e)}

    try:
        # Create FAISS index using the chosen embeddings
        # Metadata - map each doc to its person id
        metadatas = [{'id': p['id'], 'name': p['name'], 'registered_at': p['registered_at']} for p in people]

        vectorstore = FAISS.from_texts(docs, embeddings, metadatas=metadatas)
        vectorstore.save_local(INDEX_DIR)

        return {'status': 'ok', 'count': len(docs), 'backend': 'faiss'}
    except Exception as e:
        logger.exception('Failed to build vector index: %s', e)
        return {'status': 'error', 'message': str(e)}


@app.post('/query')
def query(req: QueryRequest):
    """Query the registration database using a vector retriever + LLM when available.
    Falls back to the simple prompt approach (Gemini) if vector store or LLM are not configured.
    """
    logger.info('Processing query: %s', req.query)
    people = fetch_people_from_db()
    if not people:
        return {'answer': 'No registration data available.', 'sources_count': 0, 'backend': 'none'}

    # Prefer vector search + LLM
    if LANGCHAIN_AVAILABLE:
        try:
            embeddings = get_embeddings_instance()
            if os.path.exists(os.path.join(INDEX_DIR, 'index.faiss')):
                vectorstore = FAISS.load_local(INDEX_DIR, embeddings)
            else:
                # Build on the fly if index missing
                docs = _build_documents(people)
                metadatas = [{'id': p['id'], 'name': p['name'], 'registered_at': p['registered_at']} for p in people]
                vectorstore = FAISS.from_texts(docs, embeddings, metadatas=metadatas)
                vectorstore.save_local(INDEX_DIR)

            retriever = vectorstore.as_retriever(search_type='similarity', search_kwargs={'k': 4})
            llm = OpenAI(openai_api_key=_get_openai_key(), temperature=0)
            qa = RetrievalQA.from_chain_type(llm=llm, chain_type='stuff', retriever=retriever)
            answer = qa.run(req.query)
            return {'answer': answer, 'sources_count': 4, 'backend': 'faiss+openai'}
        except Exception as e:
            logger.exception('Vector+LLM query failed, falling back: %s', e)

    # Fallback: simple prompt using Gemini if available, otherwise a local template
    try:
        last_n = people[-10:]
        docs_text = []
        for p in reversed(last_n):
            docs_text.append(f"ID: {p['id']} | Name: {p['name']} | Registered: {p['timestamp']}")
        joined = "\n".join(docs_text)

        system_prompt = "You are a friendly, helpful assistant that answers questions about face registrations. Include timestamps when asked about when people were registered. Keep responses concise and personable."
        prompt = f"{system_prompt}\n\nRegistration records:\n{joined}\n\nQuestion: {req.query}\n\nAnswer in a friendly way (one or two sentences)."

        # Prefer Gemini if configured
        if GOOGLE_GENAI_AVAILABLE and _get_google_api_key():
            answer = generate_with_gemini(prompt)
            return {'answer': answer, 'sources_count': len(last_n), 'backend': 'gemini_fallback'}

        # Final fallback: simple local heuristic
        # Example: answer simple known queries
        q = req.query.lower()
        if 'last' in q and 'registered' in q:
            last = last_n[-1] if last_n else None
            if last:
                return {'answer': f"The last registered person is {last['name']} at {last['timestamp']}", 'sources_count': 1, 'backend': 'local'}
        if 'how many' in q or 'count' in q:
            return {'answer': f"There are {len(people)} registered people.", 'sources_count': len(people), 'backend': 'local'}

        return {'answer': 'Unable to answer precisely without configured LLM/embeddings; please enable OpenAI or Gemini keys.', 'sources_count': 0, 'backend': 'local'}
    except Exception as e:
        logger.exception('Query fallback failed: %s', e)
        return {'error': 'query_failed', 'message': str(e), 'answer': ''}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8002)
