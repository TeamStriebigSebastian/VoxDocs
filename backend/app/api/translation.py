from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models import User, Entry, EntryTranslation
from app.core.config import settings
import aiohttp
import json

router = APIRouter(prefix="/translation", tags=["Translation"])

class TranslationRequest(BaseModel):
    target_language: str

class TranslationResponse(BaseModel):
    entry_id: int
    language_code: str
    translated_text: str
    cached: bool

async def translate_text(text: str, target_lang: str) -> str:
    """Translation using Ollama."""
    prompt = f"Translate the following medical text to {target_lang}. Output ONLY the translation, no explanations:\n\n{text}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{settings.OLLAMA_HOST}/api/generate",
                json={
                    "model": settings.LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            ) as response:
                if response.status != 200:
                    raise Exception(f"Ollama API Error: {response.status}")
                result = await response.json()
                return result.get("response", "").strip()
        except Exception as e:
            print(f"Translation error: {e}")
            raise HTTPException(status_code=503, detail="Translation service unavailable")

@router.post("/{entry_id}", response_model=TranslationResponse)
async def translate_entry(
    entry_id: int,
    request: TranslationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch Entry
    entry = await db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
        
    # 2. Check Cache in EntryTranslation
    stmt = select(EntryTranslation).where(
        EntryTranslation.entry_id == entry_id,
        EntryTranslation.language_code == request.target_language
    )
    cached_trans = await db.scalar(stmt)
    
    if cached_trans:
        return TranslationResponse(
            entry_id=entry.id,
            language_code=cached_trans.language_code,
            translated_text=cached_trans.translated_text,
            cached=True
        )

    # 3. Perform Translation
    if not entry.text:
         return TranslationResponse(
            entry_id=entry.id,
            language_code=request.target_language,
            translated_text="",
            cached=False
        )
        
    translated_text = await translate_text(entry.text, request.target_language)
    
    # 4. Save to Cache
    new_trans = EntryTranslation(
        entry_id=entry.id,
        language_code=request.target_language,
        translated_text=translated_text
    )
    db.add(new_trans)
    await db.commit()
    await db.refresh(new_trans)
    
    return TranslationResponse(
        entry_id=entry.id,
        language_code=new_trans.language_code,
        translated_text=new_trans.translated_text,
        cached=False
    )
