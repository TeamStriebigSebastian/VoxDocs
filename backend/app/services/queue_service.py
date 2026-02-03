"""
Queue service for batch processing of audio files.
Simple async queue for MVP, with option to use Celery/Redis later.
"""

import asyncio
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings


class JobStatus(str, Enum):
    """Status of a queue job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueueJob:
    """A job in the processing queue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recording_id: int = 0
    audio_path: str = ""
    practice_id: int = 0
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    priority: int = 0  # Higher = more urgent


class QueueService:
    """Async queue service for audio processing."""

    def __init__(self):
        self._queue: asyncio.Queue[QueueJob] = asyncio.Queue()
        self._pending_jobs: Dict[str, QueueJob] = {}
        self._completed_jobs: Dict[str, QueueJob] = {}
        self._processing_jobs: set[str] = set()  # Track jobs currently being processed
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._processor_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._process_callback: Optional[Callable] = None
        self._lock = asyncio.Lock()  # Lock for thread-safe job state changes

    async def start(self):
        """Start the queue service and scheduler."""
        if self._is_running:
            return

        self._is_running = True

        # Initialize scheduler for batch processing
        self._scheduler = AsyncIOScheduler()

        # Schedule nightly batch processing
        self._scheduler.add_job(
            self._run_batch_processing,
            CronTrigger(hour=settings.BATCH_PROCESSING_HOUR, minute=0),
            id="nightly_batch",
            name="Nightly Batch Processing"
        )

        self._scheduler.start()
        logger.info(f"Queue scheduler started. Batch processing at {settings.BATCH_PROCESSING_HOUR}:00")

        # Start background processor
        self._processor_task = asyncio.create_task(self._process_queue())
        logger.info("Queue processor started")

    async def stop(self):
        """Stop the queue service."""
        self._is_running = False

        if self._scheduler:
            self._scheduler.shutdown()

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Queue service stopped")

    def set_processor(self, callback: Callable):
        """Set the callback function to process jobs."""
        self._process_callback = callback

    async def add_job(
        self,
        recording_id: int,
        audio_path: str,
        practice_id: int,
        priority: int = 0
    ) -> QueueJob:
        """
        Add a job to the processing queue.

        Args:
            recording_id: Database ID of the recording
            audio_path: Path to the audio file
            practice_id: ID of the practice
            priority: Job priority (higher = more urgent)

        Returns:
            The created QueueJob
        """
        job = QueueJob(
            recording_id=recording_id,
            audio_path=audio_path,
            practice_id=practice_id,
            priority=priority
        )

        self._pending_jobs[job.id] = job
        await self._queue.put(job)

        logger.info(f"Job added to queue: {job.id} (recording: {recording_id})")
        return job

    async def get_job_status(self, job_id: str) -> Optional[QueueJob]:
        """Get the status of a job by ID."""
        if job_id in self._pending_jobs:
            return self._pending_jobs[job_id]
        return self._completed_jobs.get(job_id)

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        pending = [j for j in self._pending_jobs.values() if j.status == JobStatus.PENDING]
        processing = [j for j in self._pending_jobs.values() if j.status == JobStatus.PROCESSING]
        completed = [j for j in self._completed_jobs.values() if j.status == JobStatus.COMPLETED]
        failed = [j for j in self._completed_jobs.values() if j.status == JobStatus.FAILED]

        return {
            "pending": len(pending),
            "processing": len(processing),
            "completed": len(completed),
            "failed": len(failed),
            "total_in_queue": self._queue.qsize(),
        }

    async def _process_queue(self):
        """Background task to process jobs from the queue."""
        while self._is_running:
            try:
                # Wait for a job with timeout
                try:
                    job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                await self._process_job(job)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(1)

    async def _process_job(self, job: QueueJob):
        """Process a single job."""
        # Use lock to prevent race condition with double-processing
        async with self._lock:
            # Check if job is already being processed or completed
            if job.id in self._processing_jobs:
                logger.debug(f"Job {job.id} already being processed, skipping")
                return
            if job.id in self._completed_jobs:
                logger.debug(f"Job {job.id} already completed, skipping")
                return
            if job.id not in self._pending_jobs:
                logger.debug(f"Job {job.id} not in pending jobs, skipping")
                return

            # Mark as processing
            self._processing_jobs.add(job.id)
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()

        logger.info(f"Processing job: {job.id}")

        try:
            if self._process_callback:
                result = await self._process_callback(job)
                job.result = result
                job.status = JobStatus.COMPLETED
                logger.info(f"Job completed: {job.id}")
            else:
                logger.warning(f"No processor callback set for job: {job.id}")
                job.status = JobStatus.FAILED
                job.error_message = "No processor callback configured"

        except Exception as e:
            logger.error(f"Job failed: {job.id} - {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)

        finally:
            job.completed_at = datetime.utcnow()
            async with self._lock:
                # Remove from processing set
                self._processing_jobs.discard(job.id)
                # Move to completed jobs
                if job.id in self._pending_jobs:
                    del self._pending_jobs[job.id]
                self._completed_jobs[job.id] = job

            # Clean up old completed jobs (keep last 1000)
            if len(self._completed_jobs) > 1000:
                oldest_ids = sorted(
                    self._completed_jobs.keys(),
                    key=lambda x: self._completed_jobs[x].completed_at or datetime.min
                )[:100]
                for old_id in oldest_ids:
                    del self._completed_jobs[old_id]

    async def _run_batch_processing(self):
        """Run batch processing of all pending jobs."""
        logger.info("Starting nightly batch processing")

        stats = self.get_queue_stats()
        logger.info(f"Batch processing: {stats['pending']} pending jobs")

        # Process all pending jobs
        while not self._queue.empty():
            try:
                job = self._queue.get_nowait()
                await self._process_job(job)
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Batch processing error: {e}")

        logger.info("Nightly batch processing completed")

    async def process_immediate(self, job_id: str) -> Optional[QueueJob]:
        """Process a specific job immediately (bypass queue)."""
        job = self._pending_jobs.get(job_id)
        if not job:
            return None

        # Remove from queue (if possible) and process immediately
        await self._process_job(job)
        return self._completed_jobs.get(job_id)


# Global service instance
queue_service = QueueService()
