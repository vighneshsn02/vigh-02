"""
Memory and Conversation History for VIGH-02 AI AGENT.
"""

from typing import List, Dict, Any, Optional
from vigh_agent.core.prompts import SYSTEM_PROMPT


class ConversationMemory:
    """Manages conversational context and message history."""

    def __init__(self, system_prompt: str = SYSTEM_PROMPT, max_messages: int = 50):
        self.system_prompt = system_prompt
        self.max_messages = max_messages
        self.messages: List[Dict[str, Any]] = []
        self.reset()

    def reset(self):
        """Clears history and re-inserts the system prompt."""
        self.messages = [
            {"role": "system", "content": self.system_prompt}
        ]

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
        self._trim_if_needed()

    def add_assistant_message(self, content: str, tool_calls: Optional[List[Any]] = None):
        msg: Dict[str, Any] = {"role": "assistant", "content": content or ""}
        if tool_calls:
            msg["tool_calls"] = [
                {
                    "id": getattr(tc, "id", f"call_{i}"),
                    "type": "function",
                    "function": {
                        "name": getattr(tc, "name", ""),
                        "arguments": getattr(tc, "arguments", {})
                    }
                }
                for i, tc in enumerate(tool_calls)
            ]
        self.messages.append(msg)
        self._trim_if_needed()

    def add_tool_response(self, tool_name: str, tool_call_id: str, result: Any):
        # Stringify result cleanly
        if isinstance(result, (dict, list)):
            import json
            content_str = json.dumps(result, indent=2)
        else:
            content_str = str(result)

        self.messages.append({
            "role": "tool",
            "name": tool_name,
            "tool_call_id": tool_call_id or tool_name,
            "content": content_str
        })
        self._trim_if_needed()

    def _trim_if_needed(self):
        """Keep system prompt intact and trim oldest user/assistant turns if history gets too long."""
        if len(self.messages) > self.max_messages:
            # Keep system prompt (index 0), drop oldest pair
            self.messages = [self.messages[0]] + self.messages[-(self.max_messages - 1):]

    def get_messages(self) -> List[Dict[str, Any]]:
        return list(self.messages)
