"""
money_engine_routes.py
======================
FastAPI routes for the mouse/keyboard money-making automation engine.
Provides REST + SSE control over the 10-agent swarm.
"""

import asyncio
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

# Lazy-import money_engine to avoid heavy deps at import time
_orchestrator = None
_bridge = None


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        import sys
        from pathlib import Path
        root = Path(__file__).parent.parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from money_engine.orchestrator import MoneyOrchestrator
        _orchestrator = MoneyOrchestrator()
    return _orchestrator


def _get_bridge():
    global _bridge
    if _bridge is None:
        import sys
        from pathlib import Path
        root = Path(__file__).parent.parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from money_engine.kimi_bridge import KimiBridge
        _bridge = KimiBridge(_get_orchestrator())
    return _bridge


# ── Request Models ──────────────────────────────────────────────────────

class MEStartRequest(BaseModel):
    verticals: Optional[List[str]] = None
    autonomy_tier: str = "DEFAULT"
    interval_seconds: int = 300
    one_shot: bool = False


class MEInjectRequest(BaseModel):
    agent_id: str
    action: str
    params: dict = {}
    reasoning: str = "manual"


class MEApproveRequest(BaseModel):
    decision_id: str
    approved: bool = True
    modified_params: Optional[dict] = None


class MEAutonomyRequest(BaseModel):
    tier: str  # DEFAULT | OVERRIDE | AUTOPILOT


class MEIntervalRequest(BaseModel):
    seconds: int


# ── SSE Helper ──────────────────────────────────────────────────────────

async def _stream_events(generator):
    async for event in generator:
        if isinstance(event, dict):
            yield f"data: {json.dumps(event)}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'text', 'chunk': str(event)})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


# ── Endpoints ───────────────────────────────────────────────────────────

@router.get("/money-engine/status")
async def me_status():
    """Get full status of the money engine and all agents."""
    orch = _get_orchestrator()
    return orch.get_status()


@router.post("/money-engine/start")
async def me_start(req: MEStartRequest):
    """Start the money engine swarm."""
    orch = _get_orchestrator()
    orch.set_autonomy(req.autonomy_tier)
    orch.set_interval(req.interval_seconds)
    result = orch.start_swarm(req.verticals, one_shot=req.one_shot)
    return result


@router.post("/money-engine/stop")
async def me_stop():
    """Stop all money engine agents."""
    orch = _get_orchestrator()
    orch.stop_all()
    return {"success": True, "message": "All money engine agents stopped"}


@router.post("/money-engine/agent/{agent_id}/stop")
async def me_stop_agent(agent_id: str):
    """Stop a specific agent."""
    orch = _get_orchestrator()
    return orch.stop_agent(agent_id)


@router.post("/money-engine/inject")
async def me_inject(req: MEInjectRequest):
    """Manually inject a decision into an agent."""
    orch = _get_orchestrator()
    return orch.inject_decision(req.agent_id, req.action, req.params, req.reasoning)


@router.post("/money-engine/autonomy")
async def me_autonomy(req: MEAutonomyRequest):
    """Set autonomy tier (DEFAULT, OVERRIDE, AUTOPILOT)."""
    orch = _get_orchestrator()
    orch.set_autonomy(req.tier)
    return {"success": True, "tier": req.tier}


@router.post("/money-engine/interval")
async def me_interval(req: MEIntervalRequest):
    """Set cycle interval in seconds."""
    orch = _get_orchestrator()
    orch.set_interval(req.seconds)
    return {"success": True, "interval_seconds": req.seconds}


@router.get("/money-engine/agents")
async def me_list_agents():
    """List all registered agent verticals."""
    import sys
    from pathlib import Path
    root = Path(__file__).parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from money_engine.orchestrator import list_agent_verticals
    return {"verticals": list_agent_verticals()}


@router.get("/money-engine/pending")
async def me_pending():
    """List pending decisions waiting for Kimi approval."""
    bridge = _get_bridge()
    return {"pending": bridge.list_pending()}


@router.post("/money-engine/approve")
async def me_approve(req: MEApproveRequest):
    """Approve a pending decision."""
    bridge = _get_bridge()
    return bridge.approve(req.decision_id, req.modified_params)


@router.post("/money-engine/reject")
async def me_reject(req: MEApproveRequest):
    """Reject a pending decision."""
    bridge = _get_bridge()
    return bridge.reject(req.decision_id, reason="Rejected via API")


@router.post("/money-engine/start-sse")
async def me_start_sse(req: MEStartRequest):
    """Start swarm and stream status events via SSE."""
    orch = _get_orchestrator()
    orch.set_autonomy(req.autonomy_tier)
    orch.set_interval(req.interval_seconds)
    result = orch.start_swarm(req.verticals, one_shot=req.one_shot)

    async def event_generator():
        yield {"event": "status", "message": "Money Engine starting...", "result": result}
        for i in range(24 if not req.one_shot else 1):
            await asyncio.sleep(5)
            status = orch.get_status()
            yield {"event": "swarm_status", "data": status}
            if not status["running"]:
                break
        yield {"event": "complete", "message": "Money Engine stream ended"}

    return StreamingResponse(_stream_events(event_generator()), media_type="text/event-stream")
