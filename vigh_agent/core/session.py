"""
Session manager for VIGH-02 AI AGENT.
Maintains state for the current workspace, active model, and session statistics.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from vigh_agent.config import config
from vigh_agent.models.registry import model_registry
from vigh_agent.models.provider import BaseProvider
from vigh_agent.utils.path_utils import resolve_path


class AgentSession:
    """Encapsulates the runtime context for an active user session."""

    def __init__(self, workspace_path: Optional[str] = None):
        self.workspace_root = resolve_path(workspace_path or os.getcwd())
        self.provider_name: str = ""
        self.model_name: str = ""
        self.provider: Optional[BaseProvider] = None
        self.total_tool_calls: int = 0
        self.files_modified: int = 0
        self.mode: str = "single"  # "single" or "multi"
        
        self.initialize_provider()

    def set_mode(self, mode: str) -> str:
        """Sets execution mode to 'single' or 'multi'."""
        clean_mode = mode.lower().strip()
        if clean_mode in ("multi", "multi-agent", "swarm", "team"):
            self.mode = "multi"
        else:
            self.mode = "single"
        return self.mode

    def initialize_provider(self, provider_name: Optional[str] = None, model_name: Optional[str] = None):
        """Initializes or switches the active model provider."""
        if not provider_name or not model_name:
            p_name, m_name = model_registry.auto_detect_best_model()
            self.provider_name = provider_name or p_name
            self.model_name = model_name or m_name
        else:
            self.provider_name = provider_name
            self.model_name = model_name

        self.provider = model_registry.get_provider(self.provider_name, self.model_name)
        config.set("provider", self.provider_name)
        config.set("model", self.model_name)

    def set_workspace(self, path: str):
        """Updates the workspace directory."""
        target = resolve_path(path)
        if target.exists() and target.is_dir():
            self.workspace_root = target
            return True, f"Workspace switched to: {target}"
        return False, f"Directory does not exist: {path}"

    def get_status(self) -> Dict[str, Any]:
        """Returns session health and status info."""
        healthy = self.provider.health_check() if self.provider else False
        return {
            "agent_name": "VIGH-02 AI AGENT",
            "version": "2.0.0",
            "mode": self.mode,
            "workspace": str(self.workspace_root),
            "workspace_name": self.workspace_root.name,
            "provider": self.provider_name,
            "model": self.model_name,
            "provider_healthy": healthy,
            "total_tool_calls": self.total_tool_calls,
            "files_modified": self.files_modified
        }
