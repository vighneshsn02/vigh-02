"""
Diff and patch utilities for VIGH-02 AI AGENT.
Provides unified diff generation, rich terminal rendering, and patch application.
"""

import difflib
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax


def generate_diff(old_content: str, new_content: str, file_path: str = "file") -> str:
    """
    Generates a standard unified diff string between old and new text content.
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm=""
    )
    return "\n".join(diff)


def create_rich_diff(diff_str: str) -> Text:
    """
    Parses a unified diff string into rich styled Text with red/green/cyan colors.
    """
    text = Text()
    for line in diff_str.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            text.append(line + "\n", style="bold cyan")
        elif line.startswith("@@"):
            text.append(line + "\n", style="bold magenta")
        elif line.startswith("+"):
            text.append(line + "\n", style="green")
        elif line.startswith("-"):
            text.append(line + "\n", style="red")
        else:
            text.append(line + "\n", style="dim")
    return text


def apply_snippet_edit(original_content: str, target_snippet: str, replacement_snippet: str) -> Tuple[bool, str, str]:
    """
    Replaces a target snippet in the original content.
    Tries exact match first, then normalized newline match, then whitespace-trimmed fallback.
    Returns: (success: bool, updated_content: str, error_message: str)
    """
    # 1. Exact match
    if target_snippet in original_content:
        # Check if it appears multiple times
        count = original_content.count(target_snippet)
        if count == 1:
            updated = original_content.replace(target_snippet, replacement_snippet, 1)
            return True, updated, ""
        elif count > 1:
            # If multiple, replace first or warn
            updated = original_content.replace(target_snippet, replacement_snippet, 1)
            return True, updated, f"Warning: Snippet matched {count} times. Replaced first occurrence."

    # 2. Normalized newlines match (\r\n vs \n)
    norm_original = original_content.replace("\r\n", "\n")
    norm_target = target_snippet.replace("\r\n", "\n")
    norm_replacement = replacement_snippet.replace("\r\n", "\n")

    if norm_target in norm_original:
        updated = norm_original.replace(norm_target, norm_replacement, 1)
        return True, updated, ""

    # 3. Line-by-line fuzzy trim match
    orig_lines = original_content.splitlines()
    target_lines = [l.strip() for l in target_snippet.splitlines() if l.strip()]

    if not target_lines:
        return False, original_content, "Target snippet is empty."

    # Search for matching sequence of non-empty lines
    for i in range(len(orig_lines) - len(target_lines) + 1):
        match = True
        for j, t_line in enumerate(target_lines):
            if orig_lines[i + j].strip() != t_line:
                match = False
                break
        if match:
            # Found slice in orig_lines from i to i + len(target_lines)
            before = orig_lines[:i]
            after = orig_lines[i + len(target_lines):]
            rep_lines = replacement_snippet.splitlines()
            new_lines = before + rep_lines + after
            return True, "\n".join(new_lines), ""

    return False, original_content, "Could not find the target code snippet in file content."


class UndoHistory:
    """
    Maintains an in-memory stack of file snapshots for instant undo/rollback.
    """
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self._history: List[Dict[str, Any]] = []

    def record_change(self, file_path: str, previous_content: Optional[str], new_content: Optional[str], description: str = ""):
        """
        Record a file change. If previous_content is None, file was newly created.
        If new_content is None, file was deleted.
        """
        self._history.append({
            "file_path": file_path,
            "previous_content": previous_content,
            "new_content": new_content,
            "description": description
        })
        if len(self._history) > self.max_history:
            self._history.pop(0)

    def can_undo(self) -> bool:
        return len(self._history) > 0

    def undo_last(self) -> Tuple[bool, str]:
        """
        Reverts the last change. Returns (success, status_message).
        """
        if not self._history:
            return False, "No changes to undo."

        last_entry = self._history.pop()
        file_path_str = last_entry["file_path"]
        prev = last_entry["previous_content"]
        p = Path(file_path_str)

        try:
            if prev is None:
                # File was created, so deleting it undoes the action
                if p.exists():
                    p.unlink()
                return True, f"Undo complete: Deleted created file {p.name}"
            else:
                # File was edited or deleted, restore previous content
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(prev)
                return True, f"Undo complete: Restored {p.name} to previous state."
        except Exception as e:
            return False, f"Failed to undo change for {file_path_str}: {e}"

    def get_history_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "file": entry["file_path"],
                "description": entry["description"],
                "type": "create" if entry["previous_content"] is None else ("delete" if entry["new_content"] is None else "edit")
            }
            for entry in reversed(self._history)
        ]


# Global undo manager
undo_manager = UndoHistory()
