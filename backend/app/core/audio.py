import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from faster_whisper import WhisperModel
from app.core.config import settings

# Global model instance
_model = None
_model_lock = asyncio.Lock()

def get_model():
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL} on {settings.WHISPER_DEVICE}...")
        try:
            download_root = os.path.join(settings.MODEL_DIR, "whisper")
            os.makedirs(download_root, exist_ok=True)
            
            _model = WhisperModel(
                settings.WHISPER_MODEL, 
                device=settings.WHISPER_DEVICE, 
                compute_type="int8", # Optimized for CPU/Efficiency
                download_root=download_root
            )
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    return _model

async def transcribe_audio_file(file_path: str) -> str:
    """
    Transcribes the given audio file using generic Whisper model.
    Runs in a thread pool to avoid blocking the asyncio event loop.
    Returns the full transcribed text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    logger.info(f"Starting transcription for {file_path}")
    
    loop = asyncio.get_event_loop()
    
    # Run CPU-bound task in thread pool
    try:
        segments_list = await loop.run_in_executor(None, _run_whisper, file_path)
        
        # Combine segments into full text
        full_text = " ".join([segment.text for segment in segments_list]).strip()
        logger.info(f"Transcription complete: {len(full_text)} chars")
        return full_text
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise

def _run_whisper(file_path):
    """Blocking helper for Whisper"""
    model = get_model()
    segments, info = model.transcribe(
        file_path, 
        beam_size=5,
        language=None, # Auto-detect
        task="transcribe"
    )
    # Segments is a generator, so we must iterate to actually run inference
    return list(segments)
