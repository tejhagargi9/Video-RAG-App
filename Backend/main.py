from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from routes.transcript_routes import router as transcript_router
from routes.instagram_routes import router as instagram_router
from rag.ingest import prepare_video_for_rag, index_videos

logger = logging.getLogger(__name__)


def _get_model():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=5000,
    )


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcript_router)
app.include_router(instagram_router)


class IngestRequest(BaseModel):
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    namespace: Optional[str] = None


@app.get("/")
def root():
    return {"message": "Hello FastAPI"}


@app.post("/ingest")
async def ingest_videos(request: IngestRequest):
    """
    Ingest two videos (YouTube + Instagram), extract transcripts and metadata,
    compute engagement rates, and index into vector DB.
    """
    if not request.youtube_url or not request.instagram_url:
        raise HTTPException(
            status_code=400,
            detail="Both youtube_url and instagram_url are required"
        )

    results = {}
    chunks_a = []
    meta_a = {}
    chunks_b = []
    meta_b = {}

    # Ingest YouTube video
    try:
        from routes.transcript_routes import extract_video_id, get_video_metadata, YouTubeTranscriptApi
        video_a_id = extract_video_id(request.youtube_url)
        ytt_api = YouTubeTranscriptApi()
        fetched_transcript = ytt_api.fetch(video_a_id)
        raw_data = fetched_transcript.to_raw_data()

        transcript_response_a = {
            "video_id": video_a_id,
            "transcript": [{"start": s.get("start", 0), "end": s.get("start", 0) + 5, "text": s.get("text", "")} for s in raw_data],
            "metadata": get_video_metadata(video_a_id) or {}
        }

        chunks_a, meta_a = prepare_video_for_rag(transcript_response_a, video_a_id, "youtube")
        results["video_a"] = {
            "video_id": video_a_id,
            "chunks": len(chunks_a),
            "engagement_rate": meta_a.get("engagement_rate"),
            "views": meta_a.get("views"),
            "likes": meta_a.get("likes"),
            "metadata": meta_a
        }
        logger.info(f"[RAG] Prepared {len(chunks_a)} chunks for YouTube video {video_a_id}")
    except Exception as e:
        logger.error(f"[RAG] Failed to process YouTube video: {e}")
        results["video_a"] = {"error": str(e)}

    # Ingest Instagram video
    try:
        from apify_client import ApifyClient
        import os

        APIFY_TOKEN = os.getenv("APIFY_TOKEN")
        if APIFY_TOKEN:
            client = ApifyClient(APIFY_TOKEN)
            # Use the working actor from instagram_routes
            run = client.actor("apple_yang/instagram-transcripts-scraper").call(
                run_input={"videoUrl": request.instagram_url}
            )
            dataset_id = run.default_dataset_id

            items = list(client.dataset(dataset_id).iterate_items())
            
            if items:
                transcript_data = items[0]
                video_b_id = transcript_data.get("code", "unknown")

                like_count = transcript_data.get("likeCount", 0)
                comment_count = transcript_data.get("commentCount", 0)
                view_count = like_count if like_count else 0

                engagement_rate = ((like_count + comment_count) / view_count) * 100 if view_count > 0 else 0

                # Use actual segments from Apify if available, otherwise fall back to full text
                segments = transcript_data.get("segments", [])
                if segments:
                    transcript_response_b = {
                        "video_url": request.instagram_url,
                        "transcript": [{"start": seg.get("start", 0), "end": seg.get("end", 0), "text": seg.get("text", "")} for seg in segments],
                        "metadata": {
                            "title": transcript_data.get("title"),
                            "username": transcript_data.get("userName"),
                            "likeCount": like_count,
                            "commentCount": comment_count,
                            "views": view_count,
                            "engagement_rate": round(engagement_rate, 2),
                            "duration": transcript_data.get("duration"),
                            "source": "instagram"
                        }
                    }
                else:
                    transcript_response_b = {
                        "video_url": request.instagram_url,
                        "transcript": [{"start": 0, "end": 5, "text": transcript_data.get("text", "")}],
                        "metadata": {
                            "title": transcript_data.get("title"),
                            "username": transcript_data.get("userName"),
                            "likeCount": like_count,
                            "commentCount": comment_count,
                            "views": view_count,
                            "engagement_rate": round(engagement_rate, 2),
                            "duration": transcript_data.get("duration"),
                            "source": "instagram"
                        }
                    }

                chunks_b, meta_b = prepare_video_for_rag(transcript_response_b, video_b_id, "instagram")
                results["video_b"] = {
                    "video_id": video_b_id,
                    "chunks": len(chunks_b),
                    "engagement_rate": meta_b.get("engagement_rate"),
                    "views": meta_b.get("views"),
                    "likes": meta_b.get("likes"),
                    "metadata": meta_b
                }
                logger.info(f"[RAG] Prepared {len(chunks_b)} chunks for Instagram reel {video_b_id}")
            else:
                results["video_b"] = {"error": "No transcript data returned from Apify"}
        else:
            results["video_b"] = {"error": "APIFY_TOKEN not configured"}
    except Exception as e:
        logger.error(f"[RAG] Failed to process Instagram video: {e}")
        results["video_b"] = {"error": str(e)}

    # Index both videos together (if any succeeded)
    all_chunks = chunks_a + chunks_b
    if all_chunks:
        index_result = index_videos(chunks_a, chunks_b, request.namespace)
        results["indexing"] = index_result

    return {
        "status": "processed",
        "results": results,
        "namespace": request.namespace
    }


class ChatRequest(BaseModel):
    query: str
    namespace: Optional[str] = None
    video_a_id: Optional[str] = None
    video_b_id: Optional[str] = None


@app.post("/chat")
async def chat_query(request: ChatRequest):
    """
    Query the vector store with separate retrievals for YouTube and Instagram.
    Uses metadata filters to retrieve chunks for each video independently.
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="query is required")

    from rag.vector_store import get_vector_store

    try:
        vector_store = get_vector_store()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector store not configured: {e}")

    video_a_chunks = []
    video_b_chunks = []

    logger.info(f"[CHAT] Received request - video_a_id: {request.video_a_id}, video_b_id: {request.video_b_id}, query: {request.query[:50]}...")

    # Retrieve YouTube video chunks (source="youtube" and video_id match)
    if request.video_a_id:
        try:
            a_docs = vector_store.similarity_search(
                request.query,
                k=5,
                filter={"video_id": request.video_a_id, "source": "youtube"},
                namespace=request.namespace
            )
            for doc in a_docs:
                video_a_chunks.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
                logger.info(f"[RAG] Video A chunk: {doc.metadata.get('video_id', 'unknown')}")
        except Exception as e:
            logger.error(f"[RAG] Failed to retrieve Video A chunks: {e}")

    # Retrieve Instagram video chunks (source="instagram" and video_id match)
    if request.video_b_id:
        try:
            b_docs = vector_store.similarity_search(
                request.query,
                k=5,
                filter={"video_id": request.video_b_id, "source": "instagram"},
                namespace=request.namespace
            )
            for doc in b_docs:
                video_b_chunks.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
                logger.info(f"[RAG] Video B chunk: {doc.metadata.get('video_id', 'unknown')}")
        except Exception as e:
            logger.error(f"[RAG] Failed to retrieve Video B chunks: {e}")

    logger.info(f"[RAG] Retrieved {len(video_a_chunks)} A chunks, {len(video_b_chunks)} B chunks for query")

    if video_a_chunks:
        logger.info(f"[RAG] Video A retrieved chunk IDs: {[doc.get('metadata', {}).get('chunk_id') for doc in video_a_chunks]}")
    if video_b_chunks:
        logger.info(f"[RAG] Video B retrieved chunk IDs: {[doc.get('metadata', {}).get('chunk_id') for doc in video_b_chunks]}")

    llm_response = None
    citations = []
    
    if video_a_chunks or video_b_chunks:
        context_parts = []
        
        for idx, chunk in enumerate(video_a_chunks):
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
            start_time = metadata.get('start_time', 0)
            end_time = metadata.get('end_time', 0)
            context_parts.append(f"[YouTube Video {request.video_a_id}]: {content}")
            citations.append({
                "video": "A",
                "label": f"A · {start_time:.0f}s-{end_time:.0f}s · chunk {idx + 1}",
                "type": "quote"
            })
        
        for idx, chunk in enumerate(video_b_chunks):
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
            start_time = metadata.get('start_time', 0)
            end_time = metadata.get('end_time', 0)
            context_parts.append(f"[Instagram Video {request.video_b_id}]: {content}")
            citations.append({
                "video": "B",
                "label": f"B · {start_time:.0f}s-{end_time:.0f}s · chunk {idx + 1}",
                "type": "quote"
            })
        
        context = "\n\n".join(context_parts)
        
        system_prompt = (
            "You are a helpful assistant answering user queries based on retrieved video transcript chunks. "
            "Use the provided context from YouTube and Instagram videos to answer the question. "
            "Be concise and reference which video the information came from when relevant."
        )
        
        try:
            llm = _get_model()
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Question: {request.query}\n\nContext:\n{context}")
            ]
            response = await llm.ainvoke(messages)
            llm_response = response.content if isinstance(response.content, str) else str(response.content)
            logger.info(f"[CHAT] LLM response generated ({len(llm_response)} chars)")
        except Exception as exc:
            logger.exception(f"[CHAT] LLM processing failed: {exc}")
            llm_response = f"Error generating response: {str(exc)}"

    return {
        "query": request.query,
        "response": llm_response,
        "citations": citations,
        "video_a_chunks": video_a_chunks,
        "video_b_chunks": video_b_chunks,
        "namespace": request.namespace
    }