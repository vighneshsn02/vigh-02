"""
Git integration tools for VIGH-02 AI AGENT.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from vigh_agent.tools.base import BaseTool
from vigh_agent.utils.path_utils import resolve_path


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Checks the Git status of the workspace (modified, staged, and untracked files)."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to git repository (default workspace root)."
            }
        }
    }

    def run(self, path: str = ".", workspace_root: Optional[str] = None) -> Dict[str, Any]:
        target = resolve_path(path, workspace_root)
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain", "-b"],
                cwd=str(target),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            if res.returncode != 0:
                return {"success": False, "error": f"Not a git repository or git error: {res.stderr.strip()}"}

            lines = res.stdout.splitlines()
            branch_info = lines[0] if lines else "## No branch"
            status_entries = lines[1:] if len(lines) > 1 else []

            return {
                "success": True,
                "branch": branch_info,
                "changes_count": len(status_entries),
                "changes": status_entries
            }
        except Exception as e:
            return {"success": False, "error": f"Git command failed: {str(e)}"}


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "Shows the working tree git diff for modified files."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to file or repository (default workspace root)."
            },
            "staged": {
                "type": "boolean",
                "description": "Whether to view staged changes (--cached)."
            }
        }
    }

    def run(self, path: str = ".", staged: bool = False, workspace_root: Optional[str] = None) -> Dict[str, Any]:
        target = resolve_path(path, workspace_root)
        cwd = str(target if target.is_dir() else target.parent)
        args = ["git", "diff"]
        if staged:
            args.append("--cached")
        if target.is_file():
            args.append(str(target.name))

        try:
            res = subprocess.run(
                args,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            return {
                "success": res.returncode == 0,
                "diff": res.stdout,
                "error": res.stderr if res.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": f"Git diff failed: {str(e)}"}
