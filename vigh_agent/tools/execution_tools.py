"""
Terminal command execution tools for VIGH-02 AI AGENT.
"""

import os
import subprocess
from typing import Dict, Any, Optional

from vigh_agent.tools.base import BaseTool
from vigh_agent.utils.path_utils import resolve_path

DANGEROUS_COMMANDS = [
    "rm -rf /", "rmdir /s /q c:", "format ", "dd if=", ":(){ :|:& };:"
]


class RunCommandTool(BaseTool):
    name = "run_command"
    description = "Executes a terminal/shell command in the workspace directory and returns its output."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to run."
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command (default workspace root)."
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 60)."
            }
        },
        "required": ["command"]
    }

    def run(self, command: str, cwd: Optional[str] = None, timeout: int = 60, workspace_root: Optional[str] = None) -> Dict[str, Any]:
        # Safety check
        for dangerous in DANGEROUS_COMMANDS:
            if dangerous in command.lower():
                return {
                    "success": False,
                    "error": f"Refused to execute potentially destructive command: '{command}'"
                }

        target_cwd = resolve_path(cwd or ".", workspace_root)
        if not target_cwd.exists() or not target_cwd.is_dir():
            target_cwd = resolve_path(".", workspace_root)

        try:
            is_windows = os.name == "nt"
            res = subprocess.run(
                command,
                shell=True,
                cwd=str(target_cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                errors="replace"
            )

            stdout = res.stdout
            stderr = res.stderr
            exit_code = res.returncode

            # Truncate very long outputs
            max_chars = 10000
            if len(stdout) > max_chars:
                stdout = stdout[:max_chars] + f"\n... [Output truncated. {len(stdout) - max_chars} characters hidden]"
            if len(stderr) > max_chars:
                stderr = stderr[:max_chars] + f"\n... [Error output truncated]"

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "command": command,
                "cwd": str(target_cwd),
                "stdout": stdout,
                "stderr": stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "command": command,
                "error": f"Command timed out after {timeout} seconds."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute command: {str(e)}"
            }
