"""
Base tool interface for VIGH-02 AI AGENT.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert tool to OpenAI/Ollama tool specification format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
