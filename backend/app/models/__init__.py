"""Database models for Platform."""

from app.models.tenant import Tenant, Group
from app.models.user import User
from app.models.user_role import UserGroupRole, UserRole
from app.models.case import CaseFile, CaseStatus
from app.models.entry import Entry, AudioStatus
from app.models.entry_translation import EntryTranslation
from app.models.task import Task, TaskType, TaskStatus
from app.models.task_translation import TaskTranslation
from app.models.category import CategoryDefinition
from app.models.entry_chunk import EntryChunk
from app.models.audit import AuditEvent

# Deprecated / Legacy (Commented out to force breakage/refactor)
# from app.models.practice import Practice, Room
# from app.models.appointment import Appointment
# from app.models.nursing_transcription import NursingTranscription
# from app.models.audio import AudioRecording

__all__ = [
    "Tenant",
    "Group",
    "User",
    "UserGroupRole",
    "UserRole",
    "CaseFile",
    "CaseStatus",
    "Entry",
    "EntryTranslation",
    "AudioStatus",
    "Task",
    "TaskType",
    "TaskStatus",
    "CategoryDefinition",
    "EntryChunk",
    "AuditEvent",
]
