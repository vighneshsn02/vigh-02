"""
Central Tool Registry for VIGH-02 AI AGENT.
Provides schema generation, tool routing, and robust execution.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple

from vigh_agent.tools.base import BaseTool
from vigh_agent.tools.file_tools import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from vigh_agent.tools.code_scanner import CodeScannerTool
from vigh_agent.tools.search_tools import SearchCodeTool, OutlineSymbolsTool
from vigh_agent.tools.execution_tools import RunCommandTool
from vigh_agent.tools.git_tools import GitStatusTool, GitDiffTool


class ToolRegistry:
    """Manages available tools and executes calls."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        default_tools = [
            ReadFileTool(),
            WriteFileTool(),
            EditFileTool(),
            ListDirTool(),
            CodeScannerTool(),
            SearchCodeTool(),
            OutlineSymbolsTool(),
            RunCommandTool(),
            GitStatusTool(),
            GitDiffTool()
        ]
        for tool in default_tools:
            self.register(tool)

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns OpenAPI/OpenAI-compatible tool definitions."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def execute(self, tool_name: str, arguments: Dict[str, Any], workspace_root: Optional[str] = None) -> Dict[str, Any]:
        """Executes a named tool with provided kwargs."""
        tool = self._tools.get(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}"
            }

        # Inject workspace_root
        kwargs = arguments.copy()
        kwargs["workspace_root"] = workspace_root

        try:
            return tool.run(**kwargs)
        except TypeError as te:
            return {
                "success": False,
                "error": f"Invalid arguments for tool '{tool_name}': {str(te)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error during tool '{tool_name}' execution: {str(e)}"
            }

    def parse_fallback_tool_calls(self, text: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Extracts tool calls embedded in plain text output if the model didn't use native tool calling.
        Matches patterns like:
        ```tool_call
        {"name": "read_file", "arguments": {"path": "main.py"}}
        ```
        or `<tool_call>...</tool_call>` or `Action: tool_name\nAction Input: {...}`
        """
        calls: List[Tuple[str, Dict[str, Any]]] = []

        # 1. XML tag style <tool_call>...</tool_call>
        xml_matches = re.findall(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
        for match in xml_matches:
            try:
                data = json.loads(match.strip())
                name = data.get("name") or data.get("tool")
                args = data.get("arguments") or data.get("parameters") or {}
                if name and name in self._tools:
                    calls.append((name, args))
            except Exception:
                pass

        # 2. Markdown fenced tool_call
        fence_matches = re.findall(r"```(?:json)?\s*\{\s*\"name\"\s*:\s*\"([^\"]+)\"\s*,\s*\"arguments\"\s*:\s*(\{.*?\})\s*\}\s*```", text, re.DOTALL)
        for name, args_str in fence_matches:
            if name in self._tools:
                try:
                    args = json.loads(args_str)
                    calls.append((name, args))
                except Exception:
                    pass

        return calls


# Global registry singleton
tool_registry = ToolRegistry()
