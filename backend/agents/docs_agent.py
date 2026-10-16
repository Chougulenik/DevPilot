"""
Docs Agent — searches internal documentation, runbooks, and playbooks.

Responsibilities:
- Finds relevant runbooks for the identified issue
- Locates mitigation steps and commands
- Identifies if the issue has known solutions
- Surfaces approval-required actions (like kubectl commands)
"""
from __future__ import annotations

from typing import Any

from agents.base import BaseAgent
from models.events import AgentName, ApprovalRequiredEvent, ToolName
from tools.implementations import search_docs


class DocsAgent(BaseAgent):
    """Agent specialized in documentation and runbook lookup."""

    def __init__(self, session_id: str, event_bus, **kwargs):
        super().__init__(
            agent_name=AgentName.DOCS_AGENT,
            session_id=session_id,
            event_bus=event_bus,
            **kwargs,
        )
        self._pending_approval_id: str | None = None

    async def run(self, task: str) -> dict[str, Any]:
        await self.emit_start(task)

        try:
            await self.emit_thought(
                "I'll search our internal runbooks for database connection pool exhaustion "
                "and P1 incident response procedures to find mitigation steps."
            )

            # Step 1: Search runbooks
            docs_result = await self.call_tool(
                ToolName.SEARCH_DOCS,
                search_docs,
                query="database connection pool exhaustion mitigation",
                doc_type="runbook",
                limit=5,
            )

            await self.emit_thought(
                f"Found {len(docs_result['documents'])} relevant runbooks. "
                f"The top result is '{docs_result['documents'][0]['title']}' with high relevance. "
                f"It recommends scaling down non-critical consumers and running a kubectl scale command. "
                f"This is a privileged action — I need human approval before proceeding."
            )

            # Step 2: Synthesize mitigation steps with Gemini
            excerpts = "\n".join(
                f"- {d['title']}: {d['excerpt'][:200]}"
                for d in docs_result["documents"]
            )

            gemini_prompt = f"""You are an SRE responding to a P1 database connection pool exhaustion incident.

Relevant runbook excerpts:
{excerpts}

Provide a concise, prioritized list of 3 mitigation actions to resolve this immediately.
Format as: 1. [action] - [command if applicable]
"""
            mitigation_plan = await self.ask_gemini(gemini_prompt)

            # Step 3: Emit APPROVAL_REQUIRED for the kubectl command
            approval_event = ApprovalRequiredEvent(
                session_id=self.session_id,
                agent_name=self.agent_name,
                action_description="Scale down API Gateway replicas to reduce DB connection pressure",
                action_data={
                    "command": "kubectl scale deployment api-gateway --replicas=4 -n production",
                    "risk": "This will reduce throughput by 50% but should immediately free DB connections.",
                    "rollback": "kubectl scale deployment api-gateway --replicas=8 -n production",
                    "estimated_impact": "~50% traffic reduction for ~5 minutes while connections drain",
                },
            )
            await self.event_bus.emit(self.session_id, approval_event)
            self._pending_approval_id = approval_event.approval_id

            await self.emit_thought(
                f"Approval request sent (ID: {approval_event.approval_id[:8]}...). "
                f"Waiting for human confirmation before executing the kubectl scale command."
            )

            self.findings = [
                {
                    "type": "runbook_found",
                    "value": docs_result["documents"][0],
                    "description": "Primary runbook identified",
                    "severity": "info",
                },
                {
                    "type": "mitigation_plan",
                    "value": mitigation_plan,
                    "description": "AI-generated mitigation steps",
                    "severity": "info",
                },
                {
                    "type": "approval_required",
                    "value": {
                        "approval_id": approval_event.approval_id,
                        "action": approval_event.action_description,
                        "command": approval_event.action_data["command"],
                    },
                    "description": "kubectl scale command awaiting human approval",
                    "severity": "action_required",
                },
            ]

            summary = (
                f"Found {len(docs_result['documents'])} runbooks. Mitigation plan ready. "
                f"kubectl scale command requires human approval (ID: {approval_event.approval_id[:8]}...)."
            )

            await self.emit_complete(summary)
            return {
                "findings": self.findings,
                "summary": summary,
                "pending_approval_id": self._pending_approval_id,
            }

        except Exception as exc:
            await self.emit_error(str(exc))
            raise
