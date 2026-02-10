"""
Pydantic Models for VoxDocs MCP Server

Defines request/response schemas for all tools.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class SourceType(str, Enum):
    """Source type for ingested documents."""
    WHISPER_TRANSCRIPT = "whisper_transcript"
    NOTE = "note"
    IMPORTED_DOC = "imported_doc"


# ============================================================================
# Chunk Models
# ============================================================================

class ChunkMetadata(BaseModel):
    """Metadata for a stored chunk."""
    chunk_id: str = Field(..., description="Unique chunk identifier (UUID)")
    case_id: str = Field(..., description="Associated case ID")
    group_id: str = Field(..., description="Associated group ID for RBAC")
    created_at: str = Field(..., description="Creation timestamp (ISO)")
    author: str = Field(..., description="Author identifier")
    source_type: SourceType = Field(default=SourceType.WHISPER_TRANSCRIPT)
    source_ref: Optional[str] = Field(default=None, description="Reference to source document")
    version: int = Field(default=1, description="Chunk version")
    pii_flag: Optional[bool] = Field(default=None, description="PII indicator")


class RetrievedChunk(BaseModel):
    """A chunk returned from retrieval."""
    chunk_id: str
    snippet: str = Field(..., max_length=300, description="Truncated content snippet")
    timestamp: str
    distance: float = Field(..., ge=0, le=2, description="Vector distance (lower = better)")
    relevance_score: float = Field(..., ge=0, le=1, description="1 - distance")


# ============================================================================
# Retrieve Tool Models
# ============================================================================

class PolicyApplied(BaseModel):
    """Policy information applied to retrieval."""
    top_k: int
    max_distance: float
    safe_mode: bool


class RetrieveResponse(BaseModel):
    """Response from retrieve_context_for_question."""
    case_id: str
    policy_applied: PolicyApplied
    data: list[RetrievedChunk]


# ============================================================================
# Citation Tool Models
# ============================================================================

class ClaimEvidence(BaseModel):
    """Evidence for a single claim."""
    claim: str
    supported: bool
    top_chunks: list[dict] = Field(default_factory=list, description="chunk_id + distance only")


class CitationResponse(BaseModel):
    """Response from assess_citation_feasibility."""
    case_id: str
    is_citable: bool
    coverage: float = Field(..., ge=0, le=1, description="Fraction of claims supported")
    evidence: list[ClaimEvidence]


# ============================================================================
# Ingest Tool Models
# ============================================================================

class IngestResponse(BaseModel):
    """Response from ingest_transcript."""
    case_id: str
    chunks_created: int
    chunk_ids: list[str]


# ============================================================================
# Metrics Tool Models
# ============================================================================

class UsageMetrics(BaseModel):
    """Aggregated usage metrics."""
    period_days: int
    total_requests: int
    requests_per_day: float
    deny_count: int
    deny_rate: float
    empty_result_count: int
    empty_result_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    deny_reason: Optional[str] = None
    retry_after_sec: Optional[float] = None
