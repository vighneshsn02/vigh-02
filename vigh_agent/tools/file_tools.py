"""
File manipulation tools for VIGH-02 AI AGENT.
Supports reading, writing, snippet editing, listing directories, and undo snapshots.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from vigh_agent.tools.base import BaseTool
from vigh_agent.utils.path_utils import resolve_path, is_binary_file, format_file_size, is_ignored
from vigh_agent.utils.diff_utils import generate_diff, apply_snippet_edit, undo_manager


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Reads text contents of a file from any file path. Can specify start_line and end_line for specific sections."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or relative file path to read."
            },
            "start_line": {
                "type": "integer",
                "description": "Optional 1-indexed start line number to read from."
            },
            "end_line": {
                "type": "integer",
                "description": "Optional 1-indexed end line number to read to."
            }
        },
        "required": ["path"]
    }

    def run(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, workspace_root: Optional[str] = None) -> Dict[str, Any]:
        try:
            target = resolve_path(path, workspace_root)
            if not target.exists():
                return {"success": False, "error": f"File does not exist: {target}"}
            if not target.is_file():
                return {"success": False, "error": f"Path is a directory, not a file: {target}"}
            if is_binary_file(target):
                return {"success": False, "error": f"Cannot read binary file as text: {target.name}"}

            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s_line = max(1, start_line or 1)
            e_line = min(total_lines, end_line or total_lines)

            if s_line > total_lines:
                return {
                    "success": True,
                    "content": "",
                    "path": str(target),
                    "total_lines": total_lines,
                    "warning": f"start_line ({s_line}) exceeds total lines ({total_lines})."
                }

            selected_lines = lines[s_line - 1:e_line]
            content = "".join(selected_lines)

            # Include line numbering for clarity
            numbered_lines = []
            for i, line in enumerate(selected_lines, start=s_line):
                numbered_lines.append(f"{i:4d} | {line.rstrip()}")
            numbered_preview = "\n".join(numbered_lines)

            return {
                "success": True,
                "path": str(target),
                "total_lines": total_lines,
                "start_line": s_line,
                "end_line": e_line,
                "content": content,
                "numbered_preview": numbered_preview
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {str(e)}"}


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Writes or overwrites content to a specified file path. Automatically creates parent directories if they don't exist. Saves undo snapshot."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to write."
            },
            "content": {
                "type": "string",
                "description": "Full text content to write into the file."
            },
            "description": {
                "type": "string",
                "description": "Brief description of the change."
            }
        },
        "required": ["path", "content"]
    }

    def run(self, path: str, content: str, description: str = "File write", workspace_root: Optional[str] = None) -> Dict[str, Any]:
        try:
            target = resolve_path(path, workspace_root)
            prev_content = None
            is_new = not target.exists()

            if not is_new:
                if target.is_dir():
                    return {"success": False, "error": f"Cannot write to a directory path: {target}"}
                try:
                    with open(target, "r", encoding="utf-8", errors="replace") as f:
                        prev_content = f.read()
                except Exception:
                    prev_content = ""

            # Ensure parent directories exist
            target.parent.mkdir(parents=True, exist_ok=True)

            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            # Record undo history
            undo_manager.record_change(
                file_path=str(target),
                previous_content=prev_content,
                new_content=content,
                description=description
            )

            diff_str = generate_diff(prev_content or "", content, file_path=target.name) if prev_content else ""

            return {
                "success": True,
                "path": str(target),
                "is_new": is_new,
                "bytes_written": len(content.encode("utf-8")),
                "diff": diff_str,
                "message": f"Successfully {'created' if is_new else 'updated'} {target.name}"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to write file: {str(e)}"}


class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Modifies an existing file by replacing a specific code snippet with replacement code. Preserves the rest of the file and records an undo snapshot."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to edit."
            },
            "target_snippet": {
                "type": "string",
                "description": "Exact or near-exact snippet of code currently in the file to replace."
            },
            "replacement_snippet": {
                "type": "string",
                "description": "New code to replace the target snippet with."
            },
            "description": {
                "type": "string",
                "description": "Brief description of why this edit is being made."
            }
        },
        "required": ["path", "target_snippet", "replacement_snippet"]
    }

    def run(self, path: str, target_snippet: str, replacement_snippet: str, description: str = "Snippet edit", workspace_root: Optional[str] = None) -> Dict[str, Any]:
        try:
            target = resolve_path(path, workspace_root)
            if not target.exists():
                return {"success": False, "error": f"File does not exist: {target}"}
            if not target.is_file():
                return {"success": False, "error": f"Path is not a file: {target}"}

            with open(target, "r", encoding="utf-8", errors="replace") as f:
                original_content = f.read()

            success, updated_content, err = apply_snippet_edit(original_content, target_snippet, replacement_snippet)
            if not success:
                return {
                    "success": False,
                    "error": f"Failed to match target snippet in {target.name}. Details: {err}"
                }

            with open(target, "w", encoding="utf-8") as f:
                f.write(updated_content)

            undo_manager.record_change(
                file_path=str(target),
                previous_content=original_content,
                new_content=updated_content,
                description=description
            )

            diff_str = generate_diff(original_content, updated_content, file_path=target.name)

            return {
                "success": True,
                "path": str(target),
                "diff": diff_str,
                "message": f"Successfully edited {target.name}"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to edit file: {str(e)}"}


class ListDirTool(BaseTool):
    name = "list_dir"
    description = "Lists files and subdirectories at a given path, with file sizes, types, and counts."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list (default is workspace root / current dir)."
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether to list recursively."
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum depth for recursive listing (default 2)."
            }
        }
    }

    def run(self, path: str = ".", recursive: bool = False, max_depth: int = 2, workspace_root: Optional[str] = None) -> Dict[str, Any]:
        try:
            target = resolve_path(path, workspace_root)
            if not target.exists():
                return {"success": False, "error": f"Directory does not exist: {target}"}
            if not target.is_dir():
                return {"success": False, "error": f"Path is not a directory: {target}"}

            root_path = resolve_path(workspace_root or str(target))
            entries = []

            def _scan(cur_dir: Path, current_depth: int):
                if current_depth > max_depth:
                    return
                try:
                    for item in sorted(cur_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                        if is_ignored(item, root_path):
                            continue
                        rel = str(item.relative_to(target))
                        is_dir = item.is_dir()
                        size = format_file_size(item.stat().st_size) if not is_dir else "-"
                        entries.append({
                            "name": item.name,
                            "relative_path": rel,
                            "is_dir": is_dir,
                            "size": size,
                            "depth": current_depth
                        })
                        if is_dir and recursive:
                            _scan(item, current_depth + 1)
                except PermissionError:
                    pass

            _scan(target, 1)
            return {
                "success": True,
                "path": str(target),
                "total_items": len(entries),
                "entries": entries
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to list directory: {str(e)}"}
