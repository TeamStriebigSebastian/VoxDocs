"""
VoxDocs MCP Server Configuration

All configuration is loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """MCP Server configuration loaded from environment variables."""
    
    # Server identification
    server_name: str = Field(default="voxdocs-mcp", description="MCP server name")
    server_version: str = Field(default="0.1.0", description="Server version")
    
    # Concurrency & Timeouts
    max_concurrent_jobs: int = Field(default=2, description="Max concurrent jobs (ingestion + retrieval)")
    retrieval_timeout_sec: float = Field(default=3.0, description="Retrieval timeout in seconds")
    ingestion_timeout_sec: float = Field(default=30.0, description="Ingestion timeout in seconds")
    
    # Similarity & Retrieval
    max_distance: float = Field(default=0.3, description="Max distance for similarity (lower = more similar)")
    max_snippet_length: int = Field(default=300, description="Max snippet length in characters")
    top_k: int = Field(default=5, description="Number of results to return")
    
    # Safe Mode
    safe_mode: bool = Field(default=False, description="Enable safe mode (read-only, no tool calls)")
    
    # Retention
    retention_days_transcripts: int = Field(default=90, description="Retention days for transcripts")
    retention_days_logs: int = Field(default=365, description="Retention days for audit logs")
    
    # Paths
    chroma_persist_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")),
        description="ChromaDB persistence directory"
    )
    audit_log_path: Path = Field(
        default_factory=lambda: Path(os.getenv("AUDIT_LOG_PATH", "./logs/mcp_audit.jsonl")),
        description="Audit log file path (JSONL)"
    )
    users_db_path: Path = Field(
        default_factory=lambda: Path(os.getenv("USERS_DB_PATH", "./data/mcp_users.json")),
        description="Mock user database path (JSON)"
    )
    
    # Embedding model
    embedding_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="Sentence-Transformers model for embeddings"
    )
    
    # Ollama (for chunking / claim extraction)
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    ollama_model: str = Field(default="qwen3:8b", description="Ollama model for text processing")
    
    # ChromaDB collection
    chroma_collection_name: str = Field(default="voxdocs_chunks", description="ChromaDB collection name")
    
    class Config:
        env_prefix = "MCP_"
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
