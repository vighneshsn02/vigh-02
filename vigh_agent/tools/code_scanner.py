"""
Deep Code Scanner and Health Auditor for VIGH-02 AI AGENT.
Scans folders, analyzes project structure, language breakdown, security issues, and syntax health.
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from vigh_agent.tools.base import BaseTool
from vigh_agent.utils.path_utils import resolve_path, is_ignored, is_binary_file, detect_language, format_file_size

# Security and vulnerability patterns
SECURITY_PATTERNS = [
    (r"(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token|password|passwd|private[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]", "High", "Potential Hardcoded Secret / API Key"),
    (r"(?i)eval\s*\(", "Medium", "Use of eval() can lead to arbitrary code execution"),
    (r"(?i)exec\s*\(", "Medium", "Use of exec() can execute dynamic code unsafely"),
    (r"(?i)subprocess\.call\(.*shell\s*=\s*True", "High", "subprocess with shell=True is prone to command injection"),
    (r"(?i)os\.system\s*\(", "Medium", "os.system() is prone to command injection"),
    (r"(?i)SELECT\s+.*\s+FROM\s+.*WHERE\s+.*%s", "Medium", "Potential SQL string formatting vulnerability"),
    (r"(?i)SELECT\s+.*\s+FROM\s+.*WHERE\s+.*\+", "Medium", "SQL concatenation risk (use parameterized queries)"),
    (r"(?i)http://[a-zA-Z0-9.\-]+", "Low", "Insecure HTTP URL detected (prefer HTTPS)")
]

FRAMEWORK_SIGNATURES = {
    "FastAPI": ["from fastapi import", "import fastapi"],
    "Flask": ["from flask import", "import flask"],
    "Django": ["django.core", "django.urls", "django.db"],
    "React": ["from 'react'", 'from "react"', "import React"],
    "Vue": ["from 'vue'", 'from "vue"', "<template>"],
    "Next.js": ["next/head", "next/router", "next/image"],
    "Express.js": ["express()", "require('express')", 'require("express")'],
    "PyTorch": ["import torch", "from torch import"],
    "TensorFlow": ["import tensorflow", "from tensorflow import"]
}


class CodeScannerTool(BaseTool):
    name = "scan_folder"
    description = "Recursively scans a folder or codebase, produces a file tree, language statistics, project summary, TODOs, and security check."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Folder path to scan (defaults to workspace root / current directory)."
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum directory depth to traverse (default 5)."
            },
            "include_security_audit": {
                "type": "boolean",
                "description": "Whether to perform a security and vulnerability audit (default True)."
            }
        }
    }

    def run(self, path: str = ".", max_depth: int = 5, include_security_audit: bool = True, workspace_root: Optional[str] = None) -> Dict[str, Any]:
        try:
            target = resolve_path(path, workspace_root)
            if not target.exists():
                return {"success": False, "error": f"Path does not exist: {target}"}
            if not target.is_dir():
                return {"success": False, "error": f"Path is not a directory: {target}"}

            root_path = target
            tree_lines: List[str] = []
            files_scanned = 0
            dirs_scanned = 0
            total_lines_of_code = 0
            lang_stats: Dict[str, Dict[str, int]] = {}  # {lang: {"files": count, "lines": count}}
            detected_frameworks: List[str] = []
            todos: List[Dict[str, Any]] = []
            security_findings: List[Dict[str, Any]] = []
            syntax_errors: List[Dict[str, Any]] = []

            def _scan_dir(current_dir: Path, depth: int, prefix: str = ""):
                nonlocal files_scanned, dirs_scanned, total_lines_of_code
                if depth > max_depth:
                    return

                try:
                    entries = sorted(current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                except PermissionError:
                    return

                # Filter ignored
                valid_entries = [e for e in entries if not is_ignored(e, root_path)]
                total_entries = len(valid_entries)

                for index, entry in enumerate(valid_entries):
                    is_last = (index == total_entries - 1)
                    connector = "└── " if is_last else "├── "
                    child_prefix = "    " if is_last else "│   "

                    if entry.is_dir():
                        dirs_scanned += 1
                        tree_lines.append(f"{prefix}{connector}{entry.name}/")
                        _scan_dir(entry, depth + 1, prefix + child_prefix)
                    else:
                        files_scanned += 1
                        size_str = format_file_size(entry.stat().st_size)
                        tree_lines.append(f"{prefix}{connector}{entry.name} ({size_str})")

                        # Inspect text code files
                        if not is_binary_file(entry):
                            lang = detect_language(entry)
                            if lang != "text":
                                try:
                                    with open(entry, "r", encoding="utf-8", errors="replace") as f:
                                        content = f.read()
                                        file_lines = content.splitlines()
                                        line_count = len(file_lines)

                                    total_lines_of_code += line_count
                                    if lang not in lang_stats:
                                        lang_stats[lang] = {"files": 0, "lines": 0}
                                    lang_stats[lang]["files"] += 1
                                    lang_stats[lang]["lines"] += line_count

                                    rel_path = str(entry.relative_to(root_path))

                                    # Check Frameworks
                                    for fw, sigs in FRAMEWORK_SIGNATURES.items():
                                        if fw not in detected_frameworks:
                                            if any(sig in content for sig in sigs):
                                                detected_frameworks.append(fw)

                                    # Check Syntax (Python)
                                    if lang == "python":
                                        try:
                                            ast.parse(content, filename=str(entry))
                                        except SyntaxError as se:
                                            syntax_errors.append({
                                                "file": rel_path,
                                                "line": se.lineno,
                                                "message": se.msg,
                                                "text": se.text.strip() if se.text else ""
                                            })
                                    elif lang == "json":
                                        try:
                                            json.loads(content)
                                        except Exception as je:
                                            syntax_errors.append({
                                                "file": rel_path,
                                                "line": 1,
                                                "message": str(je)
                                            })

                                    # Check TODOs / FIXMEs
                                    for l_idx, line in enumerate(file_lines, start=1):
                                        if any(k in line for k in ("TODO", "FIXME", "HACK", "BUG", "XXX")):
                                            clean_l = line.strip()
                                            if len(clean_l) < 160:
                                                todos.append({
                                                    "file": rel_path,
                                                    "line": l_idx,
                                                    "comment": clean_l
                                                })

                                    # Security Scan
                                    if include_security_audit:
                                        for pattern, severity, desc in SECURITY_PATTERNS:
                                            for l_idx, line in enumerate(file_lines, start=1):
                                                if re.search(pattern, line):
                                                    security_findings.append({
                                                        "file": rel_path,
                                                        "line": l_idx,
                                                        "severity": severity,
                                                        "description": desc,
                                                        "snippet": line.strip()[:100]
                                                    })
                                except Exception:
                                    pass

            tree_lines.append(f"{target.name}/")
            _scan_dir(target, 1)

            # Sort languages by lines of code
            sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1]["lines"], reverse=True)
            lang_summary = [
                {"language": k, "files": v["files"], "lines": v["lines"]}
                for k, v in sorted_langs
            ]

            summary_text = (
                f"Codebase Scan Summary for '{target.name}':\n"
                f"• Total Files: {files_scanned}, Total Directories: {dirs_scanned}\n"
                f"• Total Lines of Code: {total_lines_of_code}\n"
                f"• Languages: {', '.join([f'{l}:{c['lines']}L' for l, c in sorted_langs[:5]]) or 'None'}\n"
                f"• Frameworks: {', '.join(detected_frameworks) or 'None detected'}\n"
                f"• Open TODOs: {len(todos)}\n"
                f"• Security Findings: {len(security_findings)}\n"
                f"• Syntax Errors: {len(syntax_errors)}"
            )

            return {
                "success": True,
                "path": str(target),
                "summary": summary_text,
                "tree": "\n".join(tree_lines[:300]),  # capped for reasonable output size
                "total_files": files_scanned,
                "total_dirs": dirs_scanned,
                "total_lines_of_code": total_lines_of_code,
                "languages": lang_summary,
                "frameworks": detected_frameworks,
                "todos": todos[:50],
                "security_findings": security_findings[:30],
                "syntax_errors": syntax_errors[:20]
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to scan folder: {str(e)}"}
