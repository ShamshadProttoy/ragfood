"""Custom exception types for the RAG-Food system."""


class RAGError(Exception):
    """Base exception for RAG operations."""


class EmbeddingError(RAGError):
    """Embedding generation failed."""


class VectorDBError(RAGError):
    """Vector database operation failed."""
