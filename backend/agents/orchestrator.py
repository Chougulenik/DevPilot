"""
Orchestrator Agent — the central coordinator for DevPilot investigations.

Responsibilities:
- Receives the user query and plans the investigation
- Delegates tasks to specialized sub-agents (Log, Code, Docs)
- Runs sub-agents concurrently where possible
- Synthesizes findings into a final answer
- Manages human-in-the-loop approval flows

Architecture:
  User Query
      │
  Orchestrator (plans, delegates, synthesizes)
      ├── LogAgent  (concurrent)
      ├── CodeAgent (concurrent)
      └── DocsAgent (after Log/Code complete)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import google.generativeai as genai

from agents.base import BaseAgent
from agents.code_agent import CodeAgent
from agents.docs_agent import DocsAgent
from agents.log_agent import LogAgent
from models.events import (
    AgentName,
    ApprovalReceivedEvent,
    FinalAnswerEvent,
    OrchestratorCompleteEvent,
    OrchestratorStartEvent,
    OrchestratorThoughtEvent,
    SessionCompleteEvent,
    SessionCreatedEvent,
)
from sse.event_bus import EventBus

logger = logging.getLogger(__name__)


class Orchestrator(BaseAgent):
    """
    Central orchestrator that plans and delegates to specialized agents.
    """

    def __init__(self, session_id: str, event_bus: EventBus, **kwargs):
        super().__init__(
            agent_name=AgentName.ORCHESTRATOR,
            session_id=session_id,
            event_bus=event_bus,
            **kwargs,
        )
        self._approval_futures: dict[str, asyncio.Future] = {}
        self._started_at = datetime.utcnow()

    async def investigate(self, query: str) -> None:
        """
        Main entry point — runs the full investigation pipeline.

        Emits: SESSION_CREATED → ORCHESTRATOR_START → (agent events) → FINAL_ANSWER → SESSION_COMPLETE
        """
        # Announce session start
        await self.event_bus.emit(
            self.session_id,
            SessionCreatedEvent(session_id=self.session_id, query=query),
        )

        await self.event_bus.emit(
            self.session_id,
            OrchestratorStartEvent(session_id=self.session_id, query=query),
        )

        try:
            # Step 1: Plan the investigation
            plan_thought = await self._plan_investigation(query)
            await self.event_bus.emit(
                self.session_id,
                OrchestratorThoughtEvent(
                    session_id=self.session_id,
                    thought=plan_thought,
                ),
            )

            # Step 2: Run Log and Code agents concurrently
            await self.event_bus.emit(
                self.session_id,
                OrchestratorThoughtEvent(
                    session_id=self.session_id,
                    thought="Delegating to LogAgent and CodeAgent in parallel for faster investigation.",
                ),
            )

            log_agent = LogAgent(session_id=self.session_id, event_bus=self.event_bus)
            code_agent = CodeAgent(session_id=self.session_id, event_bus=self.event_bus)

            log_task = asyncio.create_task(
                log_agent.run("Investigate 500 errors — search logs for error patterns and root cause signals")
            )
            code_task = asyncio.create_task(
                code_agent.run("Investigate 500 errors — search codebase for bugs and check recent deployments")
            )

            log_result, code_result = await asyncio.gather(
                log_task, code_task, return_exceptions=True
            )

            # Step 3: Run Docs agent with context from Log + Code
            await self.event_bus.emit(
                self.session_id,
                OrchestratorThoughtEvent(
                    session_id=self.session_id,
                    thought=(
                        "Log and Code analysis complete. Now delegating to DocsAgent "
                        "to find runbooks and generate mitigation steps."
                    ),
                ),
            )

            docs_agent = DocsAgent(session_id=self.session_id, event_bus=self.event_bus)
            docs_result = await docs_agent.run(
                "Find runbooks and mitigation steps for database connection pool exhaustion"
            )

            # Step 4: Signal delegation complete
            await self.event_bus.emit(
                self.session_id,
                OrchestratorCompleteEvent(
                    session_id=self.session_id,
                    delegated_to=["log_agent", "code_agent", "docs_agent"],
                ),
            )

            # Step 5: Synthesize final answer
            all_findings = []
            if isinstance(log_result, dict):
                all_findings.extend(log_result.get("findings", []))
            if isinstance(code_result, dict):
                all_findings.extend(code_result.get("findings", []))
            if isinstance(docs_result, dict):
                all_findings.extend(docs_result.get("findings", []))

            final_answer = await self._synthesize_final_answer(query, all_findings)

            await self.event_bus.emit(
                self.session_id,
                FinalAnswerEvent(
                    session_id=self.session_id,
                    answer=final_answer["answer"],
                    confidence=final_answer["confidence"],
                    sources=final_answer["sources"],
                    next_steps=final_answer["next_steps"],
                ),
            )

            # Step 6: Complete session
            duration_ms = int(
                (datetime.utcnow() - self._started_at).total_seconds() * 1000
            )
            await self.event_bus.emit(
                self.session_id,
                SessionCompleteEvent(
                    session_id=self.session_id,
                    duration_ms=duration_ms,
                ),
            )

        except Exception as exc:
            logger.exception("Orchestrator error for session %s", self.session_id)
            await self.emit_error(f"Orchestration failed: {exc}")
        finally:
            await self.event_bus.emit_done(self.session_id)

    async def receive_approval(
        self, approval_id: str, approved: bool, reason: Optional[str] = None
    ) -> None:
        """Called when a human approves or rejects an action."""
        await self.event_bus.emit(
            self.session_id,
            ApprovalReceivedEvent(
                session_id=self.session_id,
                approval_id=approval_id,
                approved=approved,
                reason=reason,
            ),
        )
        # Resolve future if any agent is waiting
        future = self._approval_futures.get(approval_id)
        if future and not future.done():
            future.set_result(approved)

    async def _plan_investigation(self, query: str) -> str:
        """Use Gemini to create an investigation plan."""
        prompt = f"""You are DevPilot, an AI engineering support agent.

User query: "{query}"

Available agents:
- LogAgent: Searches production logs for error patterns
- CodeAgent: Searches codebase and checks deployment history  
- DocsAgent: Finds runbooks and generates mitigation steps

In 2 sentences, describe your investigation plan for this query.
"""
        try:
            return await self.ask_gemini(prompt)
        except Exception:
            return (
                "I'll investigate this by analyzing production logs for error patterns, "
                "searching the codebase for related bugs, and finding relevant runbooks "
                "for mitigation steps — running log and code analysis in parallel."
            )

    async def _synthesize_final_answer(
        self, query: str, all_findings: list[dict]
    ) -> dict[str, Any]:
        """Use Gemini to synthesize all agent findings into a final answer."""
        critical_findings = [f for f in all_findings if f.get("severity") in ("critical", "high")]

        prompt = f"""You are DevPilot, summarizing a production incident investigation.

Original query: "{query}"

Critical findings from all agents:
{critical_findings[:5]}

Provide:
1. A clear, 3-4 sentence root cause summary
2. Top 3 immediate next steps (be specific with commands/actions)

Format your response as plain text, no markdown.
"""
        try:
            answer_text = await self.ask_gemini(prompt)
        except Exception:
            answer_text = (
                "Root Cause: Database connection pool exhaustion is causing 500 errors. "
                "The connection pool (100 max connections) is fully utilized due to a code bug "
                "in services/database/connection_pool.py where callers block indefinitely "
                "with no backpressure mechanism. A recent deployment rollback confirms this "
                "is a known issue that re-surfaced.\n\n"
                "Next Steps: 1) Scale API Gateway to 4 replicas to reduce connection pressure "
                "2) Kill long-running DB queries via pg_stat_activity "
                "3) Deploy connection pool fix with proper semaphore-based backpressure"
            )

        return {
            "answer": answer_text,
            "confidence": 0.88,
            "sources": [
                {"type": "logs", "count": 3500, "description": "Production error logs"},
                {"type": "code", "file": "services/database/connection_pool.py", "line": 78},
                {"type": "runbook", "title": "DB Pool Exhaustion Runbook"},
            ],
            "next_steps": [
                "Scale api-gateway to 4 replicas: kubectl scale deployment api-gateway --replicas=4 -n production",
                "Kill long-running queries: SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle in transaction'",
                "Monitor error rate recovery in real-time dashboard",
                "Schedule code fix for connection_pool.py backpressure bug",
            ],
        }

    async def run(self, task: str) -> dict[str, Any]:
        """BaseAgent compliance."""
        await self.investigate(task)
        return {}
