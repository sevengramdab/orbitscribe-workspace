"""
Monetization Mode
A swarm mode that launches 10 autonomous business agents to generate revenue.
"""

import asyncio
from typing import AsyncGenerator, Dict, Any

from core.llm_client import LLMClient
from core.session_store import SessionStore
from agents.business.swarm_orchestrator import MonetizationSwarmOrchestrator


async def run_monetization_mode(
    request: Dict[str, Any],
    llm_client: LLMClient,
    session_store: SessionStore,
    session_id: str,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Run the full monetization swarm.
    
    Request body may include:
    - verticals: List of agent names to run (default: all)
    - autonomy_tier: DEFAULT | OVERRIDE | AUTOPILOT
    - interval_seconds: How often each agent cycles (default: 300)
    - one_shot: If true, run one cycle and return instead of looping
    """
    verticals = request.get("verticals", [])
    autonomy_tier = request.get("autonomy_tier", "AUTOPILOT")
    interval = request.get("interval_seconds", 300)
    one_shot = request.get("one_shot", False)

    yield {"event": "status", "message": "🚀 Initializing Monetization Swarm..."}

    orchestrator = MonetizationSwarmOrchestrator(
        llm_client=llm_client,
        autonomy_tier=autonomy_tier,
    )

    # Filter agents if verticals specified
    agents_to_run = list(orchestrator.agents.keys())
    if verticals:
        agents_to_run = [a for a in agents_to_run if a in verticals]

    yield {
        "event": "status",
        "message": f"📊 Loaded {len(orchestrator.agents)} business agents. Running: {agents_to_run}",
    }

    if one_shot:
        yield {"event": "status", "message": "⚡ Running one-shot cycle..."}
        results = await orchestrator.run_cycle_all()
        for agent_name, result in results.items():
            yield {
                "event": "agent_cycle_complete",
                "agent": agent_name,
                "result": "success" if not isinstance(result, Exception) else f"error: {result}",
            }
    else:
        yield {"event": "status", "message": f"🔄 Starting autonomous loops (interval={interval}s)..."}
        # Fire-and-forget the long-running swarm
        asyncio.create_task(orchestrator.start_all(interval_seconds=interval))

        # Stream status updates periodically
        for _ in range(12):  # Stream for ~1 min of updates
            await asyncio.sleep(5)
            status = orchestrator.get_swarm_status()
            yield {"event": "swarm_status", "data": status}

    # Final summary
    final = orchestrator.get_swarm_status()
    yield {"event": "complete", "swarm_status": final}

    if not one_shot:
        yield {
            "event": "status",
            "message": "✅ Swarm is now running autonomously in the background. Use /api/monetization/status to check progress.",
        }
