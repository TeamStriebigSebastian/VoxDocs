"""
Tests for VoxDocs MCP Server Audit Logger
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path

from mcp_server.audit import (
    AuditLogger,
    AuditDecision,
    AuditEntry,
)
from mcp_server.auth import DenyReason


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        return Path(f.name)


@pytest.mark.asyncio
async def test_log_allow_entry(temp_log_file):
    """Test logging an allowed request."""
    logger = AuditLogger(log_path=temp_log_file)
    
    event_id = await logger.log(
        tool_name="retrieve_context_for_question",
        username="test_user",
        decision=AuditDecision.ALLOW,
        duration_ms=100.5,
        case_id="case123",
        query="test query",
        returned_chunks_count=3,
        min_distance=0.1,
        max_distance=0.25,
    )
    
    assert event_id is not None
    
    # Read and verify
    entries = await logger.read_all()
    assert len(entries) == 1
    
    entry = entries[0]
    assert entry["event_id"] == event_id
    assert entry["tool_name"] == "retrieve_context_for_question"
    assert entry["username"] == "test_user"
    assert entry["decision"] == "allow"
    assert entry["case_id"] == "case123"
    assert entry["returned_chunks_count"] == 3
    assert entry["min_distance"] == 0.1
    assert entry["max_distance"] == 0.25


@pytest.mark.asyncio
async def test_log_deny_entry(temp_log_file):
    """Test logging a denied request."""
    logger = AuditLogger(log_path=temp_log_file)
    
    event_id = await logger.log(
        tool_name="retrieve_context_for_question",
        username="bad_user",
        decision=AuditDecision.DENY,
        duration_ms=5.2,
        case_id="case123",
        deny_reason=DenyReason.INVALID_TOKEN,
    )
    
    entries = await logger.read_all()
    assert len(entries) == 1
    
    entry = entries[0]
    assert entry["decision"] == "deny"
    assert entry["deny_reason"] == "invalid_token"


@pytest.mark.asyncio
async def test_query_hash_privacy(temp_log_file):
    """Test that query is hashed, not stored in plaintext."""
    logger = AuditLogger(log_path=temp_log_file)
    
    query = "sensitive patient information"
    await logger.log(
        tool_name="test_tool",
        username="test_user",
        decision=AuditDecision.ALLOW,
        duration_ms=10.0,
        query=query,
    )
    
    entries = await logger.read_all()
    entry = entries[0]
    
    # Query should be hashed
    assert "query_hash" in entry
    assert entry["query_hash"] != query
    assert len(entry["query_hash"]) == 64  # SHA256 hex length


@pytest.mark.asyncio
async def test_append_only(temp_log_file):
    """Test that log is append-only."""
    logger = AuditLogger(log_path=temp_log_file)
    
    # Log multiple entries
    for i in range(3):
        await logger.log(
            tool_name=f"tool_{i}",
            username="test_user",
            decision=AuditDecision.ALLOW,
            duration_ms=float(i),
        )
    
    entries = await logger.read_all()
    assert len(entries) == 3
    
    # Verify order preserved
    for i, entry in enumerate(entries):
        assert entry["tool_name"] == f"tool_{i}"


@pytest.mark.asyncio
async def test_concurrent_logging(temp_log_file):
    """Test that concurrent logging is safe."""
    logger = AuditLogger(log_path=temp_log_file)
    
    async def log_entry(i: int):
        await logger.log(
            tool_name=f"tool_{i}",
            username="test_user",
            decision=AuditDecision.ALLOW,
            duration_ms=float(i),
        )
    
    # Log 10 entries concurrently
    await asyncio.gather(*[log_entry(i) for i in range(10)])
    
    entries = await logger.read_all()
    assert len(entries) == 10


@pytest.mark.asyncio
async def test_empty_log_read(temp_log_file):
    """Test reading from empty log file."""
    # Delete the file to simulate fresh start
    temp_log_file.unlink()
    
    logger = AuditLogger(log_path=temp_log_file)
    entries = await logger.read_all()
    
    assert entries == []


def test_hash_query_deterministic():
    """Test that query hashing is deterministic."""
    query = "test query"
    hash1 = AuditLogger.hash_query(query)
    hash2 = AuditLogger.hash_query(query)
    
    assert hash1 == hash2
    assert len(hash1) == 64


def test_generate_event_id_unique():
    """Test that event IDs are unique."""
    ids = [AuditLogger.generate_event_id() for _ in range(100)]
    assert len(set(ids)) == 100  # All unique
