"""Auto Mode — Intent-aware automatic dispatch.

The user doesn't pick a mode. The system reads the request, classifies intent,
and automatically routes to:
  - swarm_mode (coding, testing, fixing)
  - plan_mode (architecture, design)
  - agent_mode (research, diagram)
  - ask_mode (default Q&A)
  - aquaculture_mesh_mode (sensor mesh)
  - aoe supervisor (process manager)

Agents can also call `route_intent` as a tool to self-dispatch.
"""
import json
import asyncio
import os
from typing import AsyncGenerator, Dict, Any

from core.intent_router import classify_intent, Intent
from core.autonomy_engine import SSEEvent
from core.swarm_state import state_manager
from modes.swarm_mode import swarm_run
from modes.plan_mode import plan
from modes.agent_mode import agent_run
from modes.ask_mode import ask
from modes.aquaculture_mesh_mode import aquaculture_mesh_run
from core.aoe_client import get_aoe_client


async def auto_run(
    task: str,
    workspace_context: str = "",
    stream: bool = True,
    autonomy_level: str = "default",
    batch_mode: bool = True,
    temperature: float | None = None,
    model: str | None = None,
    orchestrator_model: str | None = None,
    subagent_mode: str | None = None,
    session_id: str | None = None,
    emit=None,
) -> AsyncGenerator[str, None]:
    """Auto-dispatch based on intent classification."""

    result = classify_intent(task)
    intent = result.intent
    mode = result.target_mode

    # Dashboard tracking
    if session_id:
        root = state_manager.create_swarm(session_id, task)
        router_agent = state_manager.spawn_agent(
            root.agent_id, "intent_router", "IntentRouter",
            system_prompt=f"Intent: {intent.value} | Confidence: {result.confidence} | Mode: {mode}"
        )
        state_manager.update_agent_status(router_agent.agent_id, "active")
        state_manager.append_thought(
            router_agent.agent_id, "intent_classified",
            f"{result.reasoning} (confidence: {result.confidence:.2f})"
        )
        await state_manager.broadcast_thought(
            session_id, router_agent.agent_id, "intent_classified", result.reasoning
        )
        await state_manager.broadcast_circuit(session_id)

    yield SSEEvent("intent", {
        "intent": intent.value,
        "confidence": result.confidence,
        "mode": mode,
        "roles": result.target_roles,
        "reasoning": result.reasoning,
    }).to_json()

    # ── Dispatch to the right mode ──
    if mode == "swarm":
        async for chunk in swarm_run(
            task=task,
            workspace_context=workspace_context,
            autonomy_level=autonomy_level,
            batch_mode=batch_mode,
            temperature=temperature,
            model=model,
            orchestrator_model=orchestrator_model,
            subagent_mode=subagent_mode,
            session_id=session_id,
        ):
            yield chunk.to_json() if hasattr(chunk, 'to_json') else str(chunk)

    elif mode == "plan":
        async for chunk in plan(
            request=task,
            workspace_context=workspace_context,
            auto_execute=False,
            stream=stream,
            temperature=temperature,
            model=model,
        ):
            yield chunk.to_json() if hasattr(chunk, 'to_json') else str(chunk)

    elif mode == "agent":
        async for chunk in agent_run(
            task=task,
            workspace_context=workspace_context,
            stream=stream,
            autonomy_level=autonomy_level,
            batch_mode=batch_mode,
            temperature=temperature,
            model=model,
            session_id=session_id,
        ):
            yield chunk.to_json() if hasattr(chunk, 'to_json') else str(chunk)

    elif mode == "mesh":
        yield SSEEvent("status", {"message": "Booting aquaculture mesh..."}).to_json()
        try:
            await aquaculture_mesh_run(
                session_id=session_id or f"mesh-auto-{id(task)}",
                task=task,
                max_cycles=5,
            )
            yield SSEEvent("status", {"message": "Mesh cycle complete. Node dormant."}).to_json()
        except Exception as e:
            yield SSEEvent("error", {"message": str(e)}).to_json()

    elif mode == "aoe":
        yield SSEEvent("status", {"message": "Dispatching to AOE supervisor..."}).to_json()
        try:
            client = get_aoe_client()
            # Check if supervisor is already responsive
            health = await client.health()
            if health.get("status") in ("ok", "degraded"):
                status = await client.mesh_status()
                if status.get("success"):
                    data = status.get("data", {})
                    msg = (
                        f"AOE supervisor online. Docker: {data.get('docker_available', False)}. "
                        f"Mesh running: {data.get('running', False)}."
                    )
                    yield SSEEvent("status", {"message": msg}).to_json()
                else:
                    yield SSEEvent("status", {"message": f"Supervisor degraded: {status.get('error')}"}).to_json()
            else:
                yield SSEEvent("status", {"message": "AOE supervisor not responding. Attempting to start..."}).to_json()
                # Attempt to start supervisor via PowerShell launcher
                import subprocess
                proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ps_script = os.path.join(proj_root, "tools", "aoe.ps1")
                subprocess.Popen(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script, "start"],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
                # Poll until it comes online
                online = await client.ensure_supervisor(max_wait=15.0)
                if online:
                    yield SSEEvent("status", {"message": "AOE supervisor started and online."}).to_json()
                else:
                    yield SSEEvent("error", {"message": "AOE supervisor failed to start within 15 seconds."}).to_json()
        except Exception as e:
            yield SSEEvent("error", {"message": f"AOE dispatch failed: {e}"}).to_json()

    else:
        # Default: ask mode
        async for chunk in ask(
            question=task,
            workspace_context=workspace_context,
            stream=stream,
            temperature=temperature,
            model=model,
        ):
            yield chunk.to_json() if hasattr(chunk, 'to_json') else str(chunk)
