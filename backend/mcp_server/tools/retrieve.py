"""
Retrieve Context Tool for VoxDocs MCP Server

Public, read-only RAG endpoint with RBAC and similarity filtering.
"""

import time
from typing import Optional

from ..config import get_settings
from ..auth import authenticate_and_authorize, DenyReason
from ..concurrency import get_job_limiter, JobType, RateLimitError, TimeoutError
from ..audit import get_audit_logger, AuditDecision
from ..chroma_client import get_chroma_client
from ..embeddings import get_embedding_pipeline
from ..models import RetrieveResponse, RetrievedChunk, PolicyApplied


async def execute_retrieve(
    username: str,
    api_token: str,
    case_id: str,
    query: str,
) -> dict:
    """
    Execute the retrieve_context_for_question tool.
    
    Flow:
    1. Auth + RBAC
    2. Vector search with case_id filter
    3. Distance filter (<= MAX_DISTANCE)
    4. Snippet truncation
    5. Audit log
    
    Returns:
        Structured response with policy info and matching snippets
    """
    settings = get_settings()
    audit_logger = get_audit_logger()
    start_time = time.perf_counter()
    
    # Track for audit
    group_id: Optional[str] = None
    returned_chunks_count = 0
    min_distance: Optional[float] = None
    max_distance_found: Optional[float] = None
    
    try:
        # 1. Auth + RBAC
        success, user, deny_reason = await authenticate_and_authorize(
            username=username,
            api_token=api_token,
            case_id=case_id,
        )
        
        if not success:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await audit_logger.log(
                tool_name="retrieve_context_for_question",
                username=username,
                decision=AuditDecision.DENY,
                duration_ms=duration_ms,
                case_id=case_id,
                deny_reason=deny_reason,
                query=query,
            )
            return {
                "error": "access_denied",
                "message": f"Access denied: {deny_reason.value if deny_reason else 'unknown'}",
                "deny_reason": deny_reason.value if deny_reason else None,
            }
        
        # 2. Run with concurrency limit
        job_limiter = get_job_limiter()
        
        async def do_retrieve():
            chroma = get_chroma_client()
            embedder = get_embedding_pipeline()
            
            # Encode query
            query_embedding = embedder.encode_query(query)
            
            # Query ChromaDB
            results = chroma.query(
                query_embedding=query_embedding,
                n_results=settings.top_k,
                where={"case_id": case_id},
                max_distance=settings.max_distance,
            )
            
            return results
        
        try:
            results = await job_limiter.run_with_limit(
                job_type=JobType.RETRIEVAL,
                coro=do_retrieve(),
            )
        except RateLimitError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await audit_logger.log(
                tool_name="retrieve_context_for_question",
                username=username,
                decision=AuditDecision.DENY,
                duration_ms=duration_ms,
                case_id=case_id,
                deny_reason=DenyReason.INVALID_TOKEN,  # Use as rate limit placeholder
                query=query,
            )
            return e.to_dict()
        except TimeoutError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await audit_logger.log(
                tool_name="retrieve_context_for_question",
                username=username,
                decision=AuditDecision.DENY,
                duration_ms=duration_ms,
                case_id=case_id,
                query=query,
            )
            return e.to_dict()
        
        # 3. Build response
        chunks: list[RetrievedChunk] = []
        
        if results["ids"] and results["ids"][0]:
            distances = results["distances"][0]
            min_distance = min(distances) if distances else None
            max_distance_found = max(distances) if distances else None
            
            for i, chunk_id in enumerate(results["ids"][0]):
                doc = results["documents"][0][i]
                distance = results["distances"][0][i]
                metadata = results["metadatas"][0][i]
                
                # Truncate snippet
                snippet = doc[:settings.max_snippet_length]
                if len(doc) > settings.max_snippet_length:
                    snippet = snippet.rsplit(" ", 1)[0] + "…"
                
                chunks.append(RetrievedChunk(
                    chunk_id=chunk_id,
                    snippet=snippet,
                    timestamp=metadata.get("created_at", ""),
                    distance=round(distance, 4),
                    relevance_score=round(1 - distance, 4),
                ))
        
        returned_chunks_count = len(chunks)
        
        # 4. Build final response
        response = RetrieveResponse(
            case_id=case_id,
            policy_applied=PolicyApplied(
                top_k=settings.top_k,
                max_distance=settings.max_distance,
                safe_mode=settings.safe_mode,
            ),
            data=chunks,
        )
        
        # 5. Audit log
        duration_ms = (time.perf_counter() - start_time) * 1000
        await audit_logger.log(
            tool_name="retrieve_context_for_question",
            username=username,
            decision=AuditDecision.ALLOW,
            duration_ms=duration_ms,
            case_id=case_id,
            query=query,
            returned_chunks_count=returned_chunks_count,
            min_distance=min_distance,
            max_distance=max_distance_found,
        )
        
        return response.model_dump()
    
    except Exception as e:
        # Log unexpected errors
        duration_ms = (time.perf_counter() - start_time) * 1000
        await audit_logger.log(
            tool_name="retrieve_context_for_question",
            username=username,
            decision=AuditDecision.DENY,
            duration_ms=duration_ms,
            case_id=case_id,
            query=query,
        )
        return {
            "error": "internal_error",
            "message": str(e),
        }
