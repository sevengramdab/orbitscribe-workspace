"""FastAPI remote control server for SimplePod."""
import base64
import os
import platform
import subprocess
import sys
import json
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import API_TOKEN, NODE_ID, NODE_NAME, NODE_ROLE, FILE_MANAGER_ROOT

app = FastAPI(title="SimplePod Remote API")


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


@app.get("/")
def root():
    return {"node_id": NODE_ID, "name": NODE_NAME, "role": NODE_ROLE}


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


def start_api_server():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SIMPLEPOD_API_PORT", "58091")), log_level="warning")

if __name__ == "__main__":
    start_api_server()
