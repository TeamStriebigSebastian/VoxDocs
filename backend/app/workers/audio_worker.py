import asyncio
import os
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger
from app.core.database import async_session_maker
from app.models.entry import Entry, AudioStatus
from app.core.audio import transcribe_audio_file
from app.core.config import settings

# Global running flag
RUNNING = True

async def process_audio_queue():
    """
    Continuous loop to process pending audio entries.
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
                
                # 2. Mark as PROCESSING (optional, skipping for now to simple 'transcribed')
                
                # 3. Transcribe
                try:
                    # Resolve path
                    # Assuming default storage structure
                    file_path = os.path.join("/app/storage/encrypted", entry.audio_object_key)
                    
                    transcript = await transcribe_audio_file(file_path)
                    
                    # 4. Update Entry
                    # Append transcript to existing text (if any)
                    current_text = entry.text or ""
                    new_text = f"{current_text}\n\n[Transkription]: {transcript}".strip()
                    
                    entry.text = new_text
                    entry.audio_status = AudioStatus.TRANSCRIBED
                    
                    # Log success
                    logger.info(f"Successfully transcribed entry {entry.uuid}")

                    
                    # 4a. Auto-Categorization (LLM Based)
                    highlight_snippet = None
                    try:
                         # Need to import CategoryDefinition here or top level
                         from app.models.category import CategoryDefinition
                         
                         # Fetch categories for this case's group
                         group_id = entry.case_file.group_id
                         cats_query = select(CategoryDefinition).where(CategoryDefinition.group_id == group_id)
                         cats_result = await db.execute(cats_query)
                         categories = cats_result.scalars().all()
                         
                         cat_result = await llm_client.categorize_entry(transcript, categories)
                         
                         if cat_result and cat_result.get("category_id"):
                             entry.category_id = cat_result["category_id"]
                             
                             # Store evidence for highlighting
                             snippet = cat_result.get("evidence_snippet")
                             if snippet:
                                 highlight_snippet = snippet
                                 # Update structured_data
                                 s_data = entry.structured_data or {}
                                 s_data["highlight_snippet"] = snippet
                                 entry.structured_data = s_data
                                 
                             logger.info(f"Auto-Categorized entry {entry.uuid} as {entry.category_id} (Evidence: {snippet})")
                             
                    except Exception as cat_err:
                        logger.error(f"Auto-categorization failed: {cat_err}")
                    
                    # 4b. Multi-Language Handling (Translations)
                    try:
                        # Fetch User and Tenant Languages
                        # We need to reload entry with author and tenant info if not present, 
                        # or just fetch them.
                        from app.models.tenant import Tenant, Group
                        from app.models.user import User
                        from app.models.entry_translation import EntryTranslation
                        from app.models.task_translation import TaskTranslation
                        
                        # Fetch Author
                        author = await db.scalar(select(User).where(User.id == entry.author_id))
                        # Fetch Tenant (via Case->Group->Tenant)
                        # entry.case_file is already loaded
                        group = await db.scalar(select(Group).where(Group.id == entry.case_file.group_id))
                        tenant = await db.scalar(select(Tenant).where(Tenant.id == group.tenant_id))
                        
                        user_lang = author.preferred_language or "en"
                        server_lang = tenant.default_language or "en"
                        
                        target_langs = set()
                        if user_lang: target_langs.add(user_lang)
                        if server_lang: target_langs.add(server_lang)
                        
                        # Translate Entry
                        current_transcript_text = transcript # The raw transcription
                        
                        for lang in target_langs:
                            # We blindly ask LLM to translate. 
                            # If it detects it's already in that language, it returns it (or we rely on LLM smarts).
                            # Optimization: If we knew source lang, we could skip one.
                            # For now, translate to ALL target langs to be safe and ensure coverage.
                            
                            # Pass highlight snippet if available
                            translated_text = await llm_client.translate_text(
                                current_transcript_text, 
                                lang,
                                highlight_phrase=highlight_snippet
                            )
                            
                            # Store Translation
                            # Check if exists (unlikely new entry)
                            trans_entry = EntryTranslation(
                                entry_id=entry.id,
                                language_code=lang,
                                translated_text=translated_text
                            )
                            db.add(trans_entry)
                            logger.info(f"Stored Entry Translation ({lang})")

                    except Exception as trans_err:
                         logger.error(f"Entry Translation failed: {trans_err}")

                    # 4c. AI Task Analysis (Check & Create)
                    try:
                        from app.core.llm import llm_client
                        from app.models.task import Task, TaskStatus, TaskType
                        from datetime import datetime
                        
                        # Fetch open tasks
                        tasks_query = select(Task).where(
                            Task.case_id == entry.case_id,
                            Task.status == TaskStatus.ACTIVE
                        )
                        tasks_result = await db.execute(tasks_query)
                        open_tasks = tasks_result.scalars().all()
                        
                        # Call LLM
                        logger.info(f"Open Tasks for Analysis: {[t.id for t in open_tasks]}")
                        # logger.info(f"Open Tasks Titles: {[t.title for t in open_tasks]}")
                        # logger.info("requesting LLM analysis...")
                        analysis = await llm_client.analyze_tasks(transcript, open_tasks)
                        
                        completed_ids = analysis.get("completed_ids", [])
                        new_task_titles = analysis.get("new_tasks", [])
                        
                        actions_log = []
                        
                        # Process Completions
                        if completed_ids and open_tasks:
                            for t in open_tasks:
                                if t.id in completed_ids:
                                    t.status = TaskStatus.COMPLETED
                                    t.last_completed_at = datetime.utcnow()
                            actions_log.append(f"{len(completed_ids)} Aufgabe(n) erledigt")

                        # Process Creations
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
                                await db.flush() # Get ID
                                
                                # Translate Task
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

                        # Append System Note
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
                # We need to import the manager from webhooks, but imports might be circular if not careful.
                # Doing purely via DB polling on frontend or explicit call here.
                # For now, let's try to notify.
                try:
                    from app.api.webhooks import send_transcription_ready_notification
                    # Need an 'appointment_uuid' equivalent. We used 'Case' concepts.
                    # The webhook frontend expects "transcription_ready".
                    await send_transcription_ready_notification(entry.case_file.uuid if entry.case_file else "unknown")
                except Exception as notify_err:
                    logger.warning(f"Could not send notification: {notify_err}")

        except Exception as e:
            logger.error(f"Worker Loop Error: {e}")
            await asyncio.sleep(5.0)

async def start_worker():
    """Helper to start the worker as task"""
    asyncio.create_task(process_audio_queue())
