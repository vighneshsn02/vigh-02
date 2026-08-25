"""
Main CLI entry point for VIGH-02 AI AGENT.
Provides interactive mode selector (CLI vs Web vs Scan vs Model) and CLI flag parsing.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Configure UTF-8 on Windows console
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from vigh_agent import __version__, __agent_name__
from vigh_agent.config import config
from vigh_agent.models.registry import model_registry
from vigh_agent.terminal.repl import run_cli_session, handle_model_switch
from vigh_agent.terminal.formatters import render_scan_results
from vigh_agent.tools.code_scanner import CodeScannerTool
from vigh_agent.web.server import start_web_server

console = Console(highlight=False)


def install_global_wrapper():
    """Installs Windows batch wrappers in Python Scripts folder for global CLI access."""
    scripts_dir = Path(sys.prefix) / "Scripts"
    if not scripts_dir.exists():
        scripts_dir.mkdir(parents=True, exist_ok=True)

    batch_vigh02 = scripts_dir / "vigh-02.bat"
    batch_vigh = scripts_dir / "vigh.bat"

    python_exe = sys.executable
    batch_content = f'@echo off\n"{python_exe}" -m vigh_agent.cli %*\n'

    try:
        with open(batch_vigh02, "w", encoding="utf-8") as f:
            f.write(batch_content)
        with open(batch_vigh, "w", encoding="utf-8") as f:
            f.write(batch_content)
        console.print(f"[bold green][OK] Successfully installed global CLI wrappers at {scripts_dir}[/bold green]")
        console.print("[green]You can now run [bold cyan]vigh-02[/bold cyan] or [bold cyan]vigh[/bold cyan] from ANY folder in your terminal![/green]")
    except Exception as e:
        console.print(f"[bold red]Failed to install global wrapper:[/bold red] {e}")


def interactive_menu(workspace_dir: str, model_name: Optional[str] = None):
    """Interactive launch menu asking user whether to open CLI, Web, or Scan."""
    detected_p, detected_m = model_registry.auto_detect_best_model()
    active_m = model_name or detected_m

    art = r"""
 ██    ██ ██  ██████  ██   ██      ██████  ██████  
 ██    ██ ██ ██       ██   ██     ██  ████      ██ 
 ██    ██ ██ ██   ███ ███████     ██ ██ ██  █████  
  ██  ██  ██ ██    ██ ██   ██     ████  ██ ██      
   ████   ██  ██████  ██   ██      ██████  ███████ 
"""
    banner_content = Text(art, style="bold cyan")
    banner_content.append("\n⚡ VIGH-02 AI AGENT ⚡\n", style="bold bright_white")
    banner_content.append("Offline-First Autonomous Local & Cloud Coding Assistant\n\n", style="bold green")
    banner_content.append(f"📁 Workspace: {workspace_dir}\n", style="bold blue")
    banner_content.append(f"🤖 Active Model: {active_m} (100% Offline Capable)\n", style="bold yellow")

    console.print(Panel(banner_content, border_style="cyan", expand=False))

    table = Table(title="Select Interface Mode", border_style="dim cyan", show_header=False)
    table.add_column("Option", style="bold cyan")
    table.add_column("Description", style="white")

    table.add_row("[1] 💻 Terminal CLI", "Interactive command line chat, live diffs & instant code edits")
    table.add_row("[2] 🌐 Modern Web UI", "Browser dashboard with Code Editor, Visual Diff & File Tree")
    table.add_row("[3] 🔍 Codebase Scan", "Deep structural audit, LOC stats, security check & TODOs")
    table.add_row("[4] ⚙️ Select AI Model", "Switch between installed local Ollama/LM Studio models")
    table.add_row("[5] 🛠️ Global Install", "Register 'vigh-02' command globally in Windows PATH")
    table.add_row("[6] ❌ Exit", "Quit VIGH-02")

    console.print(table)
    console.print()

    choice = input("Enter choice [1-6] (Default is 1): ").strip() or "1"

    if choice == "1":
        run_cli_session(workspace_dir=workspace_dir, model_name=active_m)
    elif choice == "2":
        start_web_server(workspace_dir=workspace_dir, open_browser=True)
    elif choice == "3":
        scanner = CodeScannerTool()
        with console.status("[bold cyan]Scanning workspace...[/bold cyan]", spinner="dots"):
            res = scanner.run(path=".", workspace_root=workspace_dir)
        if res.get("success"):
            render_scan_results(res)
        else:
            console.print(f"[bold red]Scan failed:[/bold red] {res.get('error')}")
    elif choice == "4":
        from vigh_agent.core.session import AgentSession
        temp_session = AgentSession(workspace_path=workspace_dir)
        handle_model_switch(temp_session)
        interactive_menu(workspace_dir, model_name=temp_session.model_name)
    elif choice == "5":
        install_global_wrapper()
    elif choice == "6":
        console.print("[yellow]Goodbye![/yellow]")
        sys.exit(0)
    else:
        console.print("[yellow]Invalid selection. Defaulting to CLI mode.[/yellow]")
        run_cli_session(workspace_dir=workspace_dir, model_name=active_m)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="vigh-02",
        description="VIGH-02 AI AGENT: Offline-First Autonomous Local & Cloud Coding AI Assistant"
    )
    parser.add_argument(
        "--cli", "-c",
        action="store_true",
        help="Launch directly in interactive CLI terminal mode"
    )
    parser.add_argument(
        "--web", "-w",
        action="store_true",
        help="Launch directly in modern browser Web UI mode"
    )
    parser.add_argument(
        "--scan", "-s",
        action="store_true",
        help="Run immediate codebase health scan and print report"
    )
    parser.add_argument(
        "--dir", "-d",
        type=str,
        default=".",
        help="Target workspace folder or file path (default: current working directory)"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Specify AI model to use (e.g. qwen2.5-coder:7b, llama3.2, deepseek-coder:1.3b)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Web UI host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="Web UI port (default: 8440)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open browser in web mode"
    )
    parser.add_argument(
        "--install-global",
        action="store_true",
        help="Install global Windows command wrappers for 'vigh-02' and 'vigh'"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"{__agent_name__} v{__version__}"
    )

    args = parser.parse_args()

    # Target directory resolution
    target_dir = os.path.abspath(args.dir)

    if args.install_global:
        install_global_wrapper()
        return

    if args.scan:
        scanner = CodeScannerTool()
        with console.status("[bold cyan]Scanning workspace...[/bold cyan]", spinner="dots"):
            res = scanner.run(path=".", workspace_root=target_dir)
        if res.get("success"):
            render_scan_results(res)
        else:
            console.print(f"[bold red]Scan failed:[/bold red] {res.get('error')}")
        return

    if args.cli:
        run_cli_session(workspace_dir=target_dir, model_name=args.model)
        return

    if args.web:
        start_web_server(
            workspace_dir=target_dir,
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser
        )
        return

    # If no flags passed, prompt interactive menu
    interactive_menu(workspace_dir=target_dir, model_name=args.model)


if __name__ == "__main__":
    main()
