"""
money_engine_bridge.py
======================
Bridge between SimplePod FastAPI and the Money Engine.

Provides:
- Lazy initialization of MoneyOrchestrator
- Status aggregation for SimplePod dashboard
- Start/stop/inject proxy methods
- Unified vault sync (writes Money Engine P&L to unified_business_vault.json)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Ensure project root is on path so we can import money_engine
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_orchestrator = None
_bridge = None


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from money_engine.orchestrator import MoneyOrchestrator
        _orchestrator = MoneyOrchestrator()
    return _orchestrator


def _get_bridge():
    global _bridge
    if _bridge is None:
        from money_engine.kimi_bridge import KimiBridge
        _bridge = KimiBridge(_get_orchestrator())
    return _bridge


def _project_path(*parts: str) -> str:
    return str(_PROJECT_ROOT.joinpath(*parts))


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


# ── Public API ───────────────────────────────────────────────────────────

def get_status() -> dict:
    """Get Money Engine status for SimplePod dashboard."""
    try:
        orch = _get_orchestrator()
        status = orch.get_status()
        return {
            "ok": True,
            "running": status.get("running", False),
            "autonomy_tier": status.get("autonomy_tier", "DEFAULT"),
            "total_revenue": status.get("total_revenue", 0.0),
            "total_costs": status.get("total_costs", 0.0),
            "net_profit": status.get("net_profit", 0.0),
            "cycle_interval": status.get("cycle_interval", 300),
            "agents": status.get("agents", {}),
            "registered_verticals": status.get("registered_verticals", []),
            "logs": status.get("logs", [])[-20:],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def start_swarm(verticals: Optional[List[str]] = None, autonomy_tier: str = "DEFAULT", interval_seconds: int = 300, one_shot: bool = False) -> dict:
    """Start the Money Engine swarm."""
    try:
        orch = _get_orchestrator()
        orch.set_autonomy(autonomy_tier)
        orch.set_interval(interval_seconds)
        result = orch.start_swarm(verticals=verticals, one_shot=one_shot)
        _sync_vault()
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stop_swarm() -> dict:
    """Stop all Money Engine agents."""
    try:
        orch = _get_orchestrator()
        orch.stop_all()
        _sync_vault()
        return {"ok": True, "message": "Money Engine stopped"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stop_agent(agent_id: str) -> dict:
    """Stop a specific agent."""
    try:
        orch = _get_orchestrator()
        return orch.stop_agent(agent_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def inject_decision(agent_id: str, action: str, params: dict, reasoning: str = "manual") -> dict:
    """Inject a manual decision into an agent."""
    try:
        orch = _get_orchestrator()
        return orch.inject_decision(agent_id, action, params, reasoning)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_pending() -> list:
    """List pending decisions."""
    try:
        bridge = _get_bridge()
        return bridge.list_pending()
    except Exception:
        return []


def approve_decision(decision_id: str, modified_params: Optional[dict] = None) -> dict:
    try:
        bridge = _get_bridge()
        return bridge.approve(decision_id, modified_params)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def reject_decision(decision_id: str) -> dict:
    try:
        bridge = _get_bridge()
        return bridge.reject(decision_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_agents_for_dashboard() -> List[dict]:
    """Return agent list in SimplePod dashboard format."""
    status = get_status()
    if not status.get("ok"):
        return []
    agents = []
    for aid, data in status.get("agents", {}).items():
        agents.append({
            "id": aid,
            "name": data.get("vertical", aid).title() + " Agent",
            "status": data.get("status", "idle"),
            "tasks_completed": data.get("decisions_executed", 0),
            "revenue": data.get("revenue", 0.0),
            "last_active": _format_time(data.get("last_run")),
        })
    return agents


def get_control_state() -> dict:
    """Return control state compatible with SimplePod dashboard."""
    status = get_status()
    if not status.get("ok"):
        return {
            "master_switch": False,
            "mode": "manual",
            "agents": [],
            "log": [],
        }

    agents = []
    for v in status.get("registered_verticals", []):
        # Find if any agent of this vertical is running
        running = False
        enabled = False
        for aid, data in status.get("agents", {}).items():
            if data.get("vertical") == v:
                enabled = True
                if data.get("status") in ("running", "completed"):
                    running = True
        agents.append({
            "id": v,
            "name": v.title() + " Agent",
            "enabled": enabled,
            "running": running,
        })

    logs = []
    for line in status.get("logs", [])[-10:]:
        logs.append({
            "time": line[:19] if line.startswith("[") else "now",
            "level": "info",
            "message": line,
        })

    return {
        "master_switch": status.get("running", False),
        "mode": "auto" if status.get("autonomy_tier") == "AUTOPILOT" else "manual",
        "agents": agents,
        "log": logs,
    }


def _sync_vault():
    """Write Money Engine P&L to unified_business_vault.json so SimplePod dashboard shows real data."""
    try:
        status = get_status()
        if not status.get("ok"):
            return
        vault_path = _project_path("tools", "saved_sessions", "unified_business_vault.json")
        vault = _read_json(vault_path, {})

        vault["revenue_today"] = status.get("total_revenue", 0.0)
        vault["revenue_month"] = status.get("total_revenue", 0.0)
        vault["active_agents"] = len(status.get("agents", {}))
        vault["last_event"] = f"Money Engine: ${status.get('net_profit', 0):.2f} net profit"

        # Build agents list for vault
        agents = []
        for aid, data in status.get("agents", {}).items():
            agents.append({
                "id": aid,
                "name": data.get("vertical", aid).title(),
                "status": data.get("status", "idle"),
                "tasks_completed": data.get("decisions_executed", 0),
                "revenue": data.get("revenue", 0.0),
                "last_active": _format_time(data.get("last_run")),
            })
        vault["agents"] = agents

        # Build P&L
        vault["pl"] = {
            "revenue": status.get("total_revenue", 0.0),
            "costs": status.get("total_costs", 0.0),
            "profit": status.get("net_profit", 0.0),
        }

        _write_json(vault_path, vault)
    except Exception:
        pass


def _format_time(ts) -> str:
    if not ts:
        return "—"
    try:
        delta = time.time() - float(ts)
        if delta < 60:
            return "just now"
        if delta < 3600:
            return f"{int(delta/60)} min ago"
        return f"{int(delta/3600)} hr ago"
    except Exception:
        return str(ts)
