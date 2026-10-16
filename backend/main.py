"""
DevPilot Backend — FastAPI Application Entry Point

Endpoints:
  POST /query                  — Start a new investigation session
  GET  /stream/{session_id}    — SSE stream of agent events
  GET  /session/{session_id}   — Get full session state/history
  POST /approve/{session_id}   — Human-in-the-loop approval
  GET  /health                 — Health check

SSE Event Format:
  id: <event_id>
  event: <event_type>
  data: <json_payload>

"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from uuid import uuid4

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agents.orchestrator import Orchestrator
from models.events import ApprovalRequest, QueryRequest, QueryResponse, SessionState, AgentStatus
from sse.event_bus import event_bus

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

# In-memory session store (use Redis in production)
_sessions: dict[str, dict] = {}
_orchestrators: dict[str, Orchestrator] = {}


# ---------------------------------------------------------------------------
# App Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, clean up on shutdown."""
    logger.info("Starting DevPilot backend...")

    # Configure Gemini SDK
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini SDK configured")
    else:
        logger.warning(
            "GEMINI_API_KEY not set — AI responses will use fallbacks. "
            "Set it in .env to enable full Gemini integration."
        )

    # Start the SSE event bus (heartbeat, etc.)
    await event_bus.start()
    logger.info("EventBus started")

    yield  # App is running

    # Shutdown
    await event_bus.stop()
    logger.info("DevPilot backend stopped")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="DevPilot API",
    description="AI Engineering & Support Agent — SSE streaming backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "active_sessions": len(_sessions),
        "gemini_configured": bool(GEMINI_API_KEY),
    }


@app.post("/query", response_model=QueryResponse)
async def create_query(request: QueryRequest) -> QueryResponse:
    """
    Start a new investigation session.

    Returns a session_id and the SSE stream URL.
    The agent runs asynchronously — connect to /stream/{session_id} to receive events.
    """
    session_id = str(uuid4())
    from datetime import datetime

    # Register session
    _sessions[session_id] = {
        "session_id": session_id,
        "query": request.query,
        "status": AgentStatus.THINKING,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "completed_at": None,
    }

    # Create orchestrator
    orchestrator = Orchestrator(session_id=session_id, event_bus=event_bus)
    _orchestrators[session_id] = orchestrator

    # Launch investigation as background task (non-blocking)
    asyncio.create_task(
        _run_investigation(session_id, orchestrator, request.query)
    )

    logger.info("Session %s created for query: %s", session_id, request.query[:80])

    return QueryResponse(
        session_id=session_id,
        status="started",
        stream_url=f"/stream/{session_id}",
    )


async def _run_investigation(session_id: str, orchestrator: Orchestrator, query: str):
    """Background task that runs the full investigation."""
    try:
        await orchestrator.investigate(query)
        _sessions[session_id]["status"] = AgentStatus.COMPLETE
    except Exception as exc:
        logger.exception("Investigation failed for session %s", session_id)
        _sessions[session_id]["status"] = AgentStatus.ERROR
        _sessions[session_id]["error"] = str(exc)
    finally:
        from datetime import datetime
        _sessions[session_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"


@app.get("/stream/{session_id}")
async def stream_events(
    session_id: str,
    request: Request,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
):
    """
    SSE endpoint — streams structured agent events in real-time.

    Supports:
    - Reconnect via Last-Event-ID header
    - Heartbeat every 15s to keep connection alive
    - All event types defined in models/events.py

    Response headers:
        Content-Type: text/event-stream
        Cache-Control: no-cache
        X-Accel-Buffering: no  (disables nginx buffering)
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    async def event_generator():
        async for chunk in event_bus.subscribe(session_id, last_event_id=last_event_id):
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("Client disconnected from session %s", session_id)
                break
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/session/{session_id}", response_model=SessionState)
async def get_session(session_id: str) -> SessionState:
    """
    Get the current state and full event history for a session.

    Useful for:
    - Initial page load to reconstruct state
    - Polling fallback if SSE is unavailable
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session = _sessions[session_id]
    events = event_bus.get_replay_buffer(session_id)

    return SessionState(
        session_id=session_id,
        query=session["query"],
        status=session["status"],
        events=events,
        started_at=session["started_at"],
        completed_at=session.get("completed_at"),
    )


@app.post("/approve/{session_id}")
async def approve_action(session_id: str, body: ApprovalRequest):
    """
    Human-in-the-loop approval endpoint.

    Called when the frontend user approves or rejects a proposed action
    (e.g., a kubectl command surfaced by the DocsAgent).
    """
    if session_id not in _orchestrators:
        raise HTTPException(
            status_code=404,
            detail=f"No active orchestrator for session {session_id}",
        )

    orchestrator = _orchestrators[session_id]
    await orchestrator.receive_approval(
        approval_id=body.approval_id,
        approved=body.approved,
        reason=body.reason,
    )

    logger.info(
        "Approval %s for session %s: %s (reason: %s)",
        body.approval_id,
        session_id,
        "approved" if body.approved else "rejected",
        body.reason,
    )

    return {
        "status": "received",
        "approval_id": body.approval_id,
        "approved": body.approved,
    }


@app.get("/sessions")
async def list_sessions():
    """List all active sessions (debug endpoint)."""
    return {
        "sessions": list(_sessions.values()),
        "active_stream_sessions": event_bus.active_session_ids(),
    }
