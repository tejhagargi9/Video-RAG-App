from typing import Optional
import logging

from .indexing import build_video_documents, chunk_video_documents, sanitize_metadata

logger = logging.getLogger(__name__)


def prepare_video_for_rag(transcript_response: dict, video_id: str, source: str) -> tuple[list, list[dict]]:
    """
    Prepare video transcript for RAG indexing.
    
    Args:
        transcript_response: Response from transcript_routes or instagram_routes
        video_id: The video/reel ID
        source: "youtube" or "instagram"
    
    Returns:
        Tuple of (chunked_documents, video_metadata)
    """
    # Build transcript data in expected format
    transcript_data = {
        "transcript": transcript_response.get("transcript", [])
    }
    
    # Build video metadata
    metadata = transcript_response.get("metadata", {})
    metadata["source"] = source
    
    # Sanitize metadata for Pinecone compatibility before any processing
    metadata = sanitize_metadata(metadata)
    
    # Build LangChain documents
    documents = build_video_documents(transcript_data, metadata, video_id)
    
    # Chunk documents
    chunks = chunk_video_documents(documents, video_id)
    
    return chunks, metadata


def index_videos(video_a_chunks: Optional[list], video_b_chunks: Optional[list], namespace: Optional[str] = None) -> dict:
    """
    Index both videos' chunks into vector store.
    Sanitizes all chunk metadata before indexing.
    """
    # Combine all chunks, handling None values
    all_chunks = (video_a_chunks or []) + (video_b_chunks or [])
    
    if not all_chunks:
        return {"chunks_indexed": 0, "namespace": namespace or "default"}
    
    logger.info(f"[RAG] Indexing {len(all_chunks)} total chunks")
    
    # Final safety: sanitize all chunk metadata
    for chunk in all_chunks:
        chunk.metadata = sanitize_metadata(chunk.metadata)
    
    # Import vector store here to avoid circular imports
    from .vector_store import get_vector_store
    
    vector_store = get_vector_store()
    if namespace:
        vector_store.add_documents(all_chunks, namespace=namespace)
    else:
        vector_store.add_documents(all_chunks)
    
    return {
        "chunks_indexed": len(all_chunks),
        "namespace": namespace or "default"
    }