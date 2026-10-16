"""
Pydantic models for SSE event payloads.
All events emitted by the agent system use these structured schemas.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    """All possible event types emitted over the SSE stream."""
    # Session lifecycle
    SESSION_CREATED = "session_created"
    SESSION_COMPLETE = "session_complete"
    SESSION_ERROR = "session_error"

    # Orchestrator
    ORCHESTRATOR_START = "orchestrator_start"
    ORCHESTRATOR_THOUGHT = "orchestrator_thought"
    ORCHESTRATOR_COMPLETE = "orchestrator_complete"

    # Sub-agents
    AGENT_START = "agent_start"
    AGENT_THOUGHT = "agent_thought"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"

    # Tools
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"

    # Human-in-the-loop
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RECEIVED = "approval_received"

    # Connectivity
    HEARTBEAT = "heartbeat"
    FINAL_ANSWER = "final_answer"


class AgentName(str, Enum):
    """Named agents in the orchestration graph."""
    ORCHESTRATOR = "orchestrator"
    LOG_AGENT = "log_agent"
    CODE_AGENT = "code_agent"
    DOCS_AGENT = "docs_agent"


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETE = "complete"
    ERROR = "error"


class ToolName(str, Enum):
    SEARCH_LOGS = "search_logs"
    SEARCH_CODE = "search_code"
    GET_DEPLOYMENT = "get_deployment"
    SEARCH_DOCS = "search_docs"


# ---------------------------------------------------------------------------
# Base Event
# ---------------------------------------------------------------------------

class BaseEvent(BaseModel):
    """All SSE events inherit from this base."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    sequence: int = 0  # monotonically increasing per session


# ---------------------------------------------------------------------------
# Session Events
# ---------------------------------------------------------------------------

class SessionCreatedEvent(BaseEvent):
    event_type: EventType = EventType.SESSION_CREATED
    query: str


class SessionCompleteEvent(BaseEvent):
    event_type: EventType = EventType.SESSION_COMPLETE
    duration_ms: int


class SessionErrorEvent(BaseEvent):
    event_type: EventType = EventType.SESSION_ERROR
    error: str
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# Orchestrator Events
# ---------------------------------------------------------------------------

class OrchestratorStartEvent(BaseEvent):
    event_type: EventType = EventType.ORCHESTRATOR_START
    query: str


class OrchestratorThoughtEvent(BaseEvent):
    event_type: EventType = EventType.ORCHESTRATOR_THOUGHT
    thought: str


class OrchestratorCompleteEvent(BaseEvent):
    event_type: EventType = EventType.ORCHESTRATOR_COMPLETE
    delegated_to: list[str]


# ---------------------------------------------------------------------------
# Agent Events
# ---------------------------------------------------------------------------

class AgentStartEvent(BaseEvent):
    event_type: EventType = EventType.AGENT_START
    agent_name: AgentName
    task: str


class AgentThoughtEvent(BaseEvent):
    event_type: EventType = EventType.AGENT_THOUGHT
    agent_name: AgentName
    thought: str


class AgentCompleteEvent(BaseEvent):
    event_type: EventType = EventType.AGENT_COMPLETE
    agent_name: AgentName
    summary: str
    findings: list[dict[str, Any]] = Field(default_factory=list)


class AgentErrorEvent(BaseEvent):
    event_type: EventType = EventType.AGENT_ERROR
    agent_name: AgentName
    error: str


# ---------------------------------------------------------------------------
# Tool Events
# ---------------------------------------------------------------------------

class ToolCallEvent(BaseEvent):
    event_type: EventType = EventType.TOOL_CALL
    agent_name: AgentName
    tool_name: ToolName
    arguments: dict[str, Any]
    call_id: str = Field(default_factory=lambda: str(uuid4()))


class ToolResultEvent(BaseEvent):
    event_type: EventType = EventType.TOOL_RESULT
    agent_name: AgentName
    tool_name: ToolName
    call_id: str
    result: Any
    duration_ms: int


# ---------------------------------------------------------------------------
# Human-in-the-Loop Events
# ---------------------------------------------------------------------------

class ApprovalRequiredEvent(BaseEvent):
    event_type: EventType = EventType.APPROVAL_REQUIRED
    agent_name: AgentName
    action_description: str
    action_data: dict[str, Any]
    timeout_seconds: int = 300  # 5 min default timeout
    approval_id: str = Field(default_factory=lambda: str(uuid4()))


class ApprovalReceivedEvent(BaseEvent):
    event_type: EventType = EventType.APPROVAL_RECEIVED
    approval_id: str
    approved: bool
    reason: Optional[str] = None
    approved_by: str = "human"


# ---------------------------------------------------------------------------
# Misc Events
# ---------------------------------------------------------------------------

class HeartbeatEvent(BaseEvent):
    event_type: EventType = EventType.HEARTBEAT
    connected_clients: int = 1


class FinalAnswerEvent(BaseEvent):
    event_type: EventType = EventType.FINAL_ANSWER
    answer: str
    confidence: float  # 0.0 – 1.0
    sources: list[dict[str, Any]] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# HTTP Request/Response schemas
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="The investigation query")
    context: Optional[dict[str, Any]] = Field(default=None, description="Optional extra context")


class QueryResponse(BaseModel):
    session_id: str
    status: str = "started"
    stream_url: str


class ApprovalRequest(BaseModel):
    approval_id: str
    approved: bool
    reason: Optional[str] = None


class SessionState(BaseModel):
    session_id: str
    query: str
    status: AgentStatus
    events: list[dict[str, Any]] = Field(default_factory=list)
    started_at: str
    completed_at: Optional[str] = None
