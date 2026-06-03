# Video-RAG-App

A small full-stack application that demonstrates Retrieval-Augmented Generation (RAG) for short-form video content (YouTube + Instagram). The backend ingests video transcripts, converts them into chunked documents, indexes them into a Pinecone vector store using OpenAI embeddings, and exposes endpoints to ingest videos and query them using an LLM. The frontend is a React + TypeScript app (Vite) that provides a simple UI for submitting video URLs and opening a chat interface.

## Repository layout

- Backend/
  - main.py - FastAPI application entrypoint (includes `/ingest` and `/chat` endpoints)
  - requirements.txt - Python dependencies
  - vercel.json - Vercel build configuration for deploying the backend
  - rag/ - RAG helper modules
    - indexing.py - converts transcripts into LangChain Documents and chunks them
    - ingest.py - high-level helpers to prepare and index videos
    - models.py - Pydantic models for video metadata
    - state.py - typed dict describing runtime state
    - vector_store.py - Pinecone vector store wiring using OpenAI embeddings
  - routes/ - API routes
    - transcript_routes.py - YouTube transcript + metadata endpoints (and Apify actor wrapper)
    - instagram_routes.py - Instagram transcript wrapper using an Apify actor

- Frontend/
  - package.json - Node dependencies and scripts
  - src/ - React + TypeScript source
    - App.tsx - main UI and ingestion flow
    - components/ - UI components (VideoURLInput, Sidebar, Chat page, etc.)

## High-level flow

1. Frontend collects a YouTube URL and an Instagram URL and generates a session namespace.
2. Frontend calls POST /ingest on the backend with both URLs and the namespace.
3. Backend extracts transcripts (YouTube via `youtube-transcript-api` or Apify; Instagram via Apify actor), computes simple engagement metrics, builds LangChain Documents, chunks them, and indexes them into Pinecone.
4. User can then query the `/chat` endpoint (used by the frontend) to retrieve relevant chunks from Pinecone and ask an LLM to produce a concise answer with citations.

## Requirements

- Python 3.10+ recommended for the backend (check compatibility with your environment and `requirements.txt`).
- Node.js 18+ for the frontend (Vite + React).
- The project expects API keys and tokens for external services (OpenAI, Pinecone, YouTube Data API, Apify).

## Important environment variables

Backend expects the following environment variables (set them before running the backend):

- PINECONE_API_KEY - API key for Pinecone (required if you use Pinecone vector store)
- PINECONE_INDEX_NAME - (optional) Pinecone index name, defaults to `videorag`
- APIFY_TOKEN - Apify API token (required for Instagram and some YouTube Apify-based endpoints)
- YOUTUBE_API_KEY - (optional) YouTube Data API key for richer metadata
- OPENAI_API_KEY (or other provider credentials used by langchain-openai / ChatOpenAI) - required for embeddings and LLM calls

Note: The backend uses `langchain-openai` and `langchain-core` packages and constructs a ChatOpenAI model instance in `main.py`. Ensure your OpenAI-compatible credentials are available to the environment as expected by `langchain-openai`.

## Local development — Backend (Windows cmd.EXE)

1. Create and activate a virtual environment (Windows cmd):

```bat
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies:

```bat
pip install -r Backend\requirements.txt
```

3. Set required environment variables (example):

```bat
set PINECONE_API_KEY=your_pinecone_key
set PINECONE_INDEX_NAME=videorag
set APIFY_TOKEN=your_apify_token
set YOUTUBE_API_KEY=your_youtube_key
set OPENAI_API_KEY=your_openai_key
```

4. Run the FastAPI server (recommended using Uvicorn):

```bat
cd Backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will expose endpoints (see below) on http://127.0.0.1:8000 by default.

## Local development — Frontend

1. Install dependencies and run the dev server (Windows cmd):

```bat
cd Frontend
npm install
npm run dev
```

2. By default the frontend expects the backend API to be available at `VITE_API_URL` (in `App.tsx` it falls back to `http://127.0.0.1:8000`). You can create a `.env` file in `Frontend/` with `VITE_API_URL=http://127.0.0.1:8000`.

## API endpoints (Backend)

- GET / - health check
- POST /ingest - Body: { youtube_url: string, instagram_url: string, namespace?: string }
  - Ingests both videos, extracts transcripts & metadata, prepares chunks and indexes them to Pinecone under the provided namespace (or default).
  - Returns a summary with chunk counts, metadata and any errors encountered.

- POST /chat - Body: { query: string, namespace?: string, video_a_id?: string, video_b_id?: string }
  - Runs a similarity search against the vector store for chunks matching the supplied video IDs and namespace, constructs context and calls the configured LLM (ChatOpenAI) to produce an answer along with citations.

- GET /transcript/{video_path} - Fetches YouTube transcript using `youtube-transcript-api` (or treated as a video ID).
- GET /youtube-transcript-apify/{video_path} - Uses Apify actor to fetch YouTube transcript (requires APIFY_TOKEN)
- GET /instagram-transcript/{video_path} - Uses Apify actor `apple_yang/instagram-transcripts-scraper` to retrieve Instagram transcript and metadata (requires APIFY_TOKEN)

(See `Backend/routes/*.py` for the implementation details and expected output shapes.)

## Notes, caveats and troubleshooting

- Apify: Several routes rely on Apify actors. You must set `APIFY_TOKEN` in your environment for those routes to work. If missing, the app logs a warning and returns an error when those endpoints are called.

- Pinecone: `Backend/rag/vector_store.py` expects the Pinecone client to be available and the index to exist. Create an index in Pinecone with appropriate dimensions (the code uses text-embedding-3-small with 1024 dims). If you prefer another vector DB, you can swap the implementation in `vector_store.py`.

- OpenAI / LLM: `main.py` constructs a `ChatOpenAI` instance with `model='gpt-4o-mini'`. Make sure your credentials support the selected model. You can replace model name and settings in `_get_model()`.

- YouTube Data API: Without `YOUTUBE_API_KEY`, metadata fetch will be skipped (the transcript alone is still fetched by `youtube-transcript-api`).

- Local testing: The frontend stores a generated session namespace in `localStorage` and persists ingest results there. After a successful ingest, click "Open Chat" to navigate to the chat UI.

## Potential improvements (short list)

- Add a small integration test verifying /ingest → index → /chat flow with a mocked vector store and LLM.
- Add Dockerfiles and docker-compose for reproducible local development (Pinecone can be mocked with a local vector DB for tests).
- Add a sample .env.example file with the required env variables (PINECONE_API_KEY, APIFY_TOKEN, YOUTUBE_API_KEY, OPENAI_API_KEY).

## Where to look in the code

- Backend main app: `Backend/main.py`
- Transcript handling: `Backend/routes/transcript_routes.py`
- Instagram Apify wrapper: `Backend/routes/instagram_routes.py`
- Document building & chunking: `Backend/rag/indexing.py`
- Indexing & ingestion helpers: `Backend/rag/ingest.py`
- Pinecone wiring: `Backend/rag/vector_store.py`
- Frontend main: `Frontend/src/App.tsx`
