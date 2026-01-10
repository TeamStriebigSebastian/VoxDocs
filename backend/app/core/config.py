"""
Application configuration settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "VoxDocs"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default="change-me-in-production-use-strong-key")

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/voxdocs.db"

    # Storage paths
    DATA_DIR: Path = Path("./data")
    AUDIO_DIR: Path = Path("./data/audio")
    ENCRYPTED_DIR: Path = Path("./data/encrypted")
    EXPORT_DIR: Path = Path("./data/exports")
    MODEL_DIR: Path = Path("./models")

    # Encryption
    MASTER_KEY: str = Field(default="change-me-in-production-32-bytes!")
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"

    # Whisper settings
    WHISPER_MODEL: str = "small"
    WHISPER_LANGUAGE: str = "de"
    WHISPER_DEVICE: str = "cpu"

    # Processing
    BATCH_PROCESSING_HOUR: int = 2  # 2 AM
    RETENTION_DAYS: int = 90
    MAX_AUDIO_DURATION_SECONDS: int = 3600  # 1 hour max

    # Queue settings
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_CELERY: bool = False  # Use simple queue for MVP

    # Classification
    CLASSIFICATION_MODEL: str = "rule-based"  # Options: rule-based, ml-classifier, llm
    CONFIDENCE_THRESHOLD: float = 0.7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def ensure_directories():
    """Ensure all required directories exist."""
    for dir_path in [settings.DATA_DIR, settings.AUDIO_DIR, settings.ENCRYPTED_DIR,
                     settings.EXPORT_DIR, settings.MODEL_DIR, Path("./logs")]:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass  # Directory might already exist or be managed by Docker volume
