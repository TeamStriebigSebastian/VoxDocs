import asyncio
import os
from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger
from app.core.database import async_session_maker
from app.models.entry import Entry, AudioStatus
from app.models.entry_chunk import EntryChunk
from app.core.audio import transcribe_audio_file
from app.core.config import settings
from app.core.llm import llm_client

# Global running flag
RUNNING = True

async def process_audio_queue():
    """
    Continuous loop to process pending audio entries.
    
    Flow after Whisper:
      1. Semantic chunking (Ollama)
      2. Per-chunk categorization (with custom prompts)
      3. Store EntryChunks
      4. Translation per chunk
      5. Task analysis on full transcript
    """
    logger.info("Starting Audio Worker Loop...")
    
    while RUNNING:
        try:
            async with async_session_maker() as db:
                # 1. Fetch NEXT pending entry
                query = select(Entry).options(selectinload(Entry.case_file)).where(
                    Entry.audio_status == AudioStatus.PENDING
                ).order_by(Entry.created_at.asc()).limit(1)
                
                result = await db.execute(query)
                entry = result.scalar_one_or_none()
                
                if not entry:
                    # No work, sleep
                    await asyncio.sleep(2.0)
                    continue
                
                logger.info(f"Processing Entry {entry.uuid}...")
                
                # 3. Transcribe
                try:
                    # Resolve path
                    file_path = os.path.join(settings.ENCRYPTED_DIR, entry.audio_object_key)
                    
                    transcript = await transcribe_audio_file(file_path)
                    
                    # 4. Update Entry
                    # Append transcript to existing text (if any)
                    current_text = entry.text or ""
                    new_text = f"{current_text}\n\n[Transkription]: {transcript}".strip()
                    
                    entry.text = new_text
                    entry.audio_status = AudioStatus.TRANSCRIBED
                    
                    # Log success
                    logger.info(f"Successfully transcribed entry {entry.uuid}")

                    # ─── 4a. SEMANTIC CHUNKING ───────────────────────────
                    chunks_text = []
                    try:
                        chunks_text = await llm_client.chunk_transcript(transcript)
                        logger.info(f"Semantic chunking produced {len(chunks_text)} chunks for entry {entry.uuid}")
                    except Exception as chunk_err:
                        logger.error(f"Semantic chunking failed, using full text: {chunk_err}")
                        chunks_text = [transcript]

                    # ─── 4b. PER-CHUNK CATEGORIZATION ────────────────────
                    chunk_category_ids = []
                    highlight_snippet = None
                    try:
                        from app.models.category import CategoryDefinition
                        
                        group_id = entry.case_file.group_id
                        cats_query = select(CategoryDefinition).where(CategoryDefinition.group_id == group_id)
                        cats_result = await db.execute(cats_query)
                        categories = cats_result.scalars().all()
                        
                        for idx, chunk_text in enumerate(chunks_text):
                            cat_result = await llm_client.categorize_chunk(chunk_text, categories)
                            
                            chunk_cat_id = None
                            chunk_evidence = None
                            if cat_result and cat_result.get("category_id"):
                                chunk_cat_id = cat_result["category_id"]
                                chunk_evidence = cat_result.get("evidence_snippet")
                                chunk_category_ids.append(chunk_cat_id)
                                
                                # Keep first evidence for backward compat
                                if highlight_snippet is None and chunk_evidence:
                                    highlight_snippet = chunk_evidence
                                
                                logger.info(f"Chunk {idx} categorized as {chunk_cat_id}")
                            
                            # Store EntryChunk
                            entry_chunk = EntryChunk(
                                entry_id=entry.id,
                                chunk_index=idx,
                                text=chunk_text,
                                category_id=chunk_cat_id,
                                evidence_snippet=chunk_evidence,
                            )
                            db.add(entry_chunk)
                        
                        # Set entry-level category to most frequent chunk category
                        if chunk_category_ids:
                            most_common_cat = Counter(chunk_category_ids).most_common(1)[0][0]
                            entry.category_id = most_common_cat
                            logger.info(f"Entry {entry.uuid} primary category set to {most_common_cat}")
                        
                        # Backward compat: store highlight snippet
                        if highlight_snippet:
                            s_data = entry.structured_data or {}
                            s_data["highlight_snippet"] = highlight_snippet
                            entry.structured_data = s_data
                            
                    except Exception as cat_err:
                        logger.error(f"Auto-categorization failed: {cat_err}")
                        # Still store chunks even if categorization fails
                        for idx, chunk_text in enumerate(chunks_text):
                            entry_chunk = EntryChunk(
                                entry_id=entry.id,
                                chunk_index=idx,
                                text=chunk_text,
                            )
                            db.add(entry_chunk)
                    
                    # ─── 4c. MULTI-LANGUAGE TRANSLATIONS ──────────────────
                    target_langs = set()
                    try:
                        from app.models.tenant import Tenant, Group
                        from app.models.user import User
                        from app.models.entry_translation import EntryTranslation
                        from app.models.task_translation import TaskTranslation
                        
                        author = await db.scalar(select(User).where(User.id == entry.author_id))
                        group = await db.scalar(select(Group).where(Group.id == entry.case_file.group_id))
                        tenant = await db.scalar(select(Tenant).where(Tenant.id == group.tenant_id))
                        
                        user_lang = author.preferred_language or "en"
                        server_lang = tenant.default_language or "en"
                        
                        target_langs = set()
                        if user_lang: target_langs.add(user_lang)
                        if server_lang: target_langs.add(server_lang)
                        
                        # Translate the FULL transcript (joined chunks)
                        for lang in target_langs:
                            translated_text = await llm_client.translate_text(
                                transcript, 
                                lang,
                                highlight_phrase=highlight_snippet
                            )
                            
                            trans_entry = EntryTranslation(
                                entry_id=entry.id,
                                language_code=lang,
                                translated_text=translated_text
                            )
                            db.add(trans_entry)
                            logger.info(f"Stored Entry Translation ({lang})")

                    except Exception as trans_err:
                         logger.error(f"Entry Translation failed: {trans_err}")

                    # ─── 4d. AI TASK ANALYSIS ─────────────────────────────
                    try:
                        from app.core.llm import llm_client
                        from app.models.task import Task, TaskStatus, TaskType
                        from datetime import datetime
                        
                        tasks_query = select(Task).where(
                            Task.case_id == entry.case_id,
                            Task.status == TaskStatus.ACTIVE
                        )
                        tasks_result = await db.execute(tasks_query)
                        open_tasks = tasks_result.scalars().all()
                        
                        logger.info(f"Open Tasks for Analysis: {[t.id for t in open_tasks]}")
                        analysis = await llm_client.analyze_tasks(transcript, open_tasks)
                        
                        completed_ids = analysis.get("completed_ids", [])
                        new_task_titles = analysis.get("new_tasks", [])
                        
                        actions_log = []
                        
                        if completed_ids and open_tasks:
                            for t in open_tasks:
                                if t.id in completed_ids:
                                    t.status = TaskStatus.COMPLETED
                                    t.last_completed_at = datetime.utcnow()
                            actions_log.append(f"{len(completed_ids)} Aufgabe(n) erledigt")

                        if new_task_titles:
                            for title in new_task_titles:
                                new_task = Task(
                                    case_id=entry.case_id,
                                    title=title,
                                    task_type=TaskType.ONE_SHOT,
                                    status=TaskStatus.ACTIVE,
                                    created_by=entry.author_id,
                                    created_at=datetime.utcnow()
                                )
                                db.add(new_task)
                                await db.flush()
                                
                                for lang in target_langs:
                                    try:
                                        t_title = await llm_client.translate_text(title, lang)
                                        task_trans = TaskTranslation(
                                            task_id=new_task.id,
                                            language_code=lang,
                                            title=t_title
                                        )
                                        db.add(task_trans)
                                    except Exception as tt_err:
                                        logger.error(f"Task Translation failed: {tt_err}")

                            actions_log.append(f"{len(new_task_titles)} Aufgabe(n) erstellt")

                        if actions_log:
                            summary = ", ".join(actions_log) + "."
                            logger.info(f"AI Actions: {summary}")
                            new_text += f"\n\n[System]: {summary}"
                            entry.text = new_text

                                
                    except Exception as llm_err:
                        logger.error(f"Task AI analysis failed: {llm_err}")

                except Exception as e:
                    logger.error(f"Failed to transcribe entry {entry.uuid}: {e}")
                    entry.audio_status = AudioStatus.FAILED
                
                # Commit updates
                await db.commit()
                
                # 5. Notify Frontend (WebHook)
                try:
                    from app.api.webhooks import send_transcription_ready_notification
                    await send_transcription_ready_notification(entry.case_file.uuid if entry.case_file else "unknown")
                except Exception as notify_err:
                    logger.warning(f"Could not send notification: {notify_err}")

        except Exception as e:
            logger.error(f"Worker Loop Error: {e}")
            await asyncio.sleep(5.0)

async def start_worker():
    """Helper to start the worker as task"""
    asyncio.create_task(process_audio_queue())

