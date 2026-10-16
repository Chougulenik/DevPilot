"""
Base Agent class — provides common Gemini integration and SSE event emission.

Each specialized agent extends this class and implements `run()`.

The base class handles:
- Gemini SDK initialization
- Emitting typed SSE events via the event bus
- Tool call tracking (emit TOOL_CALL before, TOOL_RESULT after)
- Error handling and AGENT_ERROR emission
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

import google.generativeai as genai

from models.events import (
    AgentCompleteEvent,
    AgentErrorEvent,
    AgentName,
    AgentStartEvent,
    AgentThoughtEvent,
    ToolCallEvent,
    ToolName,
    ToolResultEvent,
)
from sse.event_bus import EventBus

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for all DevPilot agents.

    Subclasses must implement:
        async def run(self, task: str) -> dict[str, Any]
    """

    def __init__(
        self,
        agent_name: AgentName,
        session_id: str,
        event_bus: EventBus,
        model_name: str = "gemini-2.0-flash",
    ):
        self.agent_name = agent_name
        self.session_id = session_id
        self.event_bus = event_bus
        self.model_name = model_name
        self._model: Optional[genai.GenerativeModel] = None
        self.findings: list[dict[str, Any]] = []

    def _get_model(self) -> genai.GenerativeModel:
        """Lazy-init Gemini model."""
        if self._model is None:
            self._model = genai.GenerativeModel(self.model_name)
        return self._model

    async def emit_start(self, task: str) -> None:
        await self.event_bus.emit(
            self.session_id,
            AgentStartEvent(
                session_id=self.session_id,
                agent_name=self.agent_name,
                task=task,
            ),
        )

    async def emit_thought(self, thought: str) -> None:
        await self.event_bus.emit(
            self.session_id,
            AgentThoughtEvent(
                session_id=self.session_id,
                agent_name=self.agent_name,
                thought=thought,
            ),
        )

    async def emit_tool_call(
        self, tool_name: ToolName, arguments: dict[str, Any]
    ) -> str:
        """Emit TOOL_CALL event and return call_id for correlation."""
        event = ToolCallEvent(
            session_id=self.session_id,
            agent_name=self.agent_name,
            tool_name=tool_name,
            arguments=arguments,
        )
        await self.event_bus.emit(self.session_id, event)
        return event.call_id

    async def emit_tool_result(
        self,
        tool_name: ToolName,
        call_id: str,
        result: Any,
        duration_ms: int,
    ) -> None:
        await self.event_bus.emit(
            self.session_id,
            ToolResultEvent(
                session_id=self.session_id,
                agent_name=self.agent_name,
                tool_name=tool_name,
                call_id=call_id,
                result=result,
                duration_ms=duration_ms,
            ),
        )

    async def emit_complete(self, summary: str) -> None:
        await self.event_bus.emit(
            self.session_id,
            AgentCompleteEvent(
                session_id=self.session_id,
                agent_name=self.agent_name,
                summary=summary,
                findings=self.findings,
            ),
        )

    async def emit_error(self, error: str) -> None:
        await self.event_bus.emit(
            self.session_id,
            AgentErrorEvent(
                session_id=self.session_id,
                agent_name=self.agent_name,
                error=error,
            ),
        )

    async def call_tool(
        self,
        tool_name: ToolName,
        tool_fn,
        **kwargs,
    ) -> Any:
        """
        Execute a tool function with full SSE event emission.

        Emits TOOL_CALL → (executes) → TOOL_RESULT
        """
        call_id = await self.emit_tool_call(tool_name, kwargs)
        start_ms = time.monotonic()
        try:
            result = await tool_fn(**kwargs)
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            await self.emit_tool_result(tool_name, call_id, result, duration_ms)
            return result
        except Exception as exc:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            error_result = {"error": str(exc)}
            await self.emit_tool_result(tool_name, call_id, error_result, duration_ms)
            raise

    async def ask_gemini(self, prompt: str) -> str:
        """
        Call Gemini and return the text response.
        Runs in a thread pool to avoid blocking the event loop.
        """
        model = self._get_model()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: model.generate_content(prompt)
        )
        return response.text

    async def run(self, task: str) -> dict[str, Any]:
        """Override in subclasses."""
        raise NotImplementedError
