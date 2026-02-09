"""
Embeddings Pipeline for VoxDocs MCP Server

Local embedding generation using Sentence-Transformers.
"""

from typing import Optional
from sentence_transformers import SentenceTransformer

from .config import get_settings


class EmbeddingPipeline:
    """
    Sentence-Transformers embedding pipeline.
    
    Loads model once and provides encoding for queries and documents.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._model: Optional[SentenceTransformer] = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        Encode texts to embeddings.
        
        Args:
            texts: List of text strings to encode
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def encode_query(self, query: str) -> list[float]:
        """
        Encode a single query.
        
        Args:
            query: Query string
            
        Returns:
            Embedding vector
        """
        embedding = self.model.encode([query], convert_to_numpy=True)
        return embedding[0].tolist()
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        return self.model.get_sentence_embedding_dimension()


# Global pipeline instance
_embedding_pipeline: Optional[EmbeddingPipeline] = None


def get_embedding_pipeline() -> EmbeddingPipeline:
    """Get the global embedding pipeline instance."""
    global _embedding_pipeline
    if _embedding_pipeline is None:
        _embedding_pipeline = EmbeddingPipeline()
    return _embedding_pipeline
