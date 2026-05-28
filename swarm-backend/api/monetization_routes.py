"""
Monetization Swarm API Routes
Exposes the 10-agent autonomous business suite via REST + SSE.
"""

import asyncio
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core import config as cfg
from core.llm_client import LLMClient
from core.autonomy_engine import SSEEvent
from core.business_tools.registry import registry
from core.business_tools.vault import vault
from core.mode_guard import mode_guard, ModeGuardError
from agents.business.swarm_orchestrator import MonetizationSwarmOrchestrator
from agents.business import _load_all_agents, BUSINESS_AGENT_REGISTRY

router = APIRouter()

# Global orchestrator instance (lazy-initialized)
_orchestrator: Optional[MonetizationSwarmOrchestrator] = None


def _get_orchestrator(autonomy_tier: str = "AUTOPILOT") -> MonetizationSwarmOrchestrator:
    global _orchestrator
    if _orchestrator is None or _orchestrator.autonomy_tier != autonomy_tier:
        llm_client = LLMClient()
        _orchestrator = MonetizationSwarmOrchestrator(
            llm_client=llm_client,
            autonomy_tier=autonomy_tier,
        )
    return _orchestrator


# ── Request Models ──────────────────────────────────────────────────────

class MonetizationStartRequest(BaseModel):
    verticals: Optional[List[str]] = None
    autonomy_tier: str = "AUTOPILOT"
    interval_seconds: int = 300
    one_shot: bool = False


class MonetizationInjectRequest(BaseModel):
    agent_name: str
    decision_type: str
    payload: dict = {}


class MonetizationStatusResponse(BaseModel):
    running: bool
    autonomy_tier: str
    total_revenue: float
    total_costs: float
    net_profit: float
    vault_summary: dict
    agents: dict


# ── SSE Helper ──────────────────────────────────────────────────────────

async def _stream_events(generator):
    async for event in generator:
        if isinstance(event, dict):
            yield f"data: {json.dumps(event)}\n\n"
        elif isinstance(event, SSEEvent):
            yield f"data: {event.to_json()}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'text', 'chunk': str(event)})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


# ── Endpoints ───────────────────────────────────────────────────────────

@router.post("/monetization/start")
async def monetization_start(req: MonetizationStartRequest):
    """Start the monetization swarm (SSE stream of status)."""
    # Gate check: if any agent would execute real financial actions, verify mode
    if mode_guard.is_simulation:
        # Simulation is always allowed
        pass
    orchestrator = _get_orchestrator(req.autonomy_tier)

    async def event_generator():
        verticals = req.verticals or list(orchestrator.agents.keys())
        yield {"event": "status", "message": "🚀 Initializing Monetization Swarm..."}
        yield {"event": "status", "message": f"📊 Loaded {len(orchestrator.agents)} business agents. Running: {verticals}"}

        if req.one_shot:
            yield {"event": "status", "message": "⚡ Running one-shot cycle..."}
            results = await orchestrator.run_cycle_all()
            for agent_name, result in results.items():
                status = "success" if not isinstance(result, Exception) else f"error: {result}"
                yield {"event": "agent_cycle_complete", "agent": agent_name, "result": status}
        else:
            yield {"event": "status", "message": f"🔄 Starting autonomous loops (interval={req.interval_seconds}s)..."}
            asyncio.create_task(orchestrator.start_all(interval_seconds=req.interval_seconds))
            for i in range(12):
                await asyncio.sleep(5)
                status = orchestrator.get_swarm_status()
                yield {"event": "swarm_status", "data": status}

        final = orchestrator.get_swarm_status()
        yield {"event": "complete", "swarm_status": final}
        if not req.one_shot:
            yield {"event": "status", "message": "✅ Swarm is running autonomously in the background."}

    return StreamingResponse(_stream_events(event_generator()), media_type="text/event-stream")


@router.post("/monetization/stop")
async def monetization_stop():
    """Stop all running business agents."""
    orchestrator = _get_orchestrator()
    await orchestrator.stop_all()
    return {"ok": True, "message": "All business agents stopped."}


@router.get("/monetization/status")
async def monetization_status():
    """Get current swarm status and P&L."""
    orchestrator = _get_orchestrator()
    return orchestrator.get_swarm_status()


@router.post("/monetization/inject")
async def monetization_inject(req: MonetizationInjectRequest):
    """Manually inject a decision into a specific business agent."""
    orchestrator = _get_orchestrator()
    result = orchestrator.force_decision(req.agent_name, req.decision_type, req.payload)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/monetization/agents")
async def monetization_agents():
    """List all available business agents."""
    _load_all_agents()
    return {
        "agents": {
            name: {
                "name": name,
                "description": cls.__doc__ or "",
            }
            for name, cls in BUSINESS_AGENT_REGISTRY.items()
        }
    }


@router.get("/monetization/agent/{agent_name}")
async def monetization_agent_detail(agent_name: str):
    """Get detailed status of a single business agent."""
    orchestrator = _get_orchestrator()
    agent = orchestrator.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return agent.get_status()


@router.post("/monetization/agent/{agent_name}/cycle")
async def monetization_agent_cycle(agent_name: str):
    """Force a single business agent to run one cycle."""
    orchestrator = _get_orchestrator()
    agent = orchestrator.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    await agent.cycle()
    return {"ok": True, "agent": agent_name, "status": "cycle_complete"}


# ── Vault & Tool Explorer ───────────────────────────────────────────────

@router.get("/monetization/vault")
async def monetization_vault_summary():
    """Summary of all data in the unified business vault."""
    return {"collections": vault.summary()}


@router.get("/monetization/vault/{collection}")
async def monetization_vault_collection(collection: str, limit: int = 100):
    """List documents in a vault collection."""
    docs = vault.find(collection, limit=limit)
    return {"collection": collection, "count": len(docs), "documents": docs}


@router.get("/monetization/tools")
async def monetization_tools(category: Optional[str] = None):
    """List all registered business tools."""
    return {"tools": registry.list_tools(category=category), "categories": registry.categories()}


@router.post("/monetization/tools/{tool_name}")
async def monetization_tool_execute(tool_name: str, payload: dict):
    """Execute a business tool directly."""
    result = await registry.execute(tool_name, **payload)
    return {"tool": tool_name, "result": result}


# ── P&L & Analytics ─────────────────────────────────────────────────────

@router.get("/monetization/pl")
async def monetization_pl():
    """Profit & Loss summary across all verticals."""
    orchestrator = _get_orchestrator()
    status = orchestrator.get_swarm_status()
    return {
        "total_revenue": status["total_revenue"],
        "total_costs": status["total_costs"],
        "net_profit": status["net_profit"],
        "agent_breakdown": {
            name: {
                "revenue": a["ledger"]["lifetime_revenue"],
                "costs": a["ledger"]["lifetime_costs"],
                "decisions": a["ledger"]["decisions_made"],
                "executed": a["ledger"]["decisions_executed"],
            }
            for name, a in status["agents"].items()
        },
    }
