"""
Path and file utility functions for VIGH-02 AI AGENT.
"""

import os
import fnmatch
from pathlib import Path
from typing import List, Optional, Tuple, Set

from vigh_agent.config import config

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".json": "json",
    ".md": "markdown",
    ".markdown": "markdown",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".xml": "xml",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".bat": "batch",
    ".ps1": "powershell",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".toml": "toml",
    ".ini": "ini",
    ".env": "dotenv",
    ".dockerfile": "dockerfile",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".bmp", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".pyc", ".pyo", ".pyd", ".class", ".jar",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv"
}


def resolve_path(target_path: str, workspace_root: Optional[str] = None) -> Path:
    """
    Safely resolves a path. If relative, joins with workspace_root (or cwd).
    """
    if workspace_root is None:
        workspace_root = os.getcwd()
    
    clean_target = target_path.strip().strip('"').strip("'")
    p = Path(clean_target)
    
    if not p.is_absolute():
        p = Path(workspace_root) / p
        
    return p.resolve()


def is_ignored(file_path: Path, workspace_root: Path, custom_ignores: Optional[List[str]] = None) -> bool:
    """
    Checks if a file or directory path matches ignore patterns.
    """
    ignored_patterns = config.get("ignored_patterns", [])
    if custom_ignores:
        ignored_patterns = list(set(ignored_patterns + custom_ignores))

    try:
        rel_path = file_path.relative_to(workspace_root)
        parts = rel_path.parts
    except ValueError:
        parts = file_path.parts

    for part in parts:
        for pattern in ignored_patterns:
            if fnmatch.fnmatch(part, pattern):
                return True

    name = file_path.name
    for pattern in ignored_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True

    return False


def is_binary_file(file_path: Path) -> bool:
    """
    Determines if a file is binary by extension and initial byte inspection.
    """
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    
    if not file_path.is_file() or not file_path.exists():
        return False
        
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
    except Exception:
        return True
    return False


def detect_language(file_path: Path) -> str:
    """
    Detects language identifier for syntax highlighting.
    """
    suffix = file_path.suffix.lower()
    if suffix in LANGUAGE_EXTENSIONS:
        return LANGUAGE_EXTENSIONS[suffix]
    
    name = file_path.name.lower()
    if name in ("dockerfile", "containerfile"):
        return "dockerfile"
    if name in ("makefile", "gnumakefile"):
        return "makefile"
    if name.startswith(".env"):
        return "dotenv"
    if name.endswith("rc"):
        return "json"
        
    return "text"


def format_file_size(size_bytes: int) -> str:
    """
    Formats byte size to human readable string.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
