"""
REST & Streaming API endpoints for VIGH-02 AI AGENT Web UI.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from vigh_agent.core.session import AgentSession
from vigh_agent.core.agent import VighAgent, AgentEvent
from vigh_agent.models.registry import model_registry
from vigh_agent.tools.registry import tool_registry
from vigh_agent.tools.code_scanner import CodeScannerTool
from vigh_agent.tools.file_tools import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from vigh_agent.tools.execution_tools import RunCommandTool
from vigh_agent.utils.diff_utils import undo_manager
from vigh_agent.utils.path_utils import resolve_path, is_ignored, is_binary_file

router = APIRouter(prefix="/api")

# Global session and agent instance for web
web_session = AgentSession()
web_agent = VighAgent(session=web_session)


class ChatRequest(BaseModel):
    message: str


class SwitchModelRequest(BaseModel):
    provider: str
    model: str


class SwitchWorkspaceRequest(BaseModel):
    path: str


class SaveFileRequest(BaseModel):
    path: str
    content: str
    description: Optional[str] = "Web editor save"


class CommandRequest(BaseModel):
    command: str


@router.get("/status")
def get_status():
    """Returns agent status, workspace, and model health."""
    return web_session.get_status()


@router.get("/models")
def get_models():
    """Returns all local and configured models."""
    available = model_registry.scan_all_models()
    return {
        "current_provider": web_session.provider_name,
        "current_model": web_session.model_name,
        "models": available
    }


@router.post("/models/select")
def select_model(req: SwitchModelRequest):
    """Switch active model."""
    try:
        web_session.initialize_provider(provider_name=req.provider, model_name=req.model)
        return {
            "success": True,
            "provider": web_session.provider_name,
            "model": web_session.model_name,
            "message": f"Successfully switched to {req.model}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace")
def set_workspace(req: SwitchWorkspaceRequest):
    """Change workspace directory."""
    success, msg = web_session.set_workspace(req.path)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {
        "success": True,
        "workspace": str(web_session.workspace_root),
        "message": msg
    }


@router.get("/scan")
def scan_codebase(max_depth: int = 5, security_audit: bool = True):
    """Deeply scan the workspace."""
    scanner = CodeScannerTool()
    res = scanner.run(
        path=".",
        max_depth=max_depth,
        include_security_audit=security_audit,
        workspace_root=str(web_session.workspace_root)
    )
    return res


@router.get("/files/tree")
def get_file_tree():
    """Returns recursive file tree structure for sidebar explorer."""
    root = web_session.workspace_root
    
    def build_tree(current_dir: Path) -> List[Dict[str, Any]]:
        nodes = []
        try:
            entries = sorted(current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            for entry in entries:
                if is_ignored(entry, root):
                    continue
                is_dir = entry.is_dir()
                rel = str(entry.relative_to(root)).replace("\\", "/")
                node: Dict[str, Any] = {
                    "name": entry.name,
                    "path": rel,
                    "is_dir": is_dir
                }
                if is_dir:
                    node["children"] = build_tree(entry)
                else:
                    node["is_binary"] = is_binary_file(entry)
                nodes.append(node)
        except PermissionError:
            pass
        return nodes

    return {
        "root_name": root.name or str(root),
        "root_path": str(root),
        "tree": build_tree(root)
    }


@router.get("/files/content")
def get_file_content(path: str = Query(...)):
    """Reads file content for web editor."""
    target = resolve_path(path, str(web_session.workspace_root))
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if is_binary_file(target):
        return {"success": False, "is_binary": True, "path": path, "content": "[Binary file cannot be viewed as text]"}

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {
            "success": True,
            "path": path,
            "abs_path": str(target),
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/save")
def save_file(req: SaveFileRequest):
    """Saves file content with undo snapshot."""
    writer = WriteFileTool()
    res = writer.run(
        path=req.path,
        content=req.content,
        description=req.description or "Web editor save",
        workspace_root=str(web_session.workspace_root)
    )
    return res


@router.post("/files/revert")
def revert_last_edit():
    """Undo last file modification."""
    success, msg = undo_manager.undo_last()
    return {"success": success, "message": msg}


@router.get("/history/undo")
def get_undo_history():
    """Get list of undo snapshots."""
    return {"history": undo_manager.get_history_summary()}


@router.post("/command")
def execute_command(req: CommandRequest):
    """Execute shell command in workspace."""
    runner = RunCommandTool()
    res = runner.run(command=req.command, workspace_root=str(web_session.workspace_root))
    return res


@router.post("/chat")
def chat_stream_endpoint(req: ChatRequest):
    """
    SSE Streaming endpoint for real-time agent output.
    """
    def event_generator():
        for event in web_agent.chat_stream(req.message):
            payload = {
                "type": event.type,
                "content": event.content,
                "data": event.data
            }
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat/reset")
def reset_chat():
    """Reset agent conversation memory."""
    web_agent.reset_conversation()
    return {"success": True, "message": "Conversation history reset."}
