"""
VoxDocs MCP Server - FastMCP Entry Point

Run with: python -m mcp_server.server
"""

import asyncio
from mcp.server.fastmcp import FastMCP

from .config import get_settings
from .auth import authenticate_and_authorize
from .concurrency import job_limiter
from .audit import audit_logger


# Initialize FastMCP server
settings = get_settings()
mcp = FastMCP(
    name=settings.server_name,
    version=settings.server_version,
)


# ============================================================================
# Tool: retrieve_context_for_question (public, read-only)
# ============================================================================
@mcp.tool()
async def retrieve_context_for_question(
    username: str,
    api_token: str,
    case_id: str,
    query: str,
) -> dict:
    """
    Retrieve relevant context chunks for a question from VoxDocs.
    
    This is a read-only RAG endpoint that returns minimal, citable snippets
    from the VoxDocs database filtered by case_id.
    
    Args:
        username: User identifier for authentication
        api_token: API token for authentication  
        case_id: Case ID to filter results
        query: Natural language query to search for
        
    Returns:
        Structured response with policy info and matching snippets
    """
    from .tools.retrieve import execute_retrieve
    
    return await execute_retrieve(
        username=username,
        api_token=api_token,
        case_id=case_id,
        query=query,
    )


# ============================================================================
# Tool: assess_citation_feasibility (public, read-only)
# ============================================================================
@mcp.tool()
async def assess_citation_feasibility(
    username: str,
    api_token: str,
    case_id: str,
    claim_or_draft_answer: str,
) -> dict:
    """
    Assess whether a claim or draft answer can be cited from VoxDocs data.
    
    Extracts claims from the input, checks each against the database,
    and returns coverage/evidence metrics WITHOUT returning actual content.
    
    Args:
        username: User identifier for authentication
        api_token: API token for authentication
        case_id: Case ID to check against
        claim_or_draft_answer: The claim or draft answer to verify
        
    Returns:
        Citation feasibility assessment with coverage score
    """
    from .tools.citation import execute_citation_check
    
    return await execute_citation_check(
        username=username,
        api_token=api_token,
        case_id=case_id,
        claim_or_draft_answer=claim_or_draft_answer,
    )


# ============================================================================
# Tool: ingest_transcript (internal only)
# ============================================================================
@mcp.tool()
async def ingest_transcript(
    case_id: str,
    text: str,
    group_id: str,
    author: str,
    source_type: str = "whisper_transcript",
    source_ref: str = "",
    categories: list[str] = None,
) -> dict:
    """
    Ingest a transcript into the VoxDocs RAG database.
    
    This is an INTERNAL tool for ingestion workflows only.
    Performs semantic chunking and stores in ChromaDB with metadata.
    
    Args:
        case_id: Case ID to associate with the transcript
        text: Raw transcript text to ingest
        group_id: Group ID for RBAC
        author: Author identifier
        source_type: Type of source (whisper_transcript, note, imported_doc)
        source_ref: Optional reference to source document
        categories: Optional list of categories to associate with chunks
        
    Returns:
        Ingestion result with chunk count
    """
    from .tools.ingest import execute_ingest
    
    return await execute_ingest(
        case_id=case_id,
        text=text,
        group_id=group_id,
        author=author,
        source_type=source_type,
        source_ref=source_ref,
        categories=categories,
    )


# ============================================================================
# Tool: get_usage_metrics (internal/admin)
# ============================================================================
@mcp.tool()
async def get_usage_metrics(
    username: str,
    api_token: str,
) -> dict:
    """
    Get aggregated usage metrics from the audit log.
    
    Admin-only tool that returns request counts, deny rates,
    empty result rates, and latency percentiles.
    
    Args:
        username: Admin user identifier
        api_token: API token for authentication
        
    Returns:
        Aggregated usage metrics
    """
    from .tools.metrics import execute_get_metrics
    
    return await execute_get_metrics(
        username=username,
        api_token=api_token,
    )


# ============================================================================
# Health check resource
# ============================================================================
@mcp.resource("health://status")
async def health_status() -> str:
    """Health check endpoint."""
    return "ok"


# ============================================================================
# Main entry point
# ============================================================================
def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
