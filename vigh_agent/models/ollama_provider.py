"""
Ollama Provider for VIGH-02 AI AGENT.
Connects directly to local Ollama instance (100% offline).
"""

import json
import re
import requests
from typing import List, Dict, Any, Generator, Optional
from vigh_agent.models.provider import BaseProvider, StreamChunk, ToolCall


class OllamaProvider(BaseProvider):
    """Local Ollama LLM provider."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5-coder:7b"):
        super().__init__("ollama", base_url, model)
        self.session = requests.Session()

    def health_check(self) -> bool:
        """Verify Ollama is running and responsive."""
        try:
            r = self.session.get(f"{self.base_url}/api/tags", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[Dict[str, Any]]:
        """List all locally downloaded models."""
        try:
            r = self.session.get(f"{self.base_url}/api/tags", timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                models = []
                for m in data.get("models", []):
                    name = m.get("name", "")
                    details = m.get("details", {})
                    size_gb = m.get("size", 0) / (1024 * 1024 * 1024)
                    models.append({
                        "id": name,
                        "name": name,
                        "size": f"{size_gb:.1f} GB" if size_gb > 0 else "Cloud/Unknown",
                        "family": details.get("family", ""),
                        "parameter_size": details.get("parameter_size", ""),
                        "provider": "ollama",
                        "is_local": True
                    })
                return models
        except Exception:
            pass
        return []

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> Generator[StreamChunk, None, None]:
        """
        Streams response chunks from Ollama /api/chat.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        if tools:
            # Format tools for Ollama API
            payload["tools"] = tools

        url = f"{self.base_url}/api/chat"
        try:
            with self.session.post(url, json=payload, stream=True, timeout=(5.0, 120.0)) as response:
                if response.status_code != 200:
                    yield StreamChunk(
                        content=f"Error: Ollama returned status {response.status_code}: {response.text}",
                        done=True
                    )
                    return

                accumulated_text = ""
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk_json = json.loads(line.decode("utf-8"))
                        msg = chunk_json.get("message", {})
                        content = msg.get("content", "")
                        done = chunk_json.get("done", False)

                        tool_calls: List[ToolCall] = []
                        
                        # Check native tool calls from Ollama
                        raw_tools = msg.get("tool_calls", [])
                        for t in raw_tools:
                            fn = t.get("function", {})
                            name = fn.get("name", "")
                            args = fn.get("arguments", {})
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except Exception:
                                    args = {"raw": args}
                            if name:
                                tool_calls.append(ToolCall(id=t.get("id", name), name=name, arguments=args))

                        if content:
                            accumulated_text += content

                        yield StreamChunk(
                            content=content,
                            tool_calls=tool_calls,
                            done=done
                        )

                        if done:
                            break
                    except Exception as e:
                        continue

        except requests.exceptions.ConnectionError:
            yield StreamChunk(
                content=f"\n[Error] Unable to connect to local Ollama at {self.base_url}. Please ensure Ollama is running (`ollama serve`).",
                done=True
            )
        except Exception as e:
            yield StreamChunk(
                content=f"\n[Error communicating with Ollama]: {str(e)}",
                done=True
            )
