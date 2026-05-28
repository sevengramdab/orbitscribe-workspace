"""
system_routes.py
================
System-level routes for mode guard, security, decision intelligence, and keep-awake control.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.mode_guard import mode_guard, Mode, ModeGuardError
from core.decision_intelligence import engine as di_engine
from core.vault_security import secure_save, secure_load, is_sensitive
from core import config

router = APIRouter()

# ── Keep-Awake Paths ────────────────────────────────────────────────────
_KEEP_AWAKE_SCRIPT = Path(config.WORKSPACE_ROOT) / "tools" / "keep_awake_headless.py"
_KEEP_AWAKE_PID_FILE = _KEEP_AWAKE_SCRIPT.with_suffix(".pid")
_KEEP_AWAKE_SENTINEL = Path(config.WORKSPACE_ROOT) / "tools" / ".keep_awake_active"


# ── Mode Guard Endpoints ────────────────────────────────────────────────

class ModeSetRequest(BaseModel):
    mode: str  # SIMULATION or LIVE
    force: bool = False


@router.get("/system/mode")
async def get_mode_status():
    """Current SIMULATION/LIVE mode and readiness of all external systems."""
    return mode_guard.get_status()


@router.post("/system/mode")
async def set_mode(req: ModeSetRequest):
    """Switch between SIMULATION and LIVE mode."""
    result = mode_guard.set_mode(req.mode, force=req.force)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── Decision Intelligence Endpoints ─────────────────────────────────────

@router.get("/intelligence/summary")
async def intelligence_summary():
    """Full data science summary: rankings, forecasts, opportunities."""
    try:
        return di_engine.get_summary()
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.get("/intelligence/agents")
async def intelligence_agents():
    """Per-agent performance analytics."""
    di_engine.analyze_performance()
    return {
        "agents": [di_engine._compute_agent_performance(aid, data).__dict__
                   for aid, data in di_engine.load_all_vaults().get("agents", {}).items()]
    }


@router.get("/intelligence/opportunities")
async def intelligence_opportunities():
    """Active conviction reports with persuasion packets."""
    return {
        "opportunities": [r.__dict__ for r in di_engine.detect_opportunities()],
        "packets": di_engine.get_persuasion_packets(),
    }


@router.post("/intelligence/analyze")
async def force_analysis():
    """Trigger an immediate full analysis cycle."""
    di_engine.analyze_performance()
    di_engine.detect_opportunities()
    return di_engine.get_summary()


# ── Security / Vault Audit Endpoints ────────────────────────────────────

@router.get("/system/security/audit")
async def security_audit():
    """Audit what sensitive data is stored and whether it's encrypted."""
    from pathlib import Path
    root = Path(__file__).parent.parent.parent / "tools" / "saved_sessions"
    files = []
    for f in root.rglob("*.json"):
        try:
            data = secure_load(f) or {}
            files.append({
                "path": str(f.relative_to(root)),
                "size": f.stat().st_size,
                "has_sensitive_data": is_sensitive(data) if isinstance(data, dict) else False,
                "encrypted": f.with_suffix(f.suffix + ".vault").exists(),
            })
        except Exception:
            pass

    return {
        "vault_root": str(root),
        "file_count": len(files),
        "sensitive_files": [f for f in files if f["has_sensitive_data"]],
        "unencrypted_sensitive": [f for f in files if f["has_sensitive_data"] and not f["encrypted"]],
        "files": files,
    }


@router.post("/system/security/encrypt-all")
async def encrypt_all_vaults():
    """Encrypt all vault files that contain sensitive data."""
    from pathlib import Path
    root = Path(__file__).parent.parent.parent / "tools" / "saved_sessions"
    encrypted = 0
    skipped = 0
    for f in root.rglob("*.json"):
        try:
            if f.suffix == ".vault" or f.suffix == ".plaintext":
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            if is_sensitive(data):
                secure_save(data, f, force_encrypt=True)
                encrypted += 1
            else:
                skipped += 1
        except Exception:
            pass
    return {"encrypted": encrypted, "skipped": skipped}


# ── Keep-Awake Control Endpoints ────────────────────────────────────────

class KeepAwakeStartRequest(BaseModel):
    duration_hours: float  # 0 = forever


def _get_keep_awake_pid() -> int | None:
    if not _KEEP_AWAKE_PID_FILE.exists():
        return None
    try:
        return int(_KEEP_AWAKE_PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


@router.get("/system/keep-awake/status")
async def keep_awake_status():
    """Get current keep-awake status."""
    pid = _get_keep_awake_pid()
    running = False
    if pid is not None:
        running = _is_process_alive(pid)
        if not running:
            # Stale PID file — clean it up
            try:
                _KEEP_AWAKE_PID_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    last_action = None
    if _KEEP_AWAKE_SENTINEL.exists():
        try:
            mtime = _KEEP_AWAKE_SENTINEL.stat().st_mtime
            last_action = datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            pass

    return {
        "running": running,
        "pid": pid if running else None,
        "last_action": last_action,
    }


@router.post("/system/keep-awake/start")
async def keep_awake_start(req: KeepAwakeStartRequest):
    """Start keep-awake with optional duration (0 = forever)."""
    # Stop any existing instance first
    pid = _get_keep_awake_pid()
    if pid is not None and _is_process_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        try:
            _KEEP_AWAKE_PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
    try:
        _KEEP_AWAKE_SENTINEL.unlink(missing_ok=True)
    except Exception:
        pass

    if not _KEEP_AWAKE_SCRIPT.exists():
        raise HTTPException(status_code=500, detail="keep_awake_headless.py not found")

    cmd = [
        sys.executable,
        str(_KEEP_AWAKE_SCRIPT),
        "--duration",
        str(req.duration_hours),
    ]
    subprocess.Popen(
        cmd,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return {
        "ok": True,
        "message": f"Keep-awake started ({req.duration_hours}h)" if req.duration_hours > 0 else "Keep-awake started (forever)",
        "duration_hours": req.duration_hours,
    }


@router.post("/system/keep-awake/stop")
async def keep_awake_stop():
    """Stop the running keep-awake instance."""
    pid = _get_keep_awake_pid()
    stopped = False
    if pid is not None:
        if _is_process_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                stopped = True
            except Exception:
                pass
        try:
            _KEEP_AWAKE_PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    try:
        _KEEP_AWAKE_SENTINEL.unlink(missing_ok=True)
    except Exception:
        pass

    return {
        "ok": True,
        "stopped": stopped,
        "message": "Keep-awake stopped." if stopped else "Keep-awake was not running.",
    }
