"""
Autonomous Agent Loop for VIGH-02 AI AGENT.
Executes multi-step reasoning, streaming tokens, tool calling, and workspace mutations.
"""

import json
from typing import Dict, Any, List, Optional, Generator, Callable
from pydantic import BaseModel

from vigh_agent.core.session import AgentSession
from vigh_agent.core.memory import ConversationMemory
from vigh_agent.tools.registry import tool_registry
from vigh_agent.models.provider import ToolCall, StreamChunk


class AgentEvent(BaseModel):
    """Event emitted during agent execution."""
    type: str  # 'token', 'tool_start', 'tool_end', 'diff', 'error', 'done'
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class VighAgent:
    """Core autonomous coding agent."""

    def __init__(self, session: Optional[AgentSession] = None):
        self.session = session or AgentSession()
        self.memory = ConversationMemory()
        self.max_steps = 10

    def chat_stream(
        self,
        user_input: str,
        on_event: Optional[Callable[[AgentEvent], None]] = None
    ) -> Generator[AgentEvent, None, None]:
        """
        Executes a multi-step streaming agent loop in response to user input.
        """
        self.memory.add_user_message(user_input)
        workspace = str(self.session.workspace_root)
        provider = self.session.provider

        if not provider:
            evt = AgentEvent(type="error", content="No active LLM provider configured.")
            if on_event:
                on_event(evt)
            yield evt
            return

        current_step = 0
        tools_schema = tool_registry.get_schemas()

        while current_step < self.max_steps:
            current_step += 1
            messages = self.memory.get_messages()

            assistant_text = ""
            collected_tool_calls: List[ToolCall] = []

            # Stream from model
            for chunk in provider.chat_stream(messages, tools=tools_schema):
                if chunk.content:
                    assistant_text += chunk.content
                    evt = AgentEvent(type="token", content=chunk.content)
                    if on_event:
                        on_event(evt)
                    yield evt

                if chunk.tool_calls:
                    collected_tool_calls.extend(chunk.tool_calls)

            # Check if fallback tool calls exist in assistant text if native list is empty
            if not collected_tool_calls and assistant_text:
                fallback_calls = tool_registry.parse_fallback_tool_calls(assistant_text)
                for f_name, f_args in fallback_calls:
                    collected_tool_calls.append(ToolCall(id=f_name, name=f_name, arguments=f_args))

            # Record assistant turn in memory
            self.memory.add_assistant_message(assistant_text, tool_calls=collected_tool_calls if collected_tool_calls else None)

            # If no tool calls, model finished its response!
            if not collected_tool_calls:
                break

            # Execute all called tools
            for tool_call in collected_tool_calls:
                self.session.total_tool_calls += 1
                
                # Emit tool start event
                start_evt = AgentEvent(
                    type="tool_start",
                    content=f"Executing tool: {tool_call.name}",
                    data={"name": tool_call.name, "arguments": tool_call.arguments}
                )
                if on_event:
                    on_event(start_evt)
                yield start_evt

                # Execute tool
                tool_result = tool_registry.execute(
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                    workspace_root=workspace
                )

                # Check if tool resulted in a diff
                if isinstance(tool_result, dict) and tool_result.get("diff"):
                    self.session.files_modified += 1
                    diff_evt = AgentEvent(
                        type="diff",
                        content=tool_result["diff"],
                        data={"path": tool_result.get("path"), "message": tool_result.get("message")}
                    )
                    if on_event:
                        on_event(diff_evt)
                    yield diff_evt

                # Emit tool end event
                end_evt = AgentEvent(
                    type="tool_end",
                    content=f"Tool {tool_call.name} finished.",
                    data={"name": tool_call.name, "result": tool_result}
                )
                if on_event:
                    on_event(end_evt)
                yield end_evt

                # Feed result back into conversation memory for the model
                self.memory.add_tool_response(
                    tool_name=tool_call.name,
                    tool_call_id=tool_call.id,
                    result=tool_result
                )

        done_evt = AgentEvent(type="done", content="Agent step cycle complete.")
        if on_event:
            on_event(done_evt)
        yield done_evt

    def reset_conversation(self):
        """Resets agent conversation history."""
        self.memory.reset()
