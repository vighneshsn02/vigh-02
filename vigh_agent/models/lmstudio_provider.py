"""
LM Studio / LocalAI / OpenAI-compatible Provider for VIGH-02 AI AGENT.
"""

import json
import requests
from typing import List, Dict, Any, Generator, Optional
from vigh_agent.models.provider import BaseProvider, StreamChunk, ToolCall


class OpenAICompatibleProvider(BaseProvider):
    """
    Connects to LM Studio, LocalAI, vLLM, llama.cpp, or custom OpenAI-compatible server.
    """

    def __init__(
        self,
        name: str = "lmstudio",
        base_url: str = "http://127.0.0.1:1234/v1",
        model: str = "local-model",
        api_key: str = ""
    ):
        super().__init__(name, base_url, model)
        self.api_key = api_key or "not-needed-for-local"
        self.session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def health_check(self) -> bool:
        """Check if server is responsive."""
        try:
            r = self.session.get(f"{self.base_url}/models", headers=self._headers(), timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[Dict[str, Any]]:
        """List loaded models from the local server."""
        try:
            r = self.session.get(f"{self.base_url}/models", headers=self._headers(), timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                models = []
                for m in data.get("data", []):
                    m_id = m.get("id", "")
                    models.append({
                        "id": m_id,
                        "name": m_id,
                        "size": "Local / Loaded",
                        "family": "Local Server",
                        "provider": self.name,
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
        """Streams chat completions from the OpenAI-compatible endpoint."""
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if tools:
            # Standard OpenAI tools format
            payload["tools"] = tools

        try:
            with self.session.post(url, headers=self._headers(), json=payload, stream=True, timeout=(5.0, 120.0)) as response:
                if response.status_code != 200:
                    yield StreamChunk(
                        content=f"Error: Server returned status {response.status_code}: {response.text}",
                        done=True
                    )
                    return

                tool_calls_map: Dict[int, Dict[str, Any]] = {}

                for line in response.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:].strip()
                        if data_str == "[DONE]":
                            yield StreamChunk(content="", done=True)
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            
                            # Handle streaming tool calls
                            t_calls = delta.get("tool_calls", [])
                            for tc in t_calls:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_map:
                                    tool_calls_map[idx] = {
                                        "id": tc.get("id", f"call_{idx}"),
                                        "name": tc.get("function", {}).get("name", ""),
                                        "args": ""
                                    }
                                if tc.get("function", {}).get("name"):
                                    tool_calls_map[idx]["name"] = tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    tool_calls_map[idx]["args"] += tc["function"]["arguments"]

                            yield StreamChunk(content=content or "")
                        except Exception:
                            continue

                # Finalize any tool calls gathered
                final_tool_calls = []
                for _, t_data in tool_calls_map.items():
                    args_parsed = {}
                    try:
                        args_parsed = json.loads(t_data["args"])
                    except Exception:
                        args_parsed = {"raw": t_data["args"]}
                    final_tool_calls.append(ToolCall(
                        id=t_data["id"],
                        name=t_data["name"],
                        arguments=args_parsed
                    ))

                if final_tool_calls:
                    yield StreamChunk(content="", tool_calls=final_tool_calls, done=True)

        except requests.exceptions.ConnectionError:
            yield StreamChunk(
                content=f"\n[Error] Unable to connect to local server at {self.base_url}. Please ensure LM Studio / LocalAI is running and server is started.",
                done=True
            )
        except Exception as e:
            yield StreamChunk(
                content=f"\n[Error communicating with local server]: {str(e)}",
                done=True
            )
