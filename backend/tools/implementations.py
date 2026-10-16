"""
Mock tool implementations for DevPilot's agent system.

These simulate real production tools:
  - search_logs: Queries log aggregation systems (e.g., Elasticsearch, CloudWatch)
  - search_code: Searches the codebase for relevant functions/files
  - get_deployment: Retrieves deployment info and recent release history
  - search_docs: Searches internal documentation

In production, these would call real APIs. The mock data is designed to be
realistic for the demo scenario of "Production users getting 500 errors".
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any


async def search_logs(
    query: str,
    service: str = "api-gateway",
    time_range_minutes: int = 60,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Search production logs for error patterns.

    Args:
        query: Log search query (supports key:value and free text)
        service: Target service/component name
        time_range_minutes: How far back to search
        limit: Max number of log entries to return

    Returns:
        Dict with 'logs' (list), 'total_count', 'error_rate', 'top_errors'
    """
    # Simulate network latency
    await asyncio.sleep(random.uniform(0.3, 0.8))

    now = datetime.utcnow()
    logs = []

    # Generate realistic mock log entries for the 500 error scenario
    error_messages = [
        "ConnectionError: Failed to connect to database replica: ECONNREFUSED 10.0.1.45:5432",
        "TimeoutError: Query execution exceeded 30000ms limit on table 'user_sessions'",
        "UnhandledPromiseRejection: Cannot read property 'id' of null in auth middleware",
        "PostgreSQL error: remaining connection slots are reserved for non-replication superuser",
        "Redis connection lost: ENOTFOUND redis-cluster.internal",
        "JWT validation failed: token expired at 2026-10-16T07:23:11Z",
    ]

    for i in range(min(limit, 20)):
        ts = (now - timedelta(minutes=random.randint(0, time_range_minutes))).isoformat() + "Z"
        is_error = random.random() < 0.65  # 65% error rate during incident
        logs.append({
            "timestamp": ts,
            "level": "ERROR" if is_error else "WARN",
            "service": service,
            "trace_id": f"tr-{random.randint(100000, 999999)}",
            "message": random.choice(error_messages) if is_error else f"Slow response: {random.randint(800, 3000)}ms",
            "http_status": 500 if is_error else 200,
            "endpoint": random.choice(["/api/users", "/api/auth/login", "/api/data/fetch"]),
            "user_id": f"usr_{random.randint(1000, 9999)}" if random.random() > 0.3 else None,
        })

    return {
        "query": query,
        "service": service,
        "time_range_minutes": time_range_minutes,
        "total_count": random.randint(1200, 3500),
        "returned_count": len(logs),
        "error_rate": 0.64,
        "logs": sorted(logs, key=lambda x: x["timestamp"], reverse=True),
        "top_errors": [
            {"message": "ConnectionError: database replica unreachable", "count": 1842, "first_seen": "2026-10-16T06:12:00Z"},
            {"message": "TimeoutError: query exceeded 30s", "count": 934, "first_seen": "2026-10-16T06:15:00Z"},
            {"message": "Redis connection lost", "count": 412, "first_seen": "2026-10-16T06:48:00Z"},
        ],
        "services_affected": ["api-gateway", "auth-service", "user-service"],
    }


async def search_code(
    query: str,
    file_pattern: str = "**/*.py",
    max_results: int = 10,
) -> dict[str, Any]:
    """
    Search the codebase for relevant files, functions, and patterns.

    Args:
        query: Search query (function name, error pattern, etc.)
        file_pattern: Glob pattern to filter files
        max_results: Maximum number of results

    Returns:
        Dict with 'matches' list containing file paths, line numbers, snippets
    """
    await asyncio.sleep(random.uniform(0.2, 0.5))

    matches = [
        {
            "file": "services/auth_service/middleware.py",
            "line": 142,
            "function": "validate_jwt_token",
            "snippet": "def validate_jwt_token(token: str) -> Optional[dict]:\n    \"\"\"Validates JWT and returns payload. Returns None if expired/invalid.\"\"\"\n    try:\n        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])\n        return payload\n    except jwt.ExpiredSignatureError:\n        logger.warning('JWT expired: %s', token[:20])\n        return None  # BUG: Should raise 401, not return None silently",
            "relevance": 0.95,
        },
        {
            "file": "services/database/connection_pool.py",
            "line": 78,
            "function": "get_connection",
            "snippet": "async def get_connection(self):\n    \"\"\"Acquire a DB connection from pool.\"\"\"\n    if self._pool.size() >= MAX_POOL_SIZE:\n        # ISSUE: No proper backpressure, callers hang indefinitely\n        await self._pool.acquire()  # This blocks forever under load",
            "relevance": 0.91,
        },
        {
            "file": "api/routes/users.py",
            "line": 55,
            "function": "get_user_profile",
            "snippet": "user = await db.fetch_one(query)\nreturn UserProfile(**user)  # AttributeError if user is None",
            "relevance": 0.88,
        },
    ]

    return {
        "query": query,
        "file_pattern": file_pattern,
        "total_files_searched": 2847,
        "matches": matches[:max_results],
    }


async def get_deployment(
    service: str = "api-gateway",
    include_history: bool = True,
) -> dict[str, Any]:
    """
    Get deployment information and recent release history for a service.

    Args:
        service: Service name to query
        include_history: Whether to include last 5 deployments

    Returns:
        Dict with current deployment info, recent history, and health status
    """
    await asyncio.sleep(random.uniform(0.1, 0.3))

    history = []
    if include_history:
        versions = ["v2.8.3", "v2.8.2", "v2.8.1", "v2.8.0", "v2.7.9"]
        for i, v in enumerate(versions):
            ts = (datetime.utcnow() - timedelta(hours=i * 6)).isoformat() + "Z"
            history.append({
                "version": v,
                "deployed_at": ts,
                "deployed_by": random.choice(["ci-bot", "john.doe", "jane.smith"]),
                "commit_sha": f"{random.randint(0, 0xFFFFFF):06x}abc",
                "status": "rolled_back" if i == 1 else ("active" if i == 0 else "superseded"),
                "changelog": f"Release {v}: " + (
                    "HOTFIX: connection pool tuning — ROLLED BACK due to memory leak" if i == 1
                    else "Feature updates and bug fixes"
                ),
            })

    return {
        "service": service,
        "current_version": "v2.8.3",
        "environment": "production",
        "replicas": {"desired": 8, "ready": 6, "unavailable": 2},
        "health_status": "degraded",
        "last_successful_deploy": "2026-10-16T00:12:00Z",
        "incidents": [
            {
                "id": "INC-20241016-001",
                "started_at": "2026-10-16T06:10:00Z",
                "severity": "P1",
                "status": "active",
                "title": "API 500 errors — database connection pool exhaustion",
            }
        ],
        "recent_deployments": history,
        "resource_usage": {
            "cpu_percent": 94.2,
            "memory_percent": 87.8,
            "db_connections_used": 98,
            "db_connections_max": 100,
        },
    }


async def search_docs(
    query: str,
    doc_type: str = "runbook",
    limit: int = 5,
) -> dict[str, Any]:
    """
    Search internal documentation, runbooks, and incident playbooks.

    Args:
        query: Search query
        doc_type: Type of docs to search ('runbook', 'architecture', 'api', 'all')
        limit: Max results

    Returns:
        Dict with 'documents' list containing title, url, excerpt, relevance
    """
    await asyncio.sleep(random.uniform(0.15, 0.4))

    documents = [
        {
            "title": "Database Connection Pool Exhaustion — Runbook",
            "url": "https://wiki.internal/runbooks/db-pool-exhaustion",
            "doc_type": "runbook",
            "excerpt": "When connection pool usage exceeds 90%, immediately scale down non-critical consumers. Steps: 1) Identify top consumers via pg_stat_activity 2) Kill long-running queries 3) Rotate connection credentials if needed.",
            "relevance": 0.97,
            "last_updated": "2026-08-15",
        },
        {
            "title": "API Gateway Architecture — Service Mesh Design",
            "url": "https://wiki.internal/architecture/api-gateway",
            "doc_type": "architecture",
            "excerpt": "The API gateway uses a connection pool of max 100 connections shared across all replicas. Under heavy load, implement circuit breaker pattern using the ConnectionBreaker middleware.",
            "relevance": 0.89,
            "last_updated": "2026-09-02",
        },
        {
            "title": "P1 Incident Response Playbook",
            "url": "https://wiki.internal/runbooks/p1-incident-response",
            "doc_type": "runbook",
            "excerpt": "For P1 incidents: 1) Page on-call SRE immediately 2) Create war room channel 3) Begin mitigation within 15 minutes. Known mitigation for DB pool exhaustion: kubectl scale deployment api-gateway --replicas=4",
            "relevance": 0.85,
            "last_updated": "2026-10-01",
        },
    ]

    return {
        "query": query,
        "doc_type": doc_type,
        "total_searched": 1204,
        "documents": documents[:limit],
    }
