import os
import logging

logger = logging.getLogger(__name__)

try:
    from pinecone import Pinecone
    from langchain_pinecone import PineconeVectorStore
    from langchain_openai import OpenAIEmbeddings
    HAS_PINECONE = True
except ImportError:
    logger.warning("Pinecone/OpenAI embeddings not installed. Install with: pip install pinecone-client langchain-pinecone langchain-openai")
    HAS_PINECONE = False


_client = None
_vector_store = None


def get_vector_store():
    """
    Get or create the Pinecone vector store with OpenAI embeddings.
    """
    global _client, _vector_store

    if _vector_store is not None:
        return _vector_store

    if not HAS_PINECONE:
        raise RuntimeError("Pinecone dependencies not installed")

    # Initialize Pinecone client
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise RuntimeError("PINECONE_API_KEY environment variable not set")

    _client = Pinecone(api_key=api_key)

    # Initialize embeddings - text-embedding-3-small supports configurable dimensions
    # Set to 1024 to match existing Pinecone index
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        dimensions=1024,
    )

    # Get index
    index_name = os.getenv("PINECONE_INDEX_NAME", "videorag")
    index = _client.Index(index_name)

    # Create vector store
    _vector_store = PineconeVectorStore(
        index=index,
        embedding=embeddings,
    )

    logger.info(f"[RAG] Initialized Pinecone vector store with index={index_name}")
    return _vector_store


def reset_vector_store():
    """Reset vector store for testing."""
    global _client, _vector_store
    _vector_store = None
    _client = None