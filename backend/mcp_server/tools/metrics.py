"""
Usage Metrics Tool for VoxDocs MCP Server

Admin-only tool for aggregating audit log metrics.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Optional
import statistics

from ..config import get_settings
from ..auth import authenticate_and_authorize, DenyReason
from ..audit import get_audit_logger, AuditDecision
from ..models import UsageMetrics


async def execute_get_metrics(
    username: str,
    api_token: str,
    period_days: int = 7,
) -> dict:
    """
    Execute the get_usage_metrics tool.
    
    Aggregates from audit log:
    - Requests per day
    - Deny rate
    - Empty result rate
    - p50, p95, p99 latency
    
    Returns:
        Aggregated usage metrics
    """
    settings = get_settings()
    audit_logger = get_audit_logger()
    start_time = time.perf_counter()
    
    try:
        # 1. Auth + require admin
        success, user, deny_reason = await authenticate_and_authorize(
            username=username,
            api_token=api_token,
            require_admin=True,
        )
        
        if not success:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await audit_logger.log(
                tool_name="get_usage_metrics",
                username=username,
                decision=AuditDecision.DENY,
                duration_ms=duration_ms,
                deny_reason=deny_reason,
            )
            return {
                "error": "access_denied",
                "message": f"Access denied: {deny_reason.value if deny_reason else 'unknown'}",
                "deny_reason": deny_reason.value if deny_reason else None,
            }
        
        # 2. Read audit log entries
        entries = await audit_logger.read_all()
        
        # 3. Filter to period
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        cutoff_str = cutoff.isoformat()
        
        period_entries = [
            e for e in entries
            if e.get("timestamp", "") >= cutoff_str
        ]
        
        if not period_entries:
            return UsageMetrics(
                period_days=period_days,
                total_requests=0,
                requests_per_day=0.0,
                deny_count=0,
                deny_rate=0.0,
                empty_result_count=0,
                empty_result_rate=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
            ).model_dump()
        
        # 4. Calculate metrics
        total_requests = len(period_entries)
        requests_per_day = total_requests / period_days
        
        deny_count = sum(1 for e in period_entries if e.get("decision") == "deny")
        deny_rate = deny_count / total_requests if total_requests > 0 else 0.0
        
        empty_result_count = sum(
            1 for e in period_entries
            if e.get("decision") == "allow" and e.get("returned_chunks_count", 0) == 0
        )
        empty_result_rate = empty_result_count / total_requests if total_requests > 0 else 0.0
        
        # Latencies
        latencies = [e.get("duration_ms", 0) for e in period_entries]
        latencies = [l for l in latencies if l > 0]
        
        if latencies:
            latencies_sorted = sorted(latencies)
            p50 = latencies_sorted[int(len(latencies_sorted) * 0.50)]
            p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
            p99 = latencies_sorted[min(int(len(latencies_sorted) * 0.99), len(latencies_sorted) - 1)]
        else:
            p50 = p95 = p99 = 0.0
        
        response = UsageMetrics(
            period_days=period_days,
            total_requests=total_requests,
            requests_per_day=round(requests_per_day, 2),
            deny_count=deny_count,
            deny_rate=round(deny_rate, 4),
            empty_result_count=empty_result_count,
            empty_result_rate=round(empty_result_rate, 4),
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2),
        )
        
        # Audit log
        duration_ms = (time.perf_counter() - start_time) * 1000
        await audit_logger.log(
            tool_name="get_usage_metrics",
            username=username,
            decision=AuditDecision.ALLOW,
            duration_ms=duration_ms,
        )
        
        return response.model_dump()
    
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        await audit_logger.log(
            tool_name="get_usage_metrics",
            username=username,
            decision=AuditDecision.DENY,
            duration_ms=duration_ms,
        )
        return {
            "error": "internal_error",
            "message": str(e),
        }
