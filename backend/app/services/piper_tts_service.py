"""
Piper TTS Service for generating German speech from text.
Uses Piper TTS with Thorsten voice (high quality male German voice).
"""

import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional
from loguru import logger

from app.core.config import settings


class PiperTTSService:
    """Service for text-to-speech using Piper."""

    def __init__(self):
        self.piper_executable = getattr(settings, 'PIPER_EXECUTABLE', 'piper')
        self.voice_model = getattr(settings, 'PIPER_VOICE_MODEL', 'de_DE-thorsten-high')
        self.output_dir = Path(getattr(settings, 'TTS_OUTPUT_DIR', './storage/tts'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Check if Piper is installed
        self._check_piper_installation()

    def _check_piper_installation(self) -> bool:
        """Check if Piper is installed and accessible."""
        try:
            result = subprocess.run(
                [self.piper_executable, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Piper TTS is installed: {result.stdout.strip()}")
                return True
            else:
                logger.warning(f"Piper TTS check failed: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error("Piper TTS executable not found. Please install Piper TTS.")
            logger.info("Installation: https://github.com/rhasspy/piper")
            return False
        except Exception as e:
            logger.error(f"Error checking Piper installation: {e}")
            return False

    async def generate_speech(
        self,
        text: str,
        output_filename: str,
        voice_model: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate speech from text using Piper TTS.

        Args:
            text: The text to convert to speech
            output_filename: Name of the output file (without path)
            voice_model: Optional voice model to use (default: Thorsten)

        Returns:
            Path to the generated audio file, or None if failed
        """
        voice = voice_model or self.voice_model
        output_path = self.output_dir / output_filename

        try:
            logger.info(f"Generating TTS audio with Piper (voice: {voice})")

            # Prepare the command
            command = [
                self.piper_executable,
                '--model', voice,
                '--output_file', str(output_path)
            ]

            # Run Piper TTS in subprocess
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send text to stdin and wait for completion
            stdout, stderr = await process.communicate(input=text.encode('utf-8'))

            if process.returncode == 0:
                logger.info(f"TTS audio generated successfully: {output_path}")
                return str(output_path)
            else:
                error_msg = stderr.decode('utf-8')
                logger.error(f"Piper TTS failed: {error_msg}")
                return None

        except Exception as e:
            logger.error(f"Error generating TTS audio: {e}")
            return None

    async def generate_nursing_documentation_audio(
        self,
        summary: str,
        services: str,
        observations: str,
        next_tasks: str,
        appointment_uuid: str
    ) -> Optional[str]:
        """
        Generate TTS audio for nursing documentation with category labels.

        Args:
            summary: Zusammenfassung
            services: Erbrachte Leistungen
            observations: Besonderheiten
            next_tasks: Aufgaben für nächsten Termin
            appointment_uuid: UUID of the appointment

        Returns:
            Path to the generated audio file
        """
        # Build the full text with category labels
        full_text = self._build_documentation_text(
            summary, services, observations, next_tasks
        )

        # Generate filename
        filename = f"nursing_doc_{appointment_uuid}.wav"

        # Generate audio
        return await self.generate_speech(full_text, filename)

    def _build_documentation_text(
        self,
        summary: str,
        services: str,
        observations: str,
        next_tasks: str
    ) -> str:
        """
        Build the full documentation text with spoken category labels.

        Args:
            summary: Zusammenfassung
            services: Erbrachte Leistungen
            observations: Besonderheiten
            next_tasks: Aufgaben für nächsten Termin

        Returns:
            Full text with category labels for TTS
        """
        parts = []

        if summary:
            parts.append(f"Zusammenfassung. {summary}")

        if services:
            parts.append(f"Erbrachte Leistungen. {services}")

        if observations:
            parts.append(f"Besonderheiten. {observations}")

        if next_tasks:
            parts.append(f"Aufgaben für den nächsten Termin. {next_tasks}")

        # Join with pauses
        return " ... ".join(parts)

    def get_status(self) -> dict:
        """Get TTS service status."""
        piper_available = self._check_piper_installation()
        return {
            "service": "Piper TTS",
            "available": piper_available,
            "voice_model": self.voice_model,
            "output_dir": str(self.output_dir),
        }


# Global service instance
piper_tts_service = PiperTTSService()
