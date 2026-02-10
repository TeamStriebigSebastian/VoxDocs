import json
from typing import List, Optional
from loguru import logger
from ollama import AsyncClient
from app.core.config import settings
from app.models.task import Task

class LLMClient:
    def __init__(self):
        self.client = AsyncClient(host=settings.OLLAMA_HOST)
        self.model = settings.LLM_MODEL

    async def analyze_tasks(self, transcript: str, open_tasks: List[Task]) -> dict:
        """
        Analyzes the transcript to determine:
        1. Which open tasks were completed.
        2. What NEW tasks should be created.
        
        Returns:
        {
            "completed_ids": [1, 2],
            "new_tasks": ["Take X", "Call Y"]
        }
        """
        # Prepare task list for the prompt
        task_list_str = "\n".join([f"- [ID: {t.id}] {t.title}" for t in open_tasks]) if open_tasks else "No open tasks."

        prompt = f"""
You are an intelligent assistant for medical task management.
Analyze the transcript and the list of open tasks.
1. Identify if any OPEN tasks were completed. Be lenient: if the user says "X done" and there is a task "Do X later", count it as done.
2. Identify if any NEW tasks serve as future todos/reminders/plans (look for keywords like "remind me", "next time", "plan", "todo").

Transcript:
"{transcript}"

Open Tasks:
{task_list_str}

Return a valid JSON object with:
- "completed_ids": [list of integer IDs]
- "new_tasks": [list of strings for new task titles]
"""
        
        try:
            logger.info(f"Sending prompt to LLM ({self.model})...")
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                stream=False
            )
            
            response_text = response['response']
            logger.info(f"LLM Response: {response_text}")
            
            result = json.loads(response_text)
            
            # Sanitize
            completed_ids = result.get("completed_ids", [])
            new_tasks = result.get("new_tasks", [])
            
            if open_tasks:
                valid_ids = [t.id for t in open_tasks]
                # Cast to int to handle "3" vs 3 mismatch
                cleaned_ids = []
                for tid in completed_ids:
                    try:
                        cleaned_ids.append(int(tid))
                    except ValueError:
                        continue
                
                completed_ids = [tid for tid in cleaned_ids if tid in valid_ids]
            
            return {
                "completed_ids": completed_ids,
                "new_tasks": new_tasks
            }

        except Exception as e:
            logger.error(f"LLM Task Analysis Error: {e}")
            return {"completed_ids": [], "new_tasks": []}

    async def translate_text(self, text: str, target_language: str, highlight_phrase: str = None) -> str:
        """
        Translates text to target language using LLM.
        If highlight_phrase is provided, asks LLM to wrap the corresponding translated phrase in <mark> tags.
        """
        if not text:
            return ""
            
        highlight_instr = ""
        prior_instructions = ""
        if highlight_phrase:
            highlight_instr = f"""
IMPORTANT: The phrase "{highlight_phrase}" is highlighted in the source text.
You MUST identify the corresponding phrase in the translation and wrap it in <mark> tags.
Ensure the <mark> tags are placed NATURALLY within the translated sentence.
DO NOT append the highlighted phrase at the end.
Example: if source is "Review the <mark>blue door</mark>" and target is German, output "Prüfen Sie die <mark>blaue Tür</mark>".
"""

        prompt = f"""
You are a professional translator. 
Translate the following text into {target_language}.
Maintain the professional tone.
Do not add any explanations, just return the translated text.
{highlight_instr}

Text:
"{text}"

"""
        try:
            # logger.info(f"Translating text to {target_language}...")
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False
            )
            return response['response'].strip()
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text # Fallback to original

    async def chunk_transcript(self, text: str) -> list[str]:
        """
        Semantically chunk a transcript into coherent segments using Ollama.
        Returns a list of text chunks.
        """
        if not text or len(text.strip()) < 50:
            return [text.strip()] if text and text.strip() else []

        prompt = f"""Du bist ein Assistent für semantisches Text-Chunking.
Teile den folgenden Transkriptionstext in logische, inhaltlich zusammenhängende Abschnitte auf.

Regeln:
1. Jeder Abschnitt soll ein eigenständiges Thema oder eine zusammenhängende Aussage enthalten.
2. Abschnitte sollten zwischen 1-5 Sätzen lang sein.
3. Schneide niemals mitten im Satz ab.
4. Behalte den Originaltext exakt bei (keine Korrekturen, keine Zusammenfassungen).
5. Gib das Ergebnis als JSON-Array von Strings zurück.

Transkription:
\"{text}\"

Antworte NUR mit einem JSON-Objekt:
{{
  "chunks": ["Abschnitt 1...", "Abschnitt 2...", ...]
}}"""

        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                format="json"
            )
            result = json.loads(response['response'])
            chunks = result.get("chunks", [])
            
            # Fallback: if LLM returns empty or invalid, return whole text
            if not chunks or not isinstance(chunks, list):
                logger.warning("LLM chunking returned invalid result, using full text as single chunk")
                return [text.strip()]
            
            # Filter out empty chunks
            chunks = [c.strip() for c in chunks if c and c.strip()]
            return chunks if chunks else [text.strip()]
            
        except Exception as e:
            logger.error(f"Semantic chunking failed: {e}")
            # Fallback: split by double newlines or return as single chunk
            fallback = [p.strip() for p in text.split("\n\n") if p.strip()]
            return fallback if fallback else [text.strip()]

    DEFAULT_SINGLE_CATEGORY_PROMPT = """Du bist ein Experte für Dokumentation.
Prüfe, ob der folgende Textabschnitt zur Kategorie "{category_name}" passt.

Keywords zur Orientierung: {keywords}

Regeln:
1. Analysiere den Text inhaltlich.
2. Wenn der Text eindeutig zu "{category_name}" gehört, setze "match" auf true.
3. Extrahiere den Beweis (Textstelle).
4. Wenn unsicher oder unpassend, setze "match" auf false.

Text:
"{text}"

Antworte NUR im JSON-Format:
{{
  "match": true/false,
  "evidence_snippet": "..."
}}"""

    # Default blueprint prompt used when a category has no custom prompt_template
    DEFAULT_CATEGORIZE_PROMPT = """Du bist ein intelligenter Kategorisierungs-Assistent.
Analysiere den folgenden Textabschnitt und bestimme, zu welcher Kategorie er gehört.

Kategorien:
{categories_json}

Anweisungen:
1. Wähle die BESTE passende Kategorie basierend auf Bedeutung und Schlüsselwörtern.
2. Extrahiere die EXAKTE Phrase oder den Satzabschnitt aus dem Text, der diese Wahl rechtfertigt.
3. Wenn keine Kategorie gut passt, gib null zurück.

Antworte NUR im JSON-Format:
{{
  "category_id": <id oder null>,
  "evidence_snippet": "<exakter Textausschnitt>"
}}

Text:
\"{text}\""""

    async def categorize_chunk(self, text: str, categories: list) -> dict:
        """
        Categorize a single chunk against available categories.
        Uses per-category prompt_template when available, falls back to default blueprint.
        Returns the best matching category ID and the evidence snippet.
        """
        if not categories:
            return None

        # Check if any category has a custom prompt
        # If a category has a custom prompt, we run it individually for better precision
        custom_cats = [c for c in categories if getattr(c, 'prompt_template', None)]
        default_cats = [c for c in categories if not getattr(c, 'prompt_template', None)]

        best_result = None

        # Run categories with custom prompts individually
        for cat in custom_cats:
            try:
                prompt = cat.prompt_template.format(
                    text=text,
                    category_name=cat.name,
                    keywords=cat.keywords or ""
                )
                response = await self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    stream=False,
                    format="json"
                )
                result = json.loads(response['response'])
                # Custom prompts should return {"match": true/false, "evidence_snippet": "..."}
                if result.get("match") or result.get("category_id") == cat.id:
                    return {"category_id": cat.id, "evidence_snippet": result.get("evidence_snippet", "")}
            except Exception as e:
                logger.error(f"Custom prompt categorization failed for category {cat.id}: {e}")

        # Run default categories as a batch
        if default_cats:
            cats_json = [{"id": c.id, "name": c.name, "keywords": c.keywords} for c in default_cats]
            prompt = self.DEFAULT_CATEGORIZE_PROMPT.format(
                categories_json=json.dumps(cats_json, indent=2, ensure_ascii=False),
                text=text
            )
            try:
                response = await self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    stream=False,
                    format="json"
                )
                result = json.loads(response['response'])
                if result and result.get("category_id"):
                    return result
            except Exception as e:
                logger.error(f"Default categorization failed: {e}")

        return None

    async def categorize_entry(self, text: str, categories: list) -> dict:
        """Legacy wrapper – delegates to categorize_chunk."""
        return await self.categorize_chunk(text, categories)

# Global instance
llm_client = LLMClient()
