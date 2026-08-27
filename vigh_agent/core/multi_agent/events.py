"""
Real-Time Event streaming definitions for VIGH-02 Multi-Agent Architecture.
Emitted across CLI, Web UI SSE stream, and external listeners to visualize
the collaborative agent swarm in action.
"""

import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class MultiAgentEvent(BaseModel):
    """Event emitted during multi-agent orchestration."""
    type: str  # 'phase_start', 'phase_end', 'agent_start', 'agent_thought', 'agent_token', 'agent_tool_start', 'agent_tool_end', 'agent_complete', 'task_update', 'diff', 'test_result', 'security_audit', 'review_result', 'autofix_start', 'autofix_iteration', 'autofix_complete', 'final_response', 'error', 'done'
    agent: str = "orchestrator"  # 'orchestrator', 'planner', 'coder', 'tester', 'reviewer', 'security'
    phase: Optional[str] = None  # 'planning', 'coding', 'verification', 'autofix', 'synthesis'
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)
