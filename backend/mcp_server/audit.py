"""
Audit Logger for VoxDocs MCP Server

Append-only JSONL logging for compliance and debugging.
All tool executions are logged with required fields.
"""

import json
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import aiofiles

from .config import get_settings
from .auth import DenyReason


class AuditDecision(str, Enum):
    """Decision outcome for audit."""
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class AuditEntry:
    """Audit log entry with all required fields."""
    event_id: str
    timestamp: str
    tool_name: str
    username: str
    case_id: Optional[str]
    group_id: Optional[str]
    decision: str
    deny_reason: Optional[str]
    query_hash: Optional[str]
    returned_chunks_count: int
    min_distance: Optional[float]
    max_distance: Optional[float]
    duration_ms: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """
    Append-only audit logger.
    
    Logs to JSONL file with no mutation capability.
    Thread-safe for concurrent writes.
    """
    
    def __init__(self, log_path: Optional[Path] = None):
        settings = get_settings()
        self.log_path = log_path or settings.audit_log_path
        self._lock = asyncio.Lock()
        self._ensure_log_dir()
    
    def _ensure_log_dir(self) -> None:
        """Ensure log directory exists."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def hash_query(query: str) -> str:
        """Hash a query for privacy (no plaintext in logs)."""
        return hashlib.sha256(query.encode()).hexdigest()
    
    @staticmethod
    def generate_event_id() -> str:
        """Generate a unique event ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()
    
    async def log(
        self,
        tool_name: str,
        username: str,
        decision: AuditDecision,
        duration_ms: float,
        case_id: Optional[str] = None,
        group_id: Optional[str] = None,
        deny_reason: Optional[DenyReason] = None,
        query: Optional[str] = None,
        returned_chunks_count: int = 0,
        min_distance: Optional[float] = None,
        max_distance: Optional[float] = None,
    ) -> str:
        """
        Log an audit entry.
        
        Returns:
            The event_id of the logged entry
        """
        entry = AuditEntry(
            event_id=self.generate_event_id(),
            timestamp=self.get_timestamp(),
            tool_name=tool_name,
            username=username,
            case_id=case_id,
            group_id=group_id,
            decision=decision.value,
            deny_reason=deny_reason.value if deny_reason else None,
            query_hash=self.hash_query(query) if query else None,
            returned_chunks_count=returned_chunks_count,
            min_distance=min_distance,
            max_distance=max_distance,
            duration_ms=duration_ms,
        )
        
        await self._append(entry)
        return entry.event_id
    
    async def _append(self, entry: AuditEntry) -> None:
        """Append an entry to the log file (thread-safe)."""
        async with self._lock:
            async with aiofiles.open(self.log_path, "a") as f:
                await f.write(entry.to_json() + "\n")
    
    async def read_all(self) -> list[dict]:
        """
        Read all audit entries (for metrics aggregation).
        
        Note: This is for admin/metrics only, not for general use.
        """
        if not self.log_path.exists():
            return []
        
        entries = []
        async with aiofiles.open(self.log_path, "r") as f:
            async for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue  # Skip malformed lines
        return entries


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience alias
audit_logger = get_audit_logger
