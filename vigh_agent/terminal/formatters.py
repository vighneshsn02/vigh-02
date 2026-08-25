"""
Rich formatting and terminal rendering helpers for VIGH-02 AI AGENT.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.markdown import Markdown
from typing import Dict, Any, List, Optional
from pathlib import Path

from vigh_agent.utils.diff_utils import create_rich_diff
from vigh_agent.utils.path_utils import detect_language

console = Console()


def render_markdown(text: str):
    """Render markdown formatted text to terminal."""
    md = Markdown(text)
    console.print(md)


def render_diff(diff_str: str, file_path: str = ""):
    """Render colored unified diff to terminal."""
    diff_text = create_rich_diff(diff_str)
    console.print(
        Panel(
            diff_text,
            title=f"[bold cyan]Diff Preview: {file_path}[/bold cyan]",
            border_style="cyan",
            expand=False
        )
    )


def render_code_file(content: str, file_path: str, start_line: int = 1):
    """Render syntax highlighted code with line numbers."""
    lang = detect_language(Path(file_path))
    syntax = Syntax(
        content,
        lang,
        theme="monokai",
        line_numbers=True,
        start_line=start_line,
        word_wrap=True
    )
    console.print(
        Panel(
            syntax,
            title=f"[bold green]File: {file_path}[/bold green]",
            border_style="green",
            expand=False
        )
    )


def render_scan_results(scan_data: Dict[str, Any]):
    """Render deep code scanner results in rich tables."""
    console.print(Panel(f"[bold cyan]🔍 Codebase Scan: {scan_data.get('path')}[/bold cyan]", border_style="cyan"))

    # Stats Table
    stats_table = Table(title="[bold yellow]Project Statistics[/bold yellow]", border_style="dim yellow")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="bold white")

    stats_table.add_row("Total Files", str(scan_data.get("total_files", 0)))
    stats_table.add_row("Total Directories", str(scan_data.get("total_dirs", 0)))
    stats_table.add_row("Total Lines of Code", f"{scan_data.get('total_lines_of_code', 0):,}")
    stats_table.add_row("Detected Frameworks", ", ".join(scan_data.get("frameworks", [])) or "None")

    console.print(stats_table)
    console.print()

    # Languages Table
    langs = scan_data.get("languages", [])
    if langs:
        lang_table = Table(title="[bold green]Language Breakdown[/bold green]", border_style="dim green")
        lang_table.add_column("Language", style="bold green")
        lang_table.add_column("Files", justify="right")
        lang_table.add_column("Lines", justify="right")

        for l in langs:
            lang_table.add_row(l["language"].capitalize(), str(l["files"]), f"{l['lines']:,}")
        console.print(lang_table)
        console.print()

    # Security findings
    sec = scan_data.get("security_findings", [])
    if sec:
        sec_table = Table(title="[bold red]🛡️ Security Audit Findings[/bold red]", border_style="red")
        sec_table.add_column("Severity", style="bold red")
        sec_table.add_column("File:Line", style="yellow")
        sec_table.add_column("Description", style="white")

        for item in sec[:10]:
            sec_table.add_row(item["severity"], f"{item['file']}:{item['line']}", item["description"])
        console.print(sec_table)
        console.print()

    # Open TODOs
    todos = scan_data.get("todos", [])
    if todos:
        todo_table = Table(title="[bold magenta]📝 Open Action Items (TODOs/FIXMEs)[/bold magenta]", border_style="dim magenta")
        todo_table.add_column("Location", style="yellow")
        todo_table.add_column("Comment", style="white")

        for t in todos[:10]:
            todo_table.add_row(f"{t['file']}:{t['line']}", t["comment"])
        console.print(todo_table)
        console.print()

    # File Tree Preview
    tree_text = scan_data.get("tree", "")
    if tree_text:
        console.print(
            Panel(
                Text(tree_text, style="cyan"),
                title="[bold blue]📁 Directory Structure[/bold blue]",
                border_style="dim blue",
                expand=False
            )
        )
