"""FastAPI remote control server for SimplePod."""
import base64
import os
import platform
import subprocess
import sys
import json
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import API_TOKEN, NODE_ID, NODE_NAME, NODE_ROLE, FILE_MANAGER_ROOT

app = FastAPI(title="SimplePod Remote API")

import os
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "monetization")
if os.path.isdir(static_dir):
    app.mount("/monetization/static", StaticFiles(directory=static_dir), name="monetization_static")


def _verify_token(token: Optional[str]) -> None:
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


class ExecRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    timeout: int = 30


class SetupRequest(BaseModel):
    script: str  # shell/batch script to run
    description: str = ""


class SyncFileRequest(BaseModel):
    filename: str
    content: str  # base64 encoded


class PathRequest(BaseModel):
    path: str


class InjectRequest(BaseModel):
    agent_name: str
    decision_type: str
    payload: dict


_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_BASE_DIR, "..", ".."))


def _project_path(*parts: str) -> str:
    return os.path.join(_PROJECT_ROOT, *parts)


def _read_json(path: str, default=None):
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def _write_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    user_agent = request.headers.get("user-agent", "").lower()
    # If accessed by a browser (not curl/api client), redirect to dashboard
    if "text/html" in accept and "curl" not in user_agent and "wget" not in user_agent:
        return RedirectResponse(url="/monetization", status_code=302)
    return {"node_id": NODE_ID, "name": NODE_NAME, "role": NODE_ROLE}


@app.get("/monetization", response_class=HTMLResponse)
def monetization_redirect():
    index_path = os.path.join(_BASE_DIR, "static", "monetization", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Monetization Dashboard</h1><p>index.html not found.</p>", status_code=404)


@app.post("/ping")
def ping(x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    return {"ok": True, "node_id": NODE_ID, "role": NODE_ROLE}


@app.get("/health")
def health(x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    return {"ok": True, "node_id": NODE_ID, "timestamp": time.time()}


@app.post("/exec")
def exec_cmd(req: ExecRequest, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        is_shell = platform.system() == "Windows"
        result = subprocess.run(
            req.command,
            shell=is_shell,
            capture_output=True,
            text=True,
            cwd=req.cwd or os.getcwd(),
            timeout=req.timeout,
        )
        return {
            "ok": True,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Command timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/status")
def status(x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    info = {
        "platform": platform.system(),
        "node_id": NODE_ID,
        "name": NODE_NAME,
        "role": NODE_ROLE,
        "python_version": platform.python_version(),
    }
    try:
        import psutil
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        info["memory_used_gb"] = round(mem.used / (1024 ** 3), 2)
        info["memory_total_gb"] = round(mem.total / (1024 ** 3), 2)
        info["disk_free_gb"] = round(psutil.disk_usage("/").free / (1024 ** 3), 2)
    except ImportError:
        pass
    return {"ok": True, **info}


@app.post("/setup")
def setup(req: SetupRequest, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        is_shell = platform.system() == "Windows"
        result = subprocess.run(
            req.script,
            shell=is_shell,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "description": req.description,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/sync")
def sync_file(req: SyncFileRequest, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        import base64
        data = base64.b64decode(req.content)
        path = os.path.join(os.getcwd(), req.filename)
        with open(path, "wb") as f:
            f.write(data)
        return {"ok": True, "saved_to": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _safe_path(requested_path: str) -> str:
    base = os.path.abspath(FILE_MANAGER_ROOT)
    target = os.path.abspath(os.path.join(base, requested_path))
    if not target.startswith(base):
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    return target


@app.post("/screenshot")
def screenshot(x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        import mss
        import mss.tools
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            img = sct.grab(monitor)
            png_bytes = mss.tools.to_png(img.rgb, img.size)
        return {"ok": True, "image_b64": base64.b64encode(png_bytes).decode()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/files/list")
def list_files(req: PathRequest, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        target = _safe_path(req.path)
        if not os.path.isdir(target):
            return {"ok": False, "error": "Not a directory"}
        entries = []
        for name in sorted(os.listdir(target)):
            full = os.path.join(target, name)
            stat = os.stat(full)
            entries.append({
                "name": name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_dir": os.path.isdir(full),
            })
        return {"ok": True, "files": entries}
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/files/download")
def download_file(req: PathRequest, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        target = _safe_path(req.path)
        if not os.path.isfile(target):
            return {"ok": False, "error": "Not a file"}
        with open(target, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        return {"ok": True, "content_b64": content}
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/files/delete")
def delete_file(req: PathRequest, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        target = _safe_path(req.path)
        if os.path.isdir(target):
            return {"ok": False, "error": "Cannot delete directories"}
        os.remove(target)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- Monetization Dashboard Routes ---

@app.get("/monetization/api/status")
def monetization_api_status():
    try:
        vault = _read_json(_project_path("tools", "saved_sessions", "unified_business_vault.json"), {})
        if vault:
            # Normalize vault fields to match dashboard JS expectations
            return {
                "ok": True,
                "active_agents": vault.get("agents_online", vault.get("active_agents", 0)),
                "queue_depth": vault.get("queue_depth", 0),
                "revenue_today": vault.get("revenue_today", vault.get("revenue", 0.0)),
                "revenue_month": vault.get("revenue_month", 0.0),
                "uptime_pct": vault.get("uptime_pct", 99.9),
                "last_event": vault.get("last_event", "System active"),
                **vault,
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {
        "ok": True,
        "active_agents": 0,
        "queue_depth": 0,
        "revenue_today": 0.0,
        "revenue_month": 0.0,
        "uptime_pct": 99.9,
        "last_event": "System active — no data yet",
    }


@app.get("/monetization/api/agents")
def monetization_api_agents():
    try:
        vault = _read_json(_project_path("tools", "saved_sessions", "unified_business_vault.json"), {})
        agents = vault.get("agents", [])
        if agents:
            return {"ok": True, "agents": agents}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "agents": []}


@app.get("/monetization/api/pl")
def monetization_api_pl():
    try:
        vault = _read_json(_project_path("tools", "saved_sessions", "unified_business_vault.json"), {})
        pl = vault.get("pl", vault.get("profit_loss", vault.get("pnl", None)))
        if pl is not None:
            return {"ok": True, "pl": pl}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "pl": {"revenue": 0.0, "costs": 0.0, "profit": 0.0}}


@app.get("/monetization/api/vault")
def monetization_api_vault():
    try:
        vault = _read_json(_project_path("tools", "saved_sessions", "unified_business_vault.json"), {})
        if vault:
            return {"ok": True, "vault": vault}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "vault": {}}


@app.get("/monetization/api/settings")
def monetization_api_settings_get():
    try:
        data = _read_json(_project_path("swarm-backend", "business_config.json"), {})
        return {"ok": True, "settings": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/monetization/api/settings")
def monetization_api_settings_post(body: dict, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        path = _project_path("swarm-backend", "business_config.json")
        _write_json(path, body)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/monetization/api/credentials")
def monetization_api_credentials_get():
    try:
        data = _read_json(_project_path("tools", "saved_sessions", "monetization_credentials.json"), [])
        return {"ok": True, "credentials": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/monetization/api/credentials")
def monetization_api_credentials_post(body: dict, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        path = _project_path("tools", "saved_sessions", "monetization_credentials.json")
        data = _read_json(path, [])
        if not isinstance(data, list):
            data = []
        if "id" not in body:
            body["id"] = f"cred_{int(time.time() * 1000)}"
        data.append(body)
        _write_json(path, data)
        return {"ok": True, "credentials": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.delete("/monetization/api/credentials/{cred_id}")
def monetization_api_credentials_delete(cred_id: str, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        path = _project_path("tools", "saved_sessions", "monetization_credentials.json")
        data = _read_json(path, [])
        if not isinstance(data, list):
            return {"ok": False, "error": "Invalid data format"}
        new_data = [c for c in data if c.get("id") != cred_id]
        removed = len(data) - len(new_data)
        _write_json(path, new_data)
        return {"ok": True, "removed": removed}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/monetization/api/links")
def monetization_api_links_get():
    try:
        data = _read_json(_project_path("tools", "saved_sessions", "monetization_links.json"), [])
        return {"ok": True, "links": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/monetization/api/links")
def monetization_api_links_post(body: dict, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        path = _project_path("tools", "saved_sessions", "monetization_links.json")
        data = _read_json(path, [])
        if not isinstance(data, list):
            data = []
        if "id" not in body:
            body["id"] = f"link_{int(time.time() * 1000)}"
        data.append(body)
        _write_json(path, data)
        return {"ok": True, "links": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.delete("/monetization/api/links/{link_id}")
def monetization_api_links_delete(link_id: str, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        path = _project_path("tools", "saved_sessions", "monetization_links.json")
        data = _read_json(path, [])
        if not isinstance(data, list):
            return {"ok": False, "error": "Invalid data format"}
        new_data = [c for c in data if c.get("id") != link_id]
        removed = len(data) - len(new_data)
        _write_json(path, new_data)
        return {"ok": True, "removed": removed}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/monetization/api/control")
def monetization_api_control_get():
    try:
        data = _read_json(_project_path("tools", "saved_sessions", "monetization_control.json"), {})
        return {"ok": True, "control": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/monetization/api/control")
def monetization_api_control_post(body: dict, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        path = _project_path("tools", "saved_sessions", "monetization_control.json")
        _write_json(path, body)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/monetization/api/inject")
def monetization_api_inject(req: InjectRequest, x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    try:
        path = _project_path("tools", "saved_sessions", "monetization_injections.json")
        data = _read_json(path, [])
        if not isinstance(data, list):
            data = []
        data.append({
            "agent_name": req.agent_name,
            "decision_type": req.decision_type,
            "payload": req.payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        _write_json(path, data)
        return {"ok": True, "injected": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def start_api_server():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SIMPLEPOD_API_PORT", "58091")), log_level="warning")


if __name__ == "__main__":
    start_api_server()
