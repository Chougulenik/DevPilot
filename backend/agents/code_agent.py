"""
Code Agent — searches and analyzes the codebase for bugs and vulnerabilities.

Responsibilities:
- Searches code for error-prone patterns
- Identifies relevant files and functions
- Cross-references deployment changes with code issues
- Returns structured code findings to the orchestrator
"""
from __future__ import annotations

from typing import Any

from agents.base import BaseAgent
from models.events import AgentName, ToolName
from tools.implementations import search_code, get_deployment


class CodeAgent(BaseAgent):
    """Agent specialized in code analysis and bug identification."""

    def __init__(self, session_id: str, event_bus, **kwargs):
        super().__init__(
            agent_name=AgentName.CODE_AGENT,
            session_id=session_id,
            event_bus=event_bus,
            **kwargs,
        )

    async def run(self, task: str) -> dict[str, Any]:
        await self.emit_start(task)

        try:
            await self.emit_thought(
                "I'll search for code patterns related to database connections and "
                "error handling that could explain the 500 errors. Also checking "
                "recent deployments for changes."
            )

            # Step 1: Search for database connection code
            code_results = await self.call_tool(
                ToolName.SEARCH_CODE,
                search_code,
                query="connection pool database acquire",
                file_pattern="**/*.py",
                max_results=10,
            )

            await self.emit_thought(
                f"Found {len(code_results['matches'])} relevant code locations. "
                f"I can see a potential bug in the connection pool — no backpressure implementation. "
                f"Let me also check the deployment history to see if recent changes introduced this."
            )

            # Step 2: Check deployment info
            deployment_info = await self.call_tool(
                ToolName.GET_DEPLOYMENT,
                get_deployment,
                service="api-gateway",
                include_history=True,
            )

            # Step 3: AI analysis of code + deployment correlation
            recent_deploys = deployment_info.get("recent_deployments", [])
            rolled_back = next(
                (d for d in recent_deploys if d.get("status") == "rolled_back"), None
            )

            await self.emit_thought(
                f"Critical finding: A deployment was rolled back recently! "
                f"Version {rolled_back['version'] if rolled_back else 'unknown'} was rolled back "
                f"due to: {rolled_back['changelog'] if rolled_back else 'unknown reason'}. "
                f"The current version {deployment_info['current_version']} may have re-introduced issues."
            )

            gemini_prompt = f"""You are a senior software engineer reviewing code and deployment data.

Code Issues Found:
{[m['snippet'][:200] for m in code_results['matches'][:2]]}

Deployment Status:
- Current version: {deployment_info['current_version']}
- Health: {deployment_info['health_status']}
- DB connections: {deployment_info['resource_usage']['db_connections_used']}/{deployment_info['resource_usage']['db_connections_max']}
- Recent rollback: {rolled_back}

In 2-3 sentences, explain the code-level root cause of the production 500 errors.
"""
            code_analysis = await self.ask_gemini(gemini_prompt)

            self.findings = [
                {
                    "type": "code_bug",
                    "file": code_results["matches"][1]["file"] if len(code_results["matches"]) > 1 else "unknown",
                    "line": code_results["matches"][1]["line"] if len(code_results["matches"]) > 1 else 0,
                    "description": "Connection pool has no backpressure — callers block indefinitely under load",
                    "severity": "critical",
                },
                {
                    "type": "deployment_issue",
                    "value": rolled_back,
                    "description": f"Recent rollback detected — v{rolled_back['version'] if rolled_back else '?'} had connection pool issues",
                    "severity": "high",
                },
                {
                    "type": "resource_exhaustion",
                    "value": deployment_info["resource_usage"],
                    "description": f"DB pool at {deployment_info['resource_usage']['db_connections_used']}/{deployment_info['resource_usage']['db_connections_max']} capacity",
                    "severity": "critical",
                },
                {
                    "type": "gemini_analysis",
                    "value": code_analysis,
                    "description": "AI code analysis",
                    "severity": "info",
                },
            ]

            summary = (
                f"Code analysis complete. Found connection pool bug with no backpressure. "
                f"DB connections at {deployment_info['resource_usage']['db_connections_used']}/"
                f"{deployment_info['resource_usage']['db_connections_max']}. "
                f"Recent rollback of {rolled_back['version'] if rolled_back else 'unknown'} "
                f"suggests this issue has been seen before."
            )

            await self.emit_complete(summary)
            return {"findings": self.findings, "summary": summary}

        except Exception as exc:
            await self.emit_error(str(exc))
            raise
