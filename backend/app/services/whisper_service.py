"""
Whisper transcription service.
Handles audio transcription using faster-whisper for improved performance.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from faster_whisper import WhisperModel
from loguru import logger

from app.core.config import settings


@dataclass
class TranscriptionResult:
    """Result of a transcription."""
    text: str
    language: str
    segments: List[Dict[str, Any]]
    processing_time: float
    confidence: float


class WhisperService:
    """Service for audio transcription using faster-whisper."""

    def __init__(self):
        self._model: Optional[WhisperModel] = None
        self._model_name = settings.WHISPER_MODEL
        self._device = settings.WHISPER_DEVICE

    def _load_model(self):
        """Load the faster-whisper model if not already loaded."""
        if self._model is None:
            logger.info(f"Loading faster-whisper model: {self._model_name}")
            start_time = time.time()

            # Determine device and compute type
            if self._device == "auto":
                device = "cuda" if self._is_cuda_available() else "cpu"
            else:
                device = self._device

            # Use int8 quantization on CPU for faster inference
            compute_type = "int8" if device == "cpu" else "float16"

            self._model = WhisperModel(
                self._model_name,
                device=device,
                compute_type=compute_type,
                download_root=str(settings.MODEL_DIR)
            )

            load_time = time.time() - start_time
            logger.info(f"faster-whisper model loaded in {load_time:.2f}s on {device} ({compute_type})")

    def _is_cuda_available(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> TranscriptionResult:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to the audio file
            language: Language code (e.g., "de" for German). If None, auto-detect.
            task: "transcribe" or "translate"

        Returns:
            TranscriptionResult with text and metadata
        """
        self._load_model()

        logger.info(f"Transcribing: {audio_path}")
        start_time = time.time()

        # Perform transcription
        segments_generator, info = self._model.transcribe(
            str(audio_path),
            language=language or settings.WHISPER_LANGUAGE,
            task=task,
            word_timestamps=True,
            vad_filter=True,  # Voice activity detection for better accuracy
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # Collect segments
        segments_list = list(segments_generator)
        processing_time = time.time() - start_time
        logger.info(f"Transcription completed in {processing_time:.2f}s")

        # Build full text and format segments
        full_text = ""
        formatted_segments = []
        total_confidence = 0.0

        for seg in segments_list:
            full_text += seg.text
            confidence = 1.0 - seg.no_speech_prob
            total_confidence += confidence

            formatted_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "confidence": confidence,
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in (seg.words or [])
                ]
            })

        avg_confidence = total_confidence / len(segments_list) if segments_list else 0.0

        return TranscriptionResult(
            text=full_text.strip(),
            language=info.language,
            segments=formatted_segments,
            processing_time=processing_time,
            confidence=avg_confidence
        )

    def transcribe_with_dental_boost(
        self,
        audio_path: Path,
        custom_vocabulary: Optional[List[str]] = None
    ) -> TranscriptionResult:
        """
        Transcribe with dental terminology boosting.

        Uses initial prompt to guide faster-whisper towards dental vocabulary.

        Args:
            audio_path: Path to the audio file
            custom_vocabulary: Optional list of custom dental terms

        Returns:
            TranscriptionResult with boosted dental vocabulary recognition
        """
        self._load_model()

        logger.info(f"Transcribing with dental boost: {audio_path}")
        start_time = time.time()

        # Dental-specific initial prompt to guide transcription
        dental_prompt = self._build_dental_prompt(custom_vocabulary)

        # Perform transcription with dental prompt
        segments_generator, info = self._model.transcribe(
            str(audio_path),
            language=settings.WHISPER_LANGUAGE,
            task="transcribe",
            word_timestamps=True,
            initial_prompt=dental_prompt,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=True,  # Better context handling
        )

        # Collect segments
        segments_list = list(segments_generator)
        processing_time = time.time() - start_time
        logger.info(f"Dental transcription completed in {processing_time:.2f}s")

        # Build full text and format segments
        full_text = ""
        formatted_segments = []
        total_confidence = 0.0

        for seg in segments_list:
            full_text += seg.text
            confidence = 1.0 - seg.no_speech_prob
            total_confidence += confidence

            formatted_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "confidence": confidence,
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in (seg.words or [])
                ]
            })

        avg_confidence = total_confidence / len(segments_list) if segments_list else 0.0

        return TranscriptionResult(
            text=full_text.strip(),
            language=info.language,
            segments=formatted_segments,
            processing_time=processing_time,
            confidence=avg_confidence
        )

    def _build_dental_prompt(self, custom_vocabulary: Optional[List[str]] = None) -> str:
        """Build an initial prompt with dental terminology."""
        # Common dental terms to guide transcription
        dental_terms = [
            # Tooth designations (FDI)
            "Zahn 11", "Zahn 16", "Zahn 27", "Zahn 38",
            "Zahn 46", "Quadrant 1", "Quadrant 2",
            # Surfaces
            "mesial", "distal", "bukkal", "palatinal", "okklusal",
            "vestibulär", "oral", "inzisal", "approximal", "zervikal",
            # Diagnoses
            "Karies Grad 1", "Karies Grad 2", "Karies Grad 3",
            "Parodontitis", "Pulpitis", "Gingivitis", "Periimplantitis",
            # Findings
            "Lockerungsgrad", "Taschentiefe", "Millimeter",
            "Blutung auf Sondierung", "Furkationsbefall", "Fistel",
            # Treatments
            "Wurzelkanalbehandlung", "Kavitätenpräparation", "Composite-Füllung",
            "Kronenversorgung", "Extraktion", "Implantation",
            # Materials
            "Composite", "Amalgam", "Glasionomerzement",
            "Zirkonoxid", "Guttapercha", "Artikain",
        ]

        # Add custom vocabulary if provided
        if custom_vocabulary:
            dental_terms.extend(custom_vocabulary)

        # Build prompt - faster-whisper uses this to condition the model
        prompt = "Zahnärztliche Dokumentation: " + ", ".join(dental_terms[:25])
        return prompt

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        self._load_model()
        return {
            "model_name": self._model_name,
            "device": self._device,
            "backend": "faster-whisper",
        }


# Global service instance
whisper_service = WhisperService()
