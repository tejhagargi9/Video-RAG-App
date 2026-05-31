from typing import Optional, TypedDict


class VideoRAGState(TypedDict, total=False):
    """
    State for video RAG indexing and chat workflow.
    """
    video_a_url: Optional[str]
    video_b_url: Optional[str]
    video_a_data: Optional[dict]
    video_b_data: Optional[dict]
    video_a_meta: Optional[dict]
    video_b_meta: Optional[dict]
    video_a_documents: Optional[list]
    video_b_documents: Optional[list]
    chunks_a: Optional[list]
    chunks_b: Optional[list]
    chunks_indexed: Optional[int]
    namespace: Optional[str]
    query: Optional[str]
    retrieved: Optional[list]
    response: Optional[str]