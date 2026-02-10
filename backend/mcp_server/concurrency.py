"""
Concurrency Control for VoxDocs MCP Server

Implements global job limiting with backpressure and timeouts.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from dataclasses import dataclass
from enum import Enum

from .config import get_settings


class JobType(str, Enum):
    """Types of jobs for timeout selection."""
    RETRIEVAL = "retrieval"
    INGESTION = "ingestion"


@dataclass
class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    retry_after_sec: float = 5.0
    message: str = "Rate limit exceeded. Too many concurrent requests."
    
    def to_dict(self) -> dict:
        return {
            "error": "rate_limit_exceeded",
            "message": self.message,
            "retry_after_sec": self.retry_after_sec,
        }


@dataclass
class TimeoutError(Exception):
    """Raised when a job times out."""
    timeout_sec: float
    job_type: JobType
    
    def to_dict(self) -> dict:
        return {
            "error": "timeout",
            "message": f"{self.job_type.value} timed out after {self.timeout_sec}s",
            "timeout_sec": self.timeout_sec,
        }


class JobLimiter:
    """
    Global job limiter with semaphore-based concurrency control.
    
    Implements:
    - MAX_CONCURRENT_JOBS limit
    - Per-job-type timeouts
    - Non-blocking rejection (no queuing)
    """
    
    def __init__(self, max_concurrent: Optional[int] = None):
        settings = get_settings()
        self.max_concurrent = max_concurrent or settings.max_concurrent_jobs
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._active_jobs = 0
        self._lock = asyncio.Lock()
    
    @property
    def active_jobs(self) -> int:
        """Current number of active jobs."""
        return self._active_jobs
    
    @property
    def available_slots(self) -> int:
        """Number of available job slots."""
        return self.max_concurrent - self._active_jobs
    
    def _get_timeout(self, job_type: JobType) -> float:
        """Get timeout for a job type."""
        settings = get_settings()
        if job_type == JobType.RETRIEVAL:
            return settings.retrieval_timeout_sec
        elif job_type == JobType.INGESTION:
            return settings.ingestion_timeout_sec
        return settings.retrieval_timeout_sec  # Default
    
    @asynccontextmanager
    async def acquire(self, job_type: JobType) -> AsyncGenerator[None, None]:
        """
        Acquire a job slot with timeout.
        
        Raises:
            RateLimitError: If no slots available (non-blocking)
            TimeoutError: If job exceeds timeout
        """
        # Try to acquire without blocking
        acquired = self._semaphore.locked() is False
        if not acquired:
            # Check if we can acquire immediately
            try:
                # Use wait_for with 0 timeout to check availability
                await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=0.01  # Near-instant check
                )
            except asyncio.TimeoutError:
                raise RateLimitError(
                    retry_after_sec=5.0,
                    message=f"Rate limit exceeded. {self._active_jobs}/{self.max_concurrent} jobs active."
                )
        else:
            await self._semaphore.acquire()
        
        async with self._lock:
            self._active_jobs += 1
        
        timeout = self._get_timeout(job_type)
        
        try:
            yield
        finally:
            async with self._lock:
                self._active_jobs -= 1
            self._semaphore.release()
    
    async def run_with_limit(
        self,
        job_type: JobType,
        coro,
    ):
        """
        Run a coroutine with job limiting and timeout.
        
        Args:
            job_type: Type of job for timeout selection
            coro: Coroutine to run
            
        Returns:
            Result of the coroutine
            
        Raises:
            RateLimitError: If no slots available
            TimeoutError: If job exceeds timeout
        """
        async with self.acquire(job_type):
            timeout = self._get_timeout(job_type)
            try:
                return await asyncio.wait_for(coro, timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(timeout_sec=timeout, job_type=job_type)


# Global job limiter instance
_job_limiter: Optional[JobLimiter] = None


def get_job_limiter() -> JobLimiter:
    """Get the global job limiter instance."""
    global _job_limiter
    if _job_limiter is None:
        _job_limiter = JobLimiter()
    return _job_limiter


# Convenience alias
job_limiter = get_job_limiter
