from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
from typing import Any

logger = logging.getLogger(__name__)


def sanitize_metadata(metadata: dict) -> dict:
    """
    Sanitize metadata to be Pinecone-compatible.
    
    Replaces None values with safe defaults:
    - string fields → ""
    - list fields (including hashtags) → []
    - numeric fields → 0
    - boolean fields → False
    
    Logs which fields were sanitized.
    """
    sanitized = {}
    sanitized_fields = []
    
    for key, value in metadata.items():
        if value is None:
            # Default to 0 for numeric fields, "" for strings, [] for lists
            # We'll detect based on typical field names
            if key in ("hashtags",):
                sanitized[key] = []
                sanitized_fields.append(f"{key}: None → []")
            elif key in ("views", "likes", "comments", "engagement_rate", "duration", "start_time", "end_time"):
                sanitized[key] = 0
                sanitized_fields.append(f"{key}: None → 0")
            else:
                sanitized[key] = ""
                sanitized_fields.append(f"{key}: None → ''")
        elif isinstance(value, list):
            # Ensure list contains only strings
            sanitized[key] = [str(v) if v is not None else "" for v in value]
            sanitized_fields.append(f"{key}: list (sanitized for None elements)")
        else:
            sanitized[key] = value
    
    if sanitized_fields:
        logger.info(f"[RAG] Sanitized metadata fields: {', '.join(sanitized_fields)}")
    
    return sanitized


def build_video_documents(transcript_data: dict, video_meta: dict, video_id: str) -> list[Document]:
    """
    Convert transcript data into LangChain Document objects with video metadata.

    Expected input format:
    {
        "transcript": [{"text": "...", "start": 0.0, "end": 5.0}, ...],
        "metadata": {...}  # from YouTube or Instagram
    }
    """
    logger.info(f"[RAG] Building documents for video_id={video_id}")

    transcript = transcript_data.get("transcript", [])
    if not transcript:
        logger.warning(f"[RAG] No transcript found for video_id={video_id}")
        return []

    # Build segments into a single text with timestamps for chunking
    segments = []
    for i, seg in enumerate(transcript):
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "")
        if text:
            segments.append({
                "start_time": start,
                "end_time": end,
                "text": text,
            })

    if not segments:
        logger.warning(f"[RAG] No valid segments for video_id={video_id}")
        return []

    # Create document content with timestamps for each segment
    document_content = "\n".join(
        f"[{s['start_time']:.1f}s-{s['end_time']:.1f}s] {s['text']}"
        for s in segments
    )

    # Build metadata for the document
    raw_metadata = {
        "video_id": video_id,
        "video_title": video_meta.get("title"),
        "creator": video_meta.get("channel_title") or video_meta.get("username"),
        "views": video_meta.get("view_count") or video_meta.get("views"),
        "likes": video_meta.get("like_count") or video_meta.get("likes"),
        "comments": video_meta.get("comment_count") or video_meta.get("comments"),
        "engagement_rate": video_meta.get("engagement_rate"),
        "upload_date": video_meta.get("published_at") or video_meta.get("created_at"),
        "duration": video_meta.get("duration"),
        "hashtags": video_meta.get("tags") or video_meta.get("hashtags"),
        "source": video_meta.get("source"),
    }

    # Sanitize metadata for Pinecone compatibility
    metadata = sanitize_metadata(raw_metadata)

    doc = Document(page_content=document_content, metadata=metadata)
    logger.info(f"[RAG] Created document for video_id={video_id} with {len(segments)} segments")

    return [doc]


def chunk_video_documents(documents: list[Document], video_id: str) -> list[Document]:
    """
    Chunk video documents while preserving timestamp metadata.
    Uses smaller chunks for short-form videos.
    """
    if not documents:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        add_start_index=True,
        separators=["\n"],
    )

    all_splits = []
    for doc in documents:
        splits = text_splitter.split_documents([doc])
        for i, split in enumerate(splits):
            # Extract timestamps from the split content
            content = split.page_content
            lines = content.split("\n")
            if lines:
                first_line = lines[0]
                # Parse timestamp from first line like "[0.0s-5.0s] text..."
                import re
                match = re.search(r'\[(\d+\.?\d*)s-(\d+\.?\d*)s\]', first_line)
                if match:
                    split.metadata["start_time"] = float(match.group(1))
                    split.metadata["end_time"] = float(match.group(2))
                else:
                    split.metadata["start_time"] = doc.metadata.get("start_time", 0)
                    split.metadata["end_time"] = doc.metadata.get("end_time", 0)
            split.metadata["chunk_id"] = f"{video_id}_chunk_{i + 1}"
            
            # Sanitize chunk metadata as well
            split.metadata = sanitize_metadata(split.metadata)
            all_splits.append(split)

    logger.info(f"[RAG] Chunked video_id={video_id} into {len(all_splits)} chunks")
    return all_splits