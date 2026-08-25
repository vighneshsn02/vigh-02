"""
Tab Auto-completion for VIGH-02 AI AGENT terminal.
"""

import os
from pathlib import Path
from typing import Iterable, List
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

SLASH_COMMANDS = [
    ("/scan", "Deep scan workspace structure, stats & security"),
    ("/edit", "Edit a file in workspace: /edit <path>"),
    ("/read", "View syntax-highlighted file: /read <path>"),
    ("/diff", "Show git or recent file modifications"),
    ("/undo", "Revert last file change"),
    ("/model", "Switch local AI model (Ollama / LM Studio)"),
    ("/web", "Launch modern browser Web UI"),
    ("/cd", "Change active workspace directory: /cd <path>"),
    ("/clear", "Clear terminal screen"),
    ("/help", "Show help and commands"),
    ("/exit", "Exit VIGH-02 AI AGENT")
]


class VighCompleter(Completer):
    """Custom auto-completer for commands and file paths."""

    def __init__(self, workspace_path_getter):
        self.workspace_path_getter = workspace_path_getter

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        text_before_cursor = document.text_before_cursor

        # Complete slash commands
        if text_before_cursor.startswith("/"):
            word = text_before_cursor
            for cmd, desc in SLASH_COMMANDS:
                if cmd.startswith(word):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=cmd,
                        display_meta=desc
                    )
            return

        # Complete file paths if user is typing a path or after /edit, /read
        parts = text_before_cursor.split()
        if parts and (parts[0] in ("/edit", "/read", "/cd") or "/" in parts[-1] or "\\" in parts[-1]):
            target_part = parts[-1] if len(parts) > 1 else ""
            workspace = Path(self.workspace_path_getter())
            
            try:
                base_dir = workspace
                prefix = target_part
                if os.path.isabs(target_part):
                    base_dir = Path(target_part).parent
                    prefix = Path(target_part).name
                elif "/" in target_part or "\\" in target_part:
                    p = workspace / Path(target_part)
                    base_dir = p.parent
                    prefix = p.name

                if base_dir.exists() and base_dir.is_dir():
                    for item in base_dir.iterdir():
                        if item.name.startswith(prefix) and not item.name.startswith("."):
                            rel = item.name
                            yield Completion(
                                rel,
                                start_position=-len(prefix),
                                display=item.name + ("/" if item.is_dir() else ""),
                                display_meta="dir" if item.is_dir() else "file"
                            )
            except Exception:
                pass
