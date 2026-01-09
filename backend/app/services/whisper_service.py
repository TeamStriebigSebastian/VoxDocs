"""
Whisper transcription service.
Handles audio transcription using OpenAI Whisper model.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import whisper
import torch
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
    """Service for audio transcription using Whisper."""

    def __init__(self):
        self._model: Optional[whisper.Whisper] = None
        self._model_name = settings.WHISPER_MODEL
        self._device = settings.WHISPER_DEVICE

    def _load_model(self):
        """Load the Whisper model if not already loaded."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self._model_name}")
            start_time = time.time()

            # Determine device
            if self._device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device = self._device

            self._model = whisper.load_model(self._model_name, device=device)
            load_time = time.time() - start_time
            logger.info(f"Whisper model loaded in {load_time:.2f}s on {device}")

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

        # Transcription options
        options = {
            "task": task,
            "verbose": False,
            "word_timestamps": True,
        }

        if language:
            options["language"] = language
        else:
            options["language"] = settings.WHISPER_LANGUAGE

        # Perform transcription
        result = self._model.transcribe(str(audio_path), **options)

        processing_time = time.time() - start_time
        logger.info(f"Transcription completed in {processing_time:.2f}s")

        # Calculate average confidence from segments
        segments = result.get("segments", [])
        if segments:
            avg_confidence = sum(
                seg.get("no_speech_prob", 0) for seg in segments
            ) / len(segments)
            confidence = 1.0 - avg_confidence  # Invert no_speech_prob
        else:
            confidence = 0.0

        # Format segments
        formatted_segments = []
        for seg in segments:
            formatted_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
                "confidence": 1.0 - seg.get("no_speech_prob", 0),
                "words": seg.get("words", [])
            })

        return TranscriptionResult(
            text=result["text"].strip(),
            language=result.get("language", language or "de"),
            segments=formatted_segments,
            processing_time=processing_time,
            confidence=confidence
        )

    def transcribe_with_dental_boost(
        self,
        audio_path: Path,
        custom_vocabulary: Optional[List[str]] = None
    ) -> TranscriptionResult:
        """
        Transcribe with dental terminology boosting.

        Uses initial prompt to guide Whisper towards dental vocabulary.

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

        # Transcription options with dental prompt
        result = self._model.transcribe(
            str(audio_path),
            language=settings.WHISPER_LANGUAGE,
            task="transcribe",
            verbose=False,
            word_timestamps=True,
            initial_prompt=dental_prompt,
        )

        processing_time = time.time() - start_time
        logger.info(f"Dental transcription completed in {processing_time:.2f}s")

        # Calculate confidence
        segments = result.get("segments", [])
        confidence = 0.0
        if segments:
            avg_no_speech = sum(seg.get("no_speech_prob", 0) for seg in segments) / len(segments)
            confidence = 1.0 - avg_no_speech

        # Format segments
        formatted_segments = []
        for seg in segments:
            formatted_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
                "confidence": 1.0 - seg.get("no_speech_prob", 0),
                "words": seg.get("words", [])
            })

        return TranscriptionResult(
            text=result["text"].strip(),
            language=result.get("language", "de"),
            segments=formatted_segments,
            processing_time=processing_time,
            confidence=confidence
        )

    def _build_dental_prompt(self, custom_vocabulary: Optional[List[str]] = None) -> str:
        """Build an initial prompt with dental terminology."""
        # Common dental terms to guide transcription
        dental_terms = [
            # Tooth designations (FDI)
            "Zahn eins eins", "Zahn eins sechs", "Zahn zwei sieben", "Zahn drei acht",
            "Zahn vier sechs", "Quadrant eins", "Quadrant zwei",
            # Surfaces
            "mesial", "distal", "bukkal", "palatinal", "okklusal",
            "vestibulär", "oral", "inzisal", "approximal", "zervikal",
            # Diagnoses
            "Karies Grad eins", "Karies Grad zwei", "Karies Grad drei",
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

        # Build prompt
        prompt = "Zahnärztliche Befundung: " + ", ".join(dental_terms[:20])
        return prompt

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        self._load_model()
        return {
            "model_name": self._model_name,
            "device": str(next(self._model.parameters()).device),
            "multilingual": self._model.is_multilingual,
        }


# Global service instance
whisper_service = WhisperService()
