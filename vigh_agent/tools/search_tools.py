"""
Code search and symbol outline tools for VIGH-02 AI AGENT.
"""

import ast
import fnmatch
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from vigh_agent.tools.base import BaseTool
from vigh_agent.utils.path_utils import resolve_path, is_ignored, is_binary_file, detect_language


class SearchCodeTool(BaseTool):
    name = "search_code"
    description = "Searches for a text pattern or regular expression across all files in a folder."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text or regex query to search for."
            },
            "path": {
                "type": "string",
                "description": "Folder or file path to search inside (default is workspace root)."
            },
            "file_pattern": {
                "type": "string",
                "description": "Optional glob filter for file names (e.g. '*.py', '*.js')."
            },
            "is_regex": {
                "type": "boolean",
                "description": "Whether to treat query as a regular expression."
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether search is case sensitive (default False)."
            }
        },
        "required": ["query"]
    }

    def run(
        self,
        query: str,
        path: str = ".",
        file_pattern: Optional[str] = None,
        is_regex: bool = False,
        case_sensitive: bool = False,
        workspace_root: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            target = resolve_path(path, workspace_root)
            if not target.exists():
                return {"success": False, "error": f"Search path does not exist: {target}"}

            flags = 0 if case_sensitive else re.IGNORECASE
            if not is_regex:
                regex_pattern = re.compile(re.escape(query), flags)
            else:
                try:
                    regex_pattern = re.compile(query, flags)
                except Exception as re_err:
                    return {"success": False, "error": f"Invalid regex pattern: {re_err}"}

            matches = []
            files_searched = 0
            max_matches = 50

            root_path = target if target.is_dir() else target.parent

            def _search_file(f_path: Path):
                nonlocal files_searched
                if is_ignored(f_path, root_path) or is_binary_file(f_path):
                    return
                if file_pattern and not fnmatch.fnmatch(f_path.name, file_pattern):
                    return

                files_searched += 1
                try:
                    with open(f_path, "r", encoding="utf-8", errors="replace") as f:
                        for l_idx, line in enumerate(f, start=1):
                            if regex_pattern.search(line):
                                rel = str(f_path.relative_to(root_path)) if f_path != root_path else f_path.name
                                matches.append({
                                    "file": rel,
                                    "line": l_idx,
                                    "content": line.rstrip()[:200]
                                })
                                if len(matches) >= max_matches:
                                    return
                except Exception:
                    pass

            if target.is_file():
                _search_file(target)
            else:
                for root, dirs, files in os.walk(target):
                    # Filter out ignored dirs in-place
                    dirs[:] = [d for d in dirs if not is_ignored(Path(root) / d, root_path)]
                    for file in files:
                        _search_file(Path(root) / file)
                        if len(matches) >= max_matches:
                            break
                    if len(matches) >= max_matches:
                        break

            return {
                "success": True,
                "query": query,
                "total_matches": len(matches),
                "files_searched": files_searched,
                "matches": matches,
                "truncated": len(matches) >= max_matches
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to search code: {str(e)}"}


class OutlineSymbolsTool(BaseTool):
    name = "outline_symbols"
    description = "Parses a file and extracts high-level symbols (classes, functions, methods, routes) for rapid understanding."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to extract symbols from."
            }
        },
        "required": ["path"]
    }

    def run(self, path: str, workspace_root: Optional[str] = None) -> Dict[str, Any]:
        try:
            target = resolve_path(path, workspace_root)
            if not target.exists():
                return {"success": False, "error": f"File does not exist: {target}"}
            if not target.is_file():
                return {"success": False, "error": f"Path is not a file: {target}"}

            lang = detect_language(target)
            symbols: List[Dict[str, Any]] = []

            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if lang == "python":
                try:
                    tree = ast.parse(content, filename=str(target))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            symbols.append({
                                "type": "class",
                                "name": node.name,
                                "line": node.lineno,
                                "docstring": ast.get_docstring(node) or ""
                            })
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            is_async = isinstance(node, ast.AsyncFunctionDef)
                            symbols.append({
                                "type": "async_function" if is_async else "function",
                                "name": node.name,
                                "line": node.lineno,
                                "args": [a.arg for a in node.args.args],
                                "docstring": ast.get_docstring(node) or ""
                            })
                except Exception as pe:
                    return {"success": False, "error": f"Python syntax error parsing symbols: {pe}"}

            elif lang in ("javascript", "typescript"):
                # Regex extraction for JS/TS
                class_pattern = re.compile(r"class\s+([A-Za-z0-9_$]+)", re.MULTILINE)
                func_pattern = re.compile(r"(?:function\s+([A-Za-z0-9_$]+)|(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)", re.MULTILINE)
                
                for idx, line in enumerate(content.splitlines(), start=1):
                    c_match = class_pattern.search(line)
                    if c_match:
                        symbols.append({"type": "class", "name": c_match.group(1), "line": idx})
                    f_match = func_pattern.search(line)
                    if f_match:
                        name = f_match.group(1) or f_match.group(2)
                        symbols.append({"type": "function", "name": name, "line": idx})

            return {
                "success": True,
                "file": target.name,
                "language": lang,
                "total_symbols": len(symbols),
                "symbols": symbols
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to extract symbols: {str(e)}"}
