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

    async def categorize_entry(self, text: str, categories: list) -> dict:
        """
        Analyzes the text against the provided categories.
        Returns the best matching category ID and the evidence snippet.
        """
        if not categories:
            return None
            
        cats_json = [{"id": c.id, "name": c.name, "keywords": c.keywords} for c in categories]
        
        prompt = f"""
You are an intelligent categorization assistant.
Analyze the following transcription and determine which category it belongs to.

Categories:
{json.dumps(cats_json, indent=2)}

Instructions:
1. Select the BEST matching category based on the meaning and keywords.
2. Extract the EXACT phrase or sentence fragment from the text that justifies this choice.
3. If no category fits well, return null.

Return JSON format ONLY:
{{
  "category_id": <id or null>,
  "evidence_snippet": "<exact text fragment>"
}}

Transcription:
"{text}"
"""
        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                format="json"
            )
            result = json.loads(response['response'])
            return result
        except Exception as e:
            logger.error(f"Categorization failed: {e}")
            return None

# Global instance
llm_client = LLMClient()
