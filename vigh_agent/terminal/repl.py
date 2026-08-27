"""
Interactive CLI REPL for VIGH-02 AI AGENT.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Safe UTF-8 configuration
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
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from vigh_agent.banner import print_banner, print_divider
from vigh_agent.core.session import AgentSession
from vigh_agent.core.agent import VighAgent, AgentEvent
from vigh_agent.models.registry import model_registry
from vigh_agent.tools.registry import tool_registry
from vigh_agent.tools.code_scanner import CodeScannerTool
from vigh_agent.utils.diff_utils import undo_manager
from vigh_agent.terminal.formatters import render_scan_results, render_diff, render_code_file, render_markdown
from vigh_agent.terminal.completer import VighCompleter

console = Console(highlight=False)

PT_STYLE = Style.from_dict({
    "prompt": "ansicyan bold",
    "path": "ansiyellow bold",
})


def run_cli_session(workspace_dir: Optional[str] = None, model_name: Optional[str] = None, mode: Optional[str] = None):
    """Starts the interactive CLI coding session."""
    session = AgentSession(workspace_path=workspace_dir)
    if model_name:
        session.initialize_provider(model_name=model_name)
    if mode:
        session.set_mode(mode)

    agent = VighAgent(session=session)
    completer = VighCompleter(lambda: str(session.workspace_root))
    prompt_session = PromptSession(completer=completer)

    print_banner(
        model_name=session.model_name,
        workspace_dir=str(session.workspace_root),
        mode=f"CLI ({session.mode.upper()}-AGENT)"
    )

    console.print(f"[bold green]Agent ready in {session.mode.upper()}-AGENT mode![/bold green] Type your coding request, or type [bold cyan]/help[/bold cyan] for commands.\n")

    while True:
        try:
            ws_display = session.workspace_root.name or str(session.workspace_root)
            mode_tag = " [MULTI]" if session.mode == "multi" else ""
            user_input = prompt_session.prompt(
                [
                    ("class:path", f"[{ws_display}{mode_tag}] "),
                    ("class:prompt", "vigh-02> ")
                ],
                style=PT_STYLE
            ).strip()

            if not user_input:
                continue

            # Command routing
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1].strip() if len(parts) > 1 else ""

                if cmd in ("/exit", "/quit", "/q"):
                    console.print("[bold yellow]Exiting VIGH-02 AI AGENT. Happy coding![/bold yellow]")
                    break

                elif cmd == "/help":
                    print_help()

                elif cmd in ("/multi", "/mode"):
                    if arg:
                        new_mode = session.set_mode(arg)
                    else:
                        # Toggle
                        new_mode = session.set_mode("single" if session.mode == "multi" else "multi")
                    
                    if new_mode == "multi":
                        console.print("[bold cyan]👥 Switched to MULTI-AGENT MODE![/bold cyan] Orchestrator + Planner, Coder, Tester, Reviewer & Security swarm active.")
                    else:
                        console.print("[bold green]⚡ Switched to SINGLE-AGENT MODE![/bold green] Fast direct execution active.")

                elif cmd == "/agents":
                    print_agents_table()

                elif cmd == "/scan":
                    with console.status("[bold cyan]Scanning codebase and auditing health...[/bold cyan]", spinner="dots"):
                        scanner = CodeScannerTool()
                        results = scanner.run(path=".", workspace_root=str(session.workspace_root))
                    if results.get("success"):
                        render_scan_results(results)
                    else:
                        console.print(f"[bold red]Scan failed:[/bold red] {results.get('error')}")

                elif cmd == "/edit":
                    if not arg:
                        console.print("[yellow]Usage: /edit <file_path>[/yellow]")
                        continue
                    handle_interactive_edit(agent, arg)

                elif cmd == "/read":
                    if not arg:
                        console.print("[yellow]Usage: /read <file_path>[/yellow]")
                        continue
                    p = session.workspace_root / arg
                    if p.exists() and p.is_file():
                        with open(p, "r", encoding="utf-8", errors="replace") as f:
                            render_code_file(f.read(), arg)
                    else:
                        console.print(f"[bold red]File not found:[/bold red] {arg}")

                elif cmd == "/diff":
                    diff_res = tool_registry.execute("git_diff", {}, workspace_root=str(session.workspace_root))
                    if diff_res.get("success") and diff_res.get("diff"):
                        render_diff(diff_res["diff"], "Git Working Tree")
                    elif not diff_res.get("diff"):
                        console.print("[green]No uncommitted git changes found.[/green]")
                    else:
                        console.print(f"[yellow]{diff_res.get('error')}[/yellow]")

                elif cmd == "/undo":
                    success, msg = undo_manager.undo_last()
                    if success:
                        console.print(f"[bold green][OK] {msg}[/bold green]")
                    else:
                        console.print(f"[bold yellow][!] {msg}[/bold yellow]")

                elif cmd == "/model":
                    handle_model_switch(session)

                elif cmd == "/web":
                    from vigh_agent.web.server import start_web_server
                    console.print("[bold cyan]Launching VIGH-02 Modern Web UI...[/bold cyan]")
                    start_web_server(workspace_dir=str(session.workspace_root), open_browser=True)

                elif cmd == "/cd":
                    if not arg:
                        console.print(f"Current workspace: [cyan]{session.workspace_root}[/cyan]")
                    else:
                        ok, msg = session.set_workspace(arg)
                        if ok:
                            console.print(f"[bold green]{msg}[/bold green]")
                        else:
                            console.print(f"[bold red]{msg}[/bold red]")

                elif cmd == "/clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    print_banner(session.model_name, str(session.workspace_root), f"CLI ({session.mode.upper()}-AGENT)")

                else:
                    console.print(f"[yellow]Unknown command '{cmd}'. Type /help for available commands.[/yellow]")
                continue

            # Standard Agent Interaction Loop
            console.print()
            stream_agent_response(agent, user_input)
            console.print()

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session interrupted. Type /exit to quit.[/yellow]")
        except Exception as e:
            console.print(f"\n[bold red]Error in CLI session:[/bold red] {e}\n")


def stream_agent_response(agent: VighAgent, user_prompt: str):
    """Streams live response tokens and executes tools with real-time UI."""
    is_multi = (agent.session.mode == "multi")

    if is_multi:
        console.print("[bold bright_white]👑 VIGH-02 MULTI-AGENT SWARM INITIATED[/bold bright_white]\n")
    else:
        console.print(f"[bold cyan]🤖 VIGH-02 ({agent.session.model_name}):[/bold cyan]")
    
    current_agent = None

    for event in agent.chat_stream(user_prompt):
        agent_name = (event.data.get("agent") if event.data else None) or "Agent"

        if event.type == "phase_start" and event.content:
            console.print(f"\n[bold cyan]{event.content}[/bold cyan]")

        elif event.type == "phase_end" and event.content:
            console.print(f"[dim green]{event.content}[/dim green]")

        elif event.type == "agent_start":
            current_agent = agent_name
            badge_color = "cyan"
            if agent_name.lower() == "planner": badge_color = "bright_blue"
            elif agent_name.lower() == "coder": badge_color = "bright_green"
            elif agent_name.lower() == "tester": badge_color = "bright_yellow"
            elif agent_name.lower() == "reviewer": badge_color = "bright_magenta"
            elif agent_name.lower() == "security": badge_color = "bright_red"
            elif agent_name.lower() == "orchestrator": badge_color = "bright_cyan"

            console.print(f"\n[{badge_color}]▶ [{agent_name.upper()}] Working...[/{badge_color}]")

        elif event.type == "token" and event.content:
            try:
                sys.stdout.write(event.content)
                sys.stdout.flush()
            except Exception:
                console.print(event.content, end="")

        elif event.type == "tool_start":
            tool_name = event.data.get("name", "tool") if event.data else "tool"
            console.print(f"\n[dim yellow]⚡ [{agent_name}] Executing {tool_name}...[/dim yellow]")

        elif event.type == "tool_end":
            tool_name = event.data.get("name", "") if event.data else ""
            res = event.data.get("result", {}) if event.data else {}
            if isinstance(res, dict) and not res.get("success", True):
                console.print(f"[dim red][FAIL] {tool_name}: {res.get('error')}[/dim red]")
            else:
                console.print(f"[dim green][OK] {tool_name} completed.[/dim green]")

        elif event.type == "diff":
            if event.content:
                render_diff(event.content, event.data.get("path", "Modified File") if event.data else "File")

        elif event.type == "autofix_start":
            console.print(f"\n[bold yellow]{event.content}[/bold yellow]")

        elif event.type == "autofix_complete":
            console.print(f"[bold green]{event.content}[/bold green]")

        elif event.type == "test_result":
            status_color = "green" if "PASSED" in (event.content or "") else "red"
            console.print(f"[{status_color}]🧪 {event.content}[/{status_color}]")

        elif event.type == "security_audit":
            console.print(f"[bold bright_red]🛡️ {event.content}[/bold bright_red]")

        elif event.type == "review_result":
            console.print(f"[bold magenta]🔍 {event.content}[/bold magenta]")

        elif event.type == "error":
            console.print(f"\n[bold red]Error:[/bold red] {event.content}")


def print_agents_table():
    """Prints specialized agents overview table."""
    table = Table(title="[bold cyan]⚡ VIGH-02 Specialized Multi-Agent Team[/bold cyan]", border_style="cyan")
    table.add_column("Agent", style="bold yellow")
    table.add_column("Role", style="bold white")
    table.add_column("Key Capabilities & Tools", style="dim")

    table.add_row("👑 Orchestrator", "Team Lead & Workflow Coordinator", "Parallel dispatch, auto-fix supervision, final synthesis")
    table.add_row("🧠 Planner", "Chief Software Architect", "Scope analysis, file targeting, task breakdown (`scan_folder`, `read_file`)")
    table.add_row("💻 Coder", "Senior Software Engineer", "Complete implementations, surgical patches (`edit_file`, `write_file`)")
    table.add_row("🧪 Tester", "QA & Test Automation Engineer", "Test discovery, unit test execution, failure diagnostics (`run_command`)")
    table.add_row("🔍 Reviewer", "Principal Code Reviewer", "Architecture analysis, DRY/SOLID audit, score rating (`git_diff`)")
    table.add_row("🛡️ Security", "Application Security Specialist", "Vulnerability scanning, secret detection, OWASP audit (`scan_folder`)")

    console.print(table)


def handle_interactive_edit(agent: VighAgent, file_path: str):
    """Guides user through requesting an AI edit for a specific file."""
    p = agent.session.workspace_root / file_path
    if not p.exists():
        console.print(f"[yellow]File '{file_path}' does not exist yet. Describe what you'd like to generate:[/yellow]")
    else:
        console.print(f"[cyan]What changes would you like to make to '{file_path}'?[/cyan]")
    
    prompt = input("Edit prompt: ").strip()
    if prompt:
        full_query = f"Please edit or create the file '{file_path}'. Instructions: {prompt}"
        stream_agent_response(agent, full_query)


def handle_model_switch(session: AgentSession):
    """Interactive model selection in CLI."""
    available = model_registry.scan_all_models()
    if not available:
        console.print("[bold red]No local models detected. Please ensure Ollama or LM Studio is running.[/bold red]")
        return

    table = Table(title="[bold cyan]Available Local AI Models[/bold cyan]", border_style="cyan")
    table.add_column("#", style="bold yellow")
    table.add_column("Model Name", style="bold white")
    table.add_column("Provider", style="green")
    table.add_column("Size", style="dim")

    for idx, m in enumerate(available, start=1):
        is_active = (m["id"] == session.model_name)
        prefix = "-> " if is_active else "   "
        table.add_row(f"{prefix}{idx}", m["name"], m.get("provider", "local"), m.get("size", "-"))

    console.print(table)
    choice = input(f"\nEnter model number [1-{len(available)}] or press Enter to keep current: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(available):
        chosen = available[int(choice) - 1]
        session.initialize_provider(provider_name=chosen.get("provider"), model_name=chosen["id"])
        console.print(f"[bold green][OK] Switched model to: {chosen['name']}[/bold green]")


def print_help():
    """Prints command cheat sheet."""
    table = Table(title="[bold cyan]VIGH-02 AI AGENT Commands[/bold cyan]", border_style="dim cyan")
    table.add_column("Command", style="bold yellow")
    table.add_column("Description", style="white")

    table.add_row("/multi", "Toggle between Fast Single-Agent and Collaborative Multi-Agent Swarm Mode")
    table.add_row("/agents", "Display specialized agents (Planner, Coder, Tester, Reviewer, Security, Orchestrator)")
    table.add_row("/scan", "Deeply scan folder structure, stats, languages, security vulnerabilities, and TODOs")
    table.add_row("/edit <file>", "Directly request the AI to modify or create a specific file")
    table.add_row("/read <file>", "View syntax-highlighted code with line numbers")
    table.add_row("/diff", "Show git working tree or recent file diffs")
    table.add_row("/undo", "Instantly rollback the last file edit/creation")
    table.add_row("/model", "Switch active local AI model (Ollama, LM Studio, etc.)")
    table.add_row("/web", "Launch modern Web UI in browser")
    table.add_row("/cd <path>", "Switch active workspace directory to any folder")
    table.add_row("/clear", "Clear terminal screen")
    table.add_row("/help", "Show this help table")
    table.add_row("/exit", "Exit VIGH-02 AI AGENT")

    console.print(table)
