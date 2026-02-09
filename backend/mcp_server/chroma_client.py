"""
ChromaDB Client for VoxDocs MCP Server

Persistent vector database for chunk storage and retrieval.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from .config import get_settings
from .models import ChunkMetadata, SourceType


class ChromaClient:
    """
    ChromaDB persistent client wrapper.
    
    Handles:
    - Collection management
    - Metadata schema enforcement
    - Vector storage and retrieval
    """
    
    def __init__(self, persist_dir: Optional[Path] = None):
        settings = get_settings()
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = settings.chroma_collection_name
        
        # Ensure directory exists
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize persistent client
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=False,  # No resets in production
            )
        )
        
        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine distance
        )
    
    @property
    def collection(self):
        """Get the ChromaDB collection."""
        return self._collection
    
    def add_chunks(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> list[str]:
        """
        Add chunks to the collection.
        
        Args:
            texts: Chunk texts
            embeddings: Pre-computed embeddings
            metadatas: Metadata for each chunk (must include required fields)
            
        Returns:
            List of generated chunk IDs
        """
        # Generate UUIDs for each chunk
        ids = [str(uuid.uuid4()) for _ in texts]
        
        # Add timestamp if not present
        now = datetime.now(timezone.utc).isoformat()
        for meta in metadatas:
            if "created_at" not in meta:
                meta["created_at"] = now
            meta["chunk_id"] = ids[metadatas.index(meta)]
        
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        
        return ids
    
    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
        max_distance: Optional[float] = None,
    ) -> dict:
        """
        Query the collection with a vector.
        
        Args:
            query_embedding: Query vector
            n_results: Number of results to return
            where: Filter conditions (e.g., {"case_id": "123"})
            max_distance: Maximum distance threshold
            
        Returns:
            Query results with ids, documents, distances, metadatas
        """
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "distances", "metadatas"],
        )
        
        # Filter by max_distance if specified
        if max_distance is not None and results["distances"]:
            filtered_ids = []
            filtered_docs = []
            filtered_distances = []
            filtered_metadatas = []
            
            for i, distance in enumerate(results["distances"][0]):
                if distance <= max_distance:
                    filtered_ids.append(results["ids"][0][i])
                    filtered_docs.append(results["documents"][0][i])
                    filtered_distances.append(distance)
                    filtered_metadatas.append(results["metadatas"][0][i])
            
            return {
                "ids": [filtered_ids],
                "documents": [filtered_docs],
                "distances": [filtered_distances],
                "metadatas": [filtered_metadatas],
            }
        
        return results
    
    def get_by_case_id(self, case_id: str, limit: int = 100) -> dict:
        """Get all chunks for a case (for admin/metrics only)."""
        return self._collection.get(
            where={"case_id": case_id},
            limit=limit,
            include=["documents", "metadatas"],
        )
    
    def count(self) -> int:
        """Get total number of chunks in collection."""
        return self._collection.count()
    
    def delete_by_case_id(self, case_id: str) -> None:
        """Delete all chunks for a case (for retention/purge)."""
        # Get IDs first
        results = self._collection.get(
            where={"case_id": case_id},
            include=[],
        )
        if results["ids"]:
            self._collection.delete(ids=results["ids"])


# Global client instance
_chroma_client: Optional[ChromaClient] = None


def get_chroma_client() -> ChromaClient:
    """Get the global ChromaDB client instance."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = ChromaClient()
    return _chroma_client
