"""
LLM Service for nursing care transcription correction and categorization.
Supports both Ollama (local, GDPR-compliant) and OpenAI API.
"""

import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from app.core.config import settings


@dataclass
class NursingAnalysis:
    """Result of LLM analysis of nursing care transcription."""
    corrected_text: str
    summary: str  # Gesamte Aufnahme/Zusammenfassung
    services: str  # Erbrachte Leistungen
    observations: str  # Besonderheiten
    next_tasks: str  # Aufgaben für nächsten Termin
    processing_time: float


# System prompt for nursing care analysis
NURSING_SYSTEM_PROMPT = """Du bist ein spezialisierter Assistent für Pflegedokumentation.
Deine Aufgaben:
1. Korrigiere Transkriptionsfehler bei pflegerischen Fachbegriffen
2. Kategorisiere die Inhalte nach den vorgegebenen Kategorien
3. Übersetze alles ins Deutsche (falls in anderer Sprache)

WICHTIGE PFLEGEFACHBEGRIFFE:
- Körperpflege: Ganzkörperwäsche, Teilwäsche, Intimpflege, Mundpflege, Rasur, Haarwäsche, Nagelpflege
- Mobilisation: Lagewechsel, Positionierung, Transfer, Gehen, Sitzen, Stehen, Thromboseprophylaxe
- Medikamentengabe: Medikation, Tabletten, Tropfen, Salbe, Injektion, Pflaster
- Vitalzeichen: Blutdruck, Puls, Temperatur, Atmung, Sauerstoffsättigung, Blutzucker
- Ernährung: Essen anreichen, Trinken anbieten, Sondenkost, PEG, Flüssigkeitsbilanz
- Ausscheidung: Inkontinenzversorgung, Katheter, Toilettengang, Stuhlgang, Windel wechseln
- Wundversorgung: Verbandswechsel, Dekubitus, Wundkontrolle, Wundreinigung
- Beobachtungen: Allgemeinzustand, Schmerzen, Hautkolorit, Bewusstseinslage, Orientierung

KATEGORIEN:
1. Gesamte Aufnahme/Zusammenfassung: Überblick über den gesamten Pflegeeinsatz
2. Erbrachte Leistungen: Alle durchgeführten pflegerischen Tätigkeiten (z.B. Körperpflege, Mobilisation, Medikamentengabe)
3. Besonderheiten: Auffälligkeiten, Veränderungen, besondere Vorkommnisse
4. Aufgaben für nächsten Termin: Was beim nächsten Besuch zu beachten ist

Antworte IMMER im folgenden JSON-Format:
{
  "corrected_text": "Der korrigierte vollständige Text auf Deutsch",
  "summary": "Zusammenfassung des Pflegeeinsatzes in 2-3 Sätzen",
  "services": "Detaillierte Auflistung aller erbrachten Leistungen",
  "observations": "Besonderheiten und Auffälligkeiten",
  "next_tasks": "Aufgaben und Hinweise für den nächsten Termin"
}"""


class NursingLLMService:
    """Service for LLM-based nursing care text analysis."""

    def __init__(self):
        self._ollama_available: Optional[bool] = None
        self._openai_available: Optional[bool] = None

    def _check_ollama(self) -> bool:
        """Check if Ollama is available."""
        if self._ollama_available is not None:
            return self._ollama_available

        try:
            from ollama import Client
            client = Client(host=settings.OLLAMA_HOST)
            client.list()
            self._ollama_available = True
            logger.info(f"Ollama is available at {settings.OLLAMA_HOST}")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self._ollama_available = False

        return self._ollama_available

    def _check_openai(self) -> bool:
        """Check if OpenAI API is configured."""
        if self._openai_available is not None:
            return self._openai_available

        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self._openai_available = bool(api_key and api_key != "")
        if self._openai_available:
            logger.info("OpenAI API is configured")
        return self._openai_available

    async def analyze_transcription(
        self,
        text: str,
        use_ollama: bool = True,
        model: Optional[str] = None
    ) -> NursingAnalysis:
        """
        Analyze nursing care transcription using LLM.

        Args:
            text: The transcribed text to analyze
            use_ollama: Whether to prefer Ollama (local) over OpenAI
            model: Specific model to use (optional)

        Returns:
            NursingAnalysis with corrected text and categorized content
        """
        import time
        start_time = time.time()

        user_prompt = f"""Analysiere die folgende Pflegedokumentation und kategorisiere sie:

TRANSKRIPTION:
{text}

Antworte im JSON-Format wie im System-Prompt beschrieben."""

        try:
            if use_ollama and self._check_ollama():
                response = await self._call_ollama(user_prompt, model or settings.LLM_MODEL)
            elif self._check_openai():
                response = await self._call_openai(user_prompt, model or "gpt-4o-mini")
            else:
                logger.warning("No LLM available, returning basic analysis")
                return self._basic_analysis(text, time.time() - start_time)

            # Parse JSON response
            analysis = self._parse_response(response, text)
            analysis.processing_time = time.time() - start_time

            logger.info(f"Nursing LLM analysis completed in {analysis.processing_time:.2f}s")
            return analysis

        except Exception as e:
            logger.error(f"Nursing LLM analysis failed: {e}")
            return self._basic_analysis(text, time.time() - start_time)

    async def _call_ollama(self, prompt: str, model: str) -> str:
        """Call Ollama API."""
        from ollama import Client
        import asyncio

        def _sync_call():
            client = Client(host=settings.OLLAMA_HOST)
            response = client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": NURSING_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.3}
            )
            return response["message"]["content"]

        return await asyncio.to_thread(_sync_call)

    async def _call_openai(self, prompt: str, model: str) -> str:
        """Call OpenAI API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": NURSING_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content

    def _parse_response(self, response: str, original_text: str) -> NursingAnalysis:
        """Parse LLM response into NursingAnalysis."""
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                return NursingAnalysis(
                    corrected_text=data.get("corrected_text", original_text),
                    summary=data.get("summary", ""),
                    services=data.get("services", ""),
                    observations=data.get("observations", ""),
                    next_tasks=data.get("next_tasks", ""),
                    processing_time=0.0
                )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")

        # Fallback: use response as corrected text
        return NursingAnalysis(
            corrected_text=response.strip() if response else original_text,
            summary="",
            services="",
            observations="",
            next_tasks="",
            processing_time=0.0
        )

    def _basic_analysis(self, text: str, processing_time: float) -> NursingAnalysis:
        """Provide basic analysis without LLM."""
        # Simple keyword-based extraction
        text_lower = text.lower()

        services = []
        if any(word in text_lower for word in ["wäsche", "körperpflege", "gewaschen", "geduscht"]):
            services.append("Körperpflege durchgeführt")
        if any(word in text_lower for word in ["mobilisation", "transfer", "aufstehen", "gehen"]):
            services.append("Mobilisation unterstützt")
        if any(word in text_lower for word in ["medikament", "tablette", "tropfen", "salbe"]):
            services.append("Medikamentengabe")

        services_text = "\n".join(f"- {s}" for s in services) if services else "Keine spezifischen Leistungen erkannt"

        return NursingAnalysis(
            corrected_text=text,
            summary=f"Pflegeeinsatz dokumentiert. {len(text.split())} Wörter transkribiert.",
            services=services_text,
            observations="Keine besonderen Auffälligkeiten in automatischer Analyse erkannt.",
            next_tasks="Bitte vom LLM analysieren lassen für detaillierte Aufgaben.",
            processing_time=processing_time
        )

    def get_status(self) -> Dict[str, Any]:
        """Get LLM service status."""
        return {
            "ollama_available": self._check_ollama(),
            "openai_available": self._check_openai(),
            "preferred": "ollama" if self._check_ollama() else ("openai" if self._check_openai() else "none")
        }


# Global service instance
nursing_llm_service = NursingLLMService()
