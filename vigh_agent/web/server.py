"""
FastAPI Server for VIGH-02 AI AGENT Web UI.
"""

import os
import sys
import socket
import webbrowser
import threading
import time
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from rich.console import Console

from vigh_agent.config import config
from vigh_agent.web.api import router, web_session

console = Console()

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="VIGH-02 AI AGENT Web UI",
    description="Offline-First Local & Cloud Autonomous Coding Assistant",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    """Serve single-page web app."""
    index_path = STATIC_DIR / "index.html"
    return FileResponse(str(index_path))


def find_free_port(start_port: int = 8440) -> int:
    """Find an open port on localhost."""
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1
    return start_port


def start_web_server(
    workspace_dir: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    open_browser: bool = True
):
    """Starts the web server and opens the browser."""
    if workspace_dir:
        web_session.set_workspace(workspace_dir)

    target_host = host or config.get("web_host", "127.0.0.1")
    target_port = port or config.get("web_port", 8440)
    actual_port = find_free_port(target_port)
    url = f"http://{target_host}:{actual_port}"

    console.print(f"\n[bold green]⚡ VIGH-02 AI AGENT Web UI running at:[/bold green] [bold cyan]{url}[/bold cyan]")
    console.print(f"[dim]📁 Active Workspace: {web_session.workspace_root}[/dim]")
    console.print(f"[dim]🤖 Active Model: {web_session.model_name}[/dim]")
    console.print("[dim]Press Ctrl+C in terminal to stop server.[/dim]\n")

    if open_browser:
        def _open():
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(
        app,
        host=target_host,
        port=actual_port,
        log_level="warning"
    )
