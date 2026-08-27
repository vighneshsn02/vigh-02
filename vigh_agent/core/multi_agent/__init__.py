"""
VIGH-02 Multi-Agent Architecture Package.
"""

from vigh_agent.core.multi_agent.context import (
    AgentRole, TaskStatus, TaskItem, ExecutionPlan, TestReport,
    SecurityFinding, SecurityReport, ReviewIssue, ReviewReport,
    AutoFixAttempt, AgentMessage, SharedContext
)
from vigh_agent.core.multi_agent.events import MultiAgentEvent
from vigh_agent.core.multi_agent.prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT, CODER_SYSTEM_PROMPT,
    TESTER_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT, SECURITY_SYSTEM_PROMPT,
    AUTOFIX_SYSTEM_PROMPT, SYNTHESIS_SYSTEM_PROMPT
)
from vigh_agent.core.multi_agent.specialized_agents import (
    BaseSpecializedAgent, PlannerAgent, CoderAgent, TesterAgent,
    ReviewerAgent, SecurityAgent
)
from vigh_agent.core.multi_agent.orchestrator import MultiAgentOrchestrator

__all__ = [
    "AgentRole",
    "TaskStatus",
    "TaskItem",
    "ExecutionPlan",
    "TestReport",
    "SecurityFinding",
    "SecurityReport",
    "ReviewIssue",
    "ReviewReport",
    "AutoFixAttempt",
    "AgentMessage",
    "SharedContext",
    "MultiAgentEvent",
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "PLANNER_SYSTEM_PROMPT",
    "CODER_SYSTEM_PROMPT",
    "TESTER_SYSTEM_PROMPT",
    "REVIEWER_SYSTEM_PROMPT",
    "SECURITY_SYSTEM_PROMPT",
    "AUTOFIX_SYSTEM_PROMPT",
    "SYNTHESIS_SYSTEM_PROMPT",
    "BaseSpecializedAgent",
    "PlannerAgent",
    "CoderAgent",
    "TesterAgent",
    "ReviewerAgent",
    "SecurityAgent",
    "MultiAgentOrchestrator"
]
