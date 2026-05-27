"""FastAPI remote control server for SimplePod."""
import os
import platform
import subprocess
import sys
import json
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import API_TOKEN, NODE_ID, NODE_NAME, NODE_ROLE

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


@app.get("/")
def root():
    return {"node_id": NODE_ID, "name": NODE_NAME, "role": NODE_ROLE}


@app.post("/ping")
def ping(x_token: Optional[str] = Header(None)):
    _verify_token(x_token)
    return {"ok": True, "node_id": NODE_ID, "role": NODE_ROLE}


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


def start_api_server():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SIMPLEPOD_API_PORT", "58091")), log_level="warning")
