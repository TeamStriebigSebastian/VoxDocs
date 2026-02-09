"""
Citation Feasibility Tool for VoxDocs MCP Server

Assesses whether claims can be cited from VoxDocs data.
Does NOT return actual content, only evidence metrics.
"""

import time
from typing import Optional
import ollama

from ..config import get_settings
from ..auth import authenticate_and_authorize, DenyReason
from ..concurrency import get_job_limiter, JobType, RateLimitError, TimeoutError
from ..audit import get_audit_logger, AuditDecision
from ..chroma_client import get_chroma_client
from ..embeddings import get_embedding_pipeline
from ..models import CitationResponse, ClaimEvidence


CLAIM_EXTRACTION_PROMPT = """Extract distinct factual claims from the following text.
Return ONLY a JSON array of claim strings. No explanation.
If there are no clear claims, return an empty array.

Text:
{text}

JSON array of claims:"""


async def extract_claims_with_ollama(text: str) -> list[str]:
    """
    Use Ollama to extract claims from text.
    
    Falls back to splitting by sentences if Ollama fails.
    """
    settings = get_settings()
    
    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[{
                "role": "user",
                "content": CLAIM_EXTRACTION_PROMPT.format(text=text),
            }],
            options={"temperature": 0.1},
        )
        
        # Parse JSON response
        import json
        content = response["message"]["content"].strip()
        
        # Try to extract JSON array
        if content.startswith("["):
            claims = json.loads(content)
            if isinstance(claims, list) and all(isinstance(c, str) for c in claims):
                return [c.strip() for c in claims if c.strip()]
    except Exception:
        pass
    
    # Fallback: treat each sentence as a claim
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip() and len(s) > 10]


async def execute_citation_check(
    username: str,
    api_token: str,
    case_id: str,
    claim_or_draft_answer: str,
) -> dict:
    """
    Execute the assess_citation_feasibility tool.
    
    Flow:
    1. Auth + RBAC
    2. Extract claims from input
    3. For each claim: query ChromaDB
    4. Calculate coverage
    5. Return evidence (NO content)
    
    Returns:
        Citation assessment with coverage score and evidence
    """
    settings = get_settings()
    audit_logger = get_audit_logger()
    start_time = time.perf_counter()
    
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
                tool_name="assess_citation_feasibility",
                username=username,
                decision=AuditDecision.DENY,
                duration_ms=duration_ms,
                case_id=case_id,
                deny_reason=deny_reason,
                query=claim_or_draft_answer,
            )
            return {
                "error": "access_denied",
                "message": f"Access denied: {deny_reason.value if deny_reason else 'unknown'}",
                "deny_reason": deny_reason.value if deny_reason else None,
            }
        
        # 2. Run with concurrency limit
        job_limiter = get_job_limiter()
        
        async def do_citation_check():
            # Extract claims
            claims = await extract_claims_with_ollama(claim_or_draft_answer)
            
            if not claims:
                return [], 0.0
            
            chroma = get_chroma_client()
            embedder = get_embedding_pipeline()
            
            evidence_list = []
            supported_count = 0
            
            for claim in claims:
                # Query for each claim
                query_embedding = embedder.encode_query(claim)
                
                results = chroma.query(
                    query_embedding=query_embedding,
                    n_results=3,
                    where={"case_id": case_id},
                    max_distance=settings.max_distance,
                )
                
                # Check if claim is supported
                top_chunks = []
                supported = False
                
                if results["ids"] and results["ids"][0]:
                    supported = True
                    supported_count += 1
                    
                    for i, chunk_id in enumerate(results["ids"][0]):
                        top_chunks.append({
                            "chunk_id": chunk_id,
                            "distance": round(results["distances"][0][i], 4),
                        })
                
                evidence_list.append(ClaimEvidence(
                    claim=claim[:100] + "…" if len(claim) > 100 else claim,
                    supported=supported,
                    top_chunks=top_chunks,
                ))
            
            coverage = supported_count / len(claims) if claims else 0.0
            return evidence_list, coverage
        
        try:
            evidence_list, coverage = await job_limiter.run_with_limit(
                job_type=JobType.RETRIEVAL,
                coro=do_citation_check(),
            )
        except RateLimitError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await audit_logger.log(
                tool_name="assess_citation_feasibility",
                username=username,
                decision=AuditDecision.DENY,
                duration_ms=duration_ms,
                case_id=case_id,
                query=claim_or_draft_answer,
            )
            return e.to_dict()
        except TimeoutError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await audit_logger.log(
                tool_name="assess_citation_feasibility",
                username=username,
                decision=AuditDecision.DENY,
                duration_ms=duration_ms,
                case_id=case_id,
                query=claim_or_draft_answer,
            )
            return e.to_dict()
        
        # Build response
        response = CitationResponse(
            case_id=case_id,
            is_citable=coverage >= 0.5,  # At least 50% of claims supported
            coverage=round(coverage, 2),
            evidence=evidence_list,
        )
        
        # Audit log
        duration_ms = (time.perf_counter() - start_time) * 1000
        await audit_logger.log(
            tool_name="assess_citation_feasibility",
            username=username,
            decision=AuditDecision.ALLOW,
            duration_ms=duration_ms,
            case_id=case_id,
            query=claim_or_draft_answer,
            returned_chunks_count=len(evidence_list),
        )
        
        return response.model_dump()
    
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        await audit_logger.log(
            tool_name="assess_citation_feasibility",
            username=username,
            decision=AuditDecision.DENY,
            duration_ms=duration_ms,
            case_id=case_id,
            query=claim_or_draft_answer,
        )
        return {
            "error": "internal_error",
            "message": str(e),
        }
