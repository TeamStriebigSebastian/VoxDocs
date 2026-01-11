"""
LLM Service for dental transcription correction, classification, and task extraction.
Supports both Ollama (local, GDPR-compliant) and OpenAI API.
"""

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from loguru import logger

from app.core.config import settings


@dataclass
class DentalAnalysis:
    """Result of LLM analysis of dental transcription."""
    corrected_text: str
    classifications: List[Dict[str, Any]]
    tasks: List[Dict[str, str]]
    summary: str
    processing_time: float


# System prompt for dental analysis
DENTAL_SYSTEM_PROMPT = """Du bist ein spezialisierter Assistent für zahnärztliche Dokumentation.
Deine Aufgaben:
1. Korrigiere Transkriptionsfehler bei zahnmedizinischen Fachbegriffen
2. Klassifiziere die Inhalte nach Kategorien
3. Extrahiere Aufgaben für den nächsten Termin

WICHTIGE ZAHNMEDIZINISCHE BEGRIFFE:
- Zahnbezeichnung FDI: Zahn 11-18 (OK rechts), 21-28 (OK links), 31-38 (UK links), 41-48 (UK rechts)
- Flächen: mesial, distal, bukkal, lingual, palatinal, okklusal, inzisal, approximal, zervikal, vestibulär
- Diagnosen: Karies (Grad 1-4), Pulpitis, Parodontitis, Gingivitis, Periimplantitis, Apikale Parodontitis
- Befunde: Lockerungsgrad (I-III), Taschentiefe, BOP (Blutung auf Sondierung), Furkation, Rezession
- Behandlungen: Wurzelkanalbehandlung, Extraktion, Implantation, Füllungstherapie, PZR, Kronenversorgung
- Materialien: Composite, Amalgam, Glasionomerzement, Zirkonoxid, Keramik, Guttapercha

KLASSIFIKATIONSKATEGORIEN:
- befund: Klinische Befunde und Diagnosen
- behandlung: Durchgeführte Behandlungsschritte
- planung: Geplante Maßnahmen und Empfehlungen
- anamnese: Patienteninformationen und Vorgeschichte
- aufgabe: Aufgaben für den nächsten Termin

Antworte IMMER im folgenden JSON-Format:
{
  "corrected_text": "Der korrigierte Text mit richtiger Fachterminologie",
  "classifications": [
    {"category": "befund", "text": "Relevanter Textabschnitt", "confidence": 0.95}
  ],
  "tasks": [
    {"task": "Beschreibung der Aufgabe", "priority": "hoch/mittel/niedrig", "due": "nächster Termin"}
  ],
  "summary": "Kurze Zusammenfassung des Befunds in 1-2 Sätzen"
}"""


class LLMService:
    """Service for LLM-based dental text analysis."""

    def __init__(self):
        self._ollama_available: Optional[bool] = None
        self._openai_available: Optional[bool] = None

    def _check_ollama(self) -> bool:
        """Check if Ollama is available."""
        if self._ollama_available is not None:
            return self._ollama_available

        try:
            import ollama
            # Try to list models to verify connection
            ollama.list()
            self._ollama_available = True
            logger.info("Ollama is available")
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
    ) -> DentalAnalysis:
        """
        Analyze dental transcription using LLM.

        Args:
            text: The transcribed text to analyze
            use_ollama: Whether to prefer Ollama (local) over OpenAI
            model: Specific model to use (optional)

        Returns:
            DentalAnalysis with corrected text, classifications, and tasks
        """
        import time
        start_time = time.time()

        user_prompt = f"""Analysiere die folgende zahnärztliche Transkription und korrigiere Fachbegriffe:

TRANSKRIPTION:
{text}

Antworte im JSON-Format wie im System-Prompt beschrieben."""

        try:
            if use_ollama and self._check_ollama():
                response = await self._call_ollama(user_prompt, model or "llama3.2")
            elif self._check_openai():
                response = await self._call_openai(user_prompt, model or "gpt-4o-mini")
            else:
                # Fallback: Return original text with basic analysis
                logger.warning("No LLM available, returning basic analysis")
                return self._basic_analysis(text, time.time() - start_time)

            # Parse JSON response
            analysis = self._parse_response(response, text)
            analysis.processing_time = time.time() - start_time

            logger.info(f"LLM analysis completed in {analysis.processing_time:.2f}s")
            return analysis

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._basic_analysis(text, time.time() - start_time)

    async def _call_ollama(self, prompt: str, model: str) -> str:
        """Call Ollama API."""
        import ollama
        import asyncio

        def _sync_call():
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": DENTAL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.3}
            )
            return response["message"]["content"]

        # Run in thread pool to not block
        return await asyncio.to_thread(_sync_call)

    async def _call_openai(self, prompt: str, model: str) -> str:
        """Call OpenAI API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": DENTAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content

    def _parse_response(self, response: str, original_text: str) -> DentalAnalysis:
        """Parse LLM response into DentalAnalysis."""
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                return DentalAnalysis(
                    corrected_text=data.get("corrected_text", original_text),
                    classifications=data.get("classifications", []),
                    tasks=data.get("tasks", []),
                    summary=data.get("summary", ""),
                    processing_time=0.0
                )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")

        # Fallback: use response as corrected text
        return DentalAnalysis(
            corrected_text=response.strip() if response else original_text,
            classifications=[],
            tasks=[],
            summary="",
            processing_time=0.0
        )

    def _basic_analysis(self, text: str, processing_time: float) -> DentalAnalysis:
        """Provide basic analysis without LLM."""
        # Simple keyword-based classification
        classifications = []
        tasks = []

        text_lower = text.lower()

        # Basic classification
        if any(word in text_lower for word in ["karies", "befund", "lockerung", "tasche"]):
            classifications.append({
                "category": "befund",
                "text": text[:100],
                "confidence": 0.6
            })

        if any(word in text_lower for word in ["füllung", "extraktion", "behandlung", "wurzel"]):
            classifications.append({
                "category": "behandlung",
                "text": text[:100],
                "confidence": 0.6
            })

        # Task extraction (look for keywords)
        if any(word in text_lower for word in ["nächster termin", "kontroll", "wiederkommen", "nachsorge"]):
            tasks.append({
                "task": "Kontrolltermin vereinbaren",
                "priority": "mittel",
                "due": "nächster Termin"
            })

        return DentalAnalysis(
            corrected_text=text,
            classifications=classifications,
            tasks=tasks,
            summary="Automatische Analyse ohne LLM",
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
llm_service = LLMService()
