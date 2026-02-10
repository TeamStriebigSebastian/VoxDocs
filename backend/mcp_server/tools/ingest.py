"""
Ingest Transcript Tool for VoxDocs MCP Server

Internal tool for ingesting transcripts with semantic chunking.
"""

import time
from typing import Optional
import ollama

from ..config import get_settings
from ..concurrency import get_job_limiter, JobType, RateLimitError, TimeoutError
from ..audit import get_audit_logger, AuditDecision
from ..chroma_client import get_chroma_client
from ..embeddings import get_embedding_pipeline
from ..models import IngestResponse, SourceType


CHUNKING_PROMPT = """You are a text chunking assistant. Split the following transcript into semantic chunks.
Each chunk should be a self-contained unit of meaning (1-3 sentences typically).
Return ONLY a JSON array of strings, one per chunk. No explanation.

Transcript:
{text}

JSON array of chunks:"""


async def chunk_text_with_ollama(text: str) -> list[str]:
    """
    Use Ollama to semantically chunk text.
    
    Falls back to simple sentence splitting if Ollama fails.
    """
    settings = get_settings()
    
    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[{
                "role": "user",
                "content": CHUNKING_PROMPT.format(text=text),
            }],
            options={"temperature": 0.1},
        )
        
        # Parse JSON response
        import json
        content = response["message"]["content"].strip()
        
        # Try to extract JSON array
        if content.startswith("["):
            chunks = json.loads(content)
            if isinstance(chunks, list) and all(isinstance(c, str) for c in chunks):
                return [c.strip() for c in chunks if c.strip()]
    except Exception:
        pass
    
    # Fallback: simple sentence splitting
    return simple_chunk(text)


def simple_chunk(text: str, max_chars: int = 500) -> list[str]:
    """Simple fallback chunking by sentences."""
    import re
    
    # Split by sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += (" " if current_chunk else "") + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text]


async def execute_ingest(
    case_id: str,
    text: str,
    group_id: str,
    author: str,
    source_type: str = "whisper_transcript",
    source_ref: str = "",
) -> dict:
    """
    Execute the ingest_transcript tool.
    
    Flow:
    1. Semantic chunking via Ollama
    2. Embedding generation
    3. ChromaDB storage with metadata
    
    Returns:
        Ingestion result with chunk count and IDs
    """
    settings = get_settings()
    audit_logger = get_audit_logger()
    start_time = time.perf_counter()
    
    try:
        job_limiter = get_job_limiter()
        
        async def do_ingest():
            # 1. Chunk text
            chunks = await chunk_text_with_ollama(text)
            
            # 2. Generate embeddings
            embedder = get_embedding_pipeline()
            embeddings = embedder.encode(chunks)
            
            # 3. Prepare metadata for each chunk
            metadatas = []
            for i, chunk in enumerate(chunks):
                metadatas.append({
                    "case_id": case_id,
                    "group_id": group_id,
                    "author": author,
                    "source_type": source_type,
                    "source_ref": source_ref,
                    "version": 1,
                    "chunk_index": i,
                })
            
            # 4. Store in ChromaDB
            chroma = get_chroma_client()
            chunk_ids = chroma.add_chunks(
                texts=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            
            return chunks, chunk_ids
        
        try:
            chunks, chunk_ids = await job_limiter.run_with_limit(
                job_type=JobType.INGESTION,
                coro=do_ingest(),
            )
        except RateLimitError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await audit_logger.log(
                tool_name="ingest_transcript",
                username="system",
                decision=AuditDecision.DENY,
                duration_ms=duration_ms,
                case_id=case_id,
                group_id=group_id,
            )
            return e.to_dict()
        except TimeoutError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await audit_logger.log(
                tool_name="ingest_transcript",
                username="system",
                decision=AuditDecision.DENY,
                duration_ms=duration_ms,
                case_id=case_id,
                group_id=group_id,
            )
            return e.to_dict()
        
        # Build response
        response = IngestResponse(
            case_id=case_id,
            chunks_created=len(chunk_ids),
            chunk_ids=chunk_ids,
        )
        
        # Audit log
        duration_ms = (time.perf_counter() - start_time) * 1000
        await audit_logger.log(
            tool_name="ingest_transcript",
            username="system",
            decision=AuditDecision.ALLOW,
            duration_ms=duration_ms,
            case_id=case_id,
            group_id=group_id,
            returned_chunks_count=len(chunk_ids),
        )
        
        return response.model_dump()
    
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        await audit_logger.log(
            tool_name="ingest_transcript",
            username="system",
            decision=AuditDecision.DENY,
            duration_ms=duration_ms,
            case_id=case_id,
            group_id=group_id,
        )
        return {
            "error": "internal_error",
            "message": str(e),
        }
