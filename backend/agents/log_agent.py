"""
Log Agent — specializes in searching and analyzing production logs.

Responsibilities:
- Searches logs for error patterns
- Identifies error rate spikes and timeline of events
- Correlates errors across services
- Returns structured findings to the orchestrator
"""
from __future__ import annotations

from typing import Any

from agents.base import BaseAgent
from models.events import AgentName, ToolName
from tools.implementations import search_logs


class LogAgent(BaseAgent):
    """Agent specialized in log analysis and error pattern detection."""

    def __init__(self, session_id: str, event_bus, **kwargs):
        super().__init__(
            agent_name=AgentName.LOG_AGENT,
            session_id=session_id,
            event_bus=event_bus,
            **kwargs,
        )

    async def run(self, task: str) -> dict[str, Any]:
        await self.emit_start(task)

        try:
            # Step 1: Initial thought
            await self.emit_thought(
                "I'll start by searching for recent error logs across all services "
                "to understand the scope and timing of the 500 errors."
            )

            # Step 2: Search for 500 errors
            logs_result = await self.call_tool(
                ToolName.SEARCH_LOGS,
                search_logs,
                query="level:ERROR status:500",
                service="api-gateway",
                time_range_minutes=120,
                limit=50,
            )

            await self.emit_thought(
                f"Found {logs_result['total_count']:,} log entries with a "
                f"{logs_result['error_rate']:.0%} error rate. "
                f"Top error is '{logs_result['top_errors'][0]['message']}' "
                f"occurring {logs_result['top_errors'][0]['count']:,} times. "
                f"Let me also check the auth service specifically."
            )

            # Step 3: Search auth service logs
            auth_logs = await self.call_tool(
                ToolName.SEARCH_LOGS,
                search_logs,
                query="level:ERROR ConnectionError OR TimeoutError",
                service="auth-service",
                time_range_minutes=120,
                limit=20,
            )

            # Step 4: Ask Gemini to synthesize findings
            await self.emit_thought(
                "I have enough log data. Let me analyze patterns and identify the root cause signal."
            )

            gemini_prompt = f"""You are a senior SRE analyzing production logs.

Log Analysis Summary:
- Total errors: {logs_result['total_count']:,}
- Error rate: {logs_result['error_rate']:.0%}
- Top errors: {logs_result['top_errors']}
- Services affected: {logs_result['services_affected']}

In 2-3 sentences, identify the most likely root cause based on these logs and what to investigate next.
"""
            analysis = await self.ask_gemini(gemini_prompt)

            self.findings = [
                {
                    "type": "error_rate",
                    "value": logs_result["error_rate"],
                    "description": f"Current error rate: {logs_result['error_rate']:.0%}",
                    "severity": "critical",
                },
                {
                    "type": "top_error",
                    "value": logs_result["top_errors"][0],
                    "description": "Most frequent error",
                    "severity": "critical",
                },
                {
                    "type": "services_affected",
                    "value": logs_result["services_affected"],
                    "description": "Impacted services",
                    "severity": "high",
                },
                {
                    "type": "gemini_analysis",
                    "value": analysis,
                    "description": "AI root cause analysis",
                    "severity": "info",
                },
            ]

            summary = (
                f"Log analysis complete. Error rate is {logs_result['error_rate']:.0%} "
                f"({logs_result['total_count']:,} total errors). "
                f"Primary error: database connection failures. "
                f"Services affected: {', '.join(logs_result['services_affected'])}."
            )

            await self.emit_complete(summary)
            return {"findings": self.findings, "summary": summary}

        except Exception as exc:
            await self.emit_error(str(exc))
            raise
