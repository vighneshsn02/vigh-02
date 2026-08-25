"""
Base Provider interface for VIGH-02 AI AGENT.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Generator, Optional, Union
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Represents a structured tool call from the model."""
    id: str = ""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class StreamChunk(BaseModel):
    """Represents a chunk during streaming generation."""
    content: str = ""
    tool_calls: List[ToolCall] = Field(default_factory=list)
    done: bool = False


class BaseProvider(ABC):
    """Abstract Base Class for LLM Providers."""

    def __init__(self, name: str, base_url: str, model: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model

    @abstractmethod
    def health_check(self) -> bool:
        """Checks if the provider endpoint is reachable."""
        pass

    @abstractmethod
    def list_models(self) -> List[Dict[str, Any]]:
        """Lists available models from the provider."""
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> Generator[StreamChunk, None, None]:
        """Streams chat response chunks from the model."""
        pass

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Synchronous full response generator."""
        full_content = ""
        collected_tools: List[ToolCall] = []
        
        for chunk in self.chat_stream(messages, tools, temperature, max_tokens):
            full_content += chunk.content
            if chunk.tool_calls:
                collected_tools.extend(chunk.tool_calls)
                
        return {
            "content": full_content,
            "tool_calls": collected_tools
        }
