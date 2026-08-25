"""
Banner and styling for VIGH-02 AI AGENT.
"""

import sys
import os

# Configure UTF-8 on Windows terminal if possible
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
from rich.text import Text
from rich.table import Table

console = Console(highlight=False)

BANNER_ART = r"""
 ██    ██ ██  ██████  ██   ██      ██████  ██████  
 ██    ██ ██ ██       ██   ██     ██  ████      ██ 
 ██    ██ ██ ██   ███ ███████     ██ ██ ██  █████  
  ██  ██  ██ ██    ██ ██   ██     ████  ██ ██      
   ████   ██  ██████  ██   ██      ██████  ███████ 
"""

def print_banner(model_name: str = "Auto-Detecting", workspace_dir: str = "", mode: str = "CLI"):
    """Displays the branded VIGH-02 AI AGENT startup banner."""
    art_text = Text(BANNER_ART, style="bold cyan")
    
    title = Text("⚡ VIGH-02 AI AGENT ⚡", style="bold bright_white")
    subtitle = Text("Offline-First Autonomous Local & Cloud Coding Assistant", style="bold green")
    
    info_table = Table.grid(padding=(0, 2))
    info_table.add_column(style="bold yellow", justify="right")
    info_table.add_column(style="bright_white")
    
    info_table.add_row("🤖 Active Model:", f"[bold cyan]{model_name}[/bold cyan]")
    info_table.add_row("📁 Workspace:", f"[bold blue]{workspace_dir}[/bold blue]")
    info_table.add_row("🚀 Interface:", f"[bold magenta]{mode}[/bold magenta]")
    info_table.add_row("🔌 Offline Mode:", "[bold green]100% Offline Capable (Local AI)[/bold green]")
    info_table.add_row("💡 Quick Commands:", "[dim]/scan, /edit, /model, /diff, /undo, /web, /help, /exit[/dim]")
    
    panel_content = Text()
    panel_content.append(art_text)
    panel_content.append("\n")
    panel_content.append(title)
    panel_content.append("\n")
    panel_content.append(subtitle)
    panel_content.append("\n\n")
    
    console.print(
        Panel(
            panel_content,
            subtitle="v2.0.0 | Created for Autonomous Local Coding",
            border_style="bright_cyan",
            expand=False
        )
    )
    console.print(Panel(info_table, title="[bold]Session Context[/bold]", border_style="dim cyan", expand=False))
    console.print()

def print_divider(title: str = ""):
    """Print a clean divider."""
    if title:
        console.rule(f"[bold cyan]{title}[/bold cyan]")
    else:
        console.rule(style="dim")
