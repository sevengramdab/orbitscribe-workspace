"""Aquaculture Mesh Mode — 10-agent DAG orchestration with encrypted local relay."""
import asyncio
import json
import logging
import signal
import sys
import time
from dataclasses import asdict
from typing import Dict, Any

from core.swarm_state import state_manager
from agents.aquaculture.types import NodeStatus, ActionTarget, TelemetryPayload
from agents.aquaculture.telemetry_agent import TelemetryAgent
from agents.aquaculture.dag_router_agent import DAGRouterAgent
from agents.aquaculture.ph_evaluator_agent import PhEvaluatorAgent
from agents.aquaculture.volume_evaluator_agent import VolumeEvaluatorAgent
from agents.aquaculture.actuator_dispatch_agent import ActuatorDispatchAgent
from agents.aquaculture.failsafe_agent import FailsafeAgent
from agents.aquaculture.state_wipe_agent import StateWipeAgent
from agents.aquaculture.lifecycle_coordinator_agent import LifecycleCoordinatorAgent
from agents.aquaculture.network_relay_agent import NetworkRelayAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DAG_CORE] %(message)s",
)
logger = logging.getLogger("MeshOrchestrator")

MESH_AGENT_ROLES = {
    "telemetry": {
        "name": "Telemetry",
        "system": "Sensor interface for aquaculture mesh. Generates randomized telemetry payloads.",
    },
    "dag_router": {
        "name": "DAGRouter",
        "system": "Topological DAG router for sensor telemetry. Executes graphlib.TopologicalSorter routing.",
    },
    "ph_evaluator": {
        "name": "PhEvaluator",
        "system": "Evaluates pH levels against alkaline pump threshold (6.5).",
    },
    "volume_evaluator": {
        "name": "VolumeEvaluator",
        "system": "Evaluates fluid volume against intake valve threshold (900L).",
    },
    "actuator_dispatch": {
        "name": "ActuatorDispatch",
        "system": "Dispatches final actuation commands to pumps and valves.",
    },
    "failsafe": {
        "name": "Failsafe",
        "system": "Monitors DAG validation and triggers mechanical failsafe on unhandled exceptions.",
    },
    "state_wipe": {
        "name": "StateWipe",
        "system": "Ephemeral shutdown agent. Purges all session state and transitions node to dormant.",
    },
    "lifecycle_coordinator": {
        "name": "LifecycleCoordinator",
        "system": "Manages the async lifecycle loop and signal handling for mesh nodes.",
    },
    "network_relay": {
        "name": "NetworkRelay",
        "system": "Encrypts and broadcasts actuator payloads over local mesh network before physical actuation.",
    },
    "mesh_network": {
        "name": "MeshNetwork",
        "system": "Handles inter-node communication stubs and topology gossip.",
    },
}


class EphemeralMeshOrchestrator:
    """Master control board for the 10-node aquaculture mesh.

    Execution flow:
        1. Telemetry ingest (encrypted sensor I/O)
        2. DAG topological routing (evaluate_ph → evaluate_volume → dispatch_actuator)
        3. Parallel threshold confirmation (pH + Volume via asyncio.gather)
        4. Encrypted local mesh broadcast (NetworkRelayAgent → peers)
        5. Physical relay actuation (ActuatorDispatchAgent)
        6. Stateless wipe on shutdown
    """

    def __init__(self, session_id: str, task: str = ""):
        self.session_id = session_id
        self.task = task
        self.is_active = True
        self.telemetry = TelemetryAgent()
        self.router = DAGRouterAgent()
        self.dispatcher = ActuatorDispatchAgent()
        self.wiper = StateWipeAgent()
        self.network = NetworkRelayAgent()
        self.failsafe = FailsafeAgent()
        self._agents: Dict[str, Any] = {}
        self._spawn_dashboard_nodes()

    def _spawn_dashboard_nodes(self) -> None:
        root = state_manager.create_swarm(self.session_id, self.task)
        for role_key, cfg in MESH_AGENT_ROLES.items():
            node = state_manager.spawn_agent(
                parent_id=root.agent_id,
                role=role_key,
                name=cfg["name"],
                system_prompt=cfg["system"],
            )
            self._agents[role_key] = node
            state_manager.update_agent_status(node.agent_id, "idle")

    # ── Graceful Shutdown ──

    async def _graceful_shutdown(self, sig_name: str) -> None:
        logger.warning(
            "Interrupt signal %s detected. Tripping master breaker and initiating state wipe...",
            sig_name,
        )
        self.is_active = False

    def _setup_signals(self) -> None:
        loop = asyncio.get_running_loop()
        if sys.platform == "win32":
            signal.signal(
                signal.SIGINT,
                lambda s, f: loop.create_task(self._graceful_shutdown("SIGINT")),
            )
        else:
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig, lambda s=sig: asyncio.create_task(self._graceful_shutdown(s.name))
                )

    # ── Core Execution Loop ──

    async def _execute_mesh_cycle(self, cycle: int) -> None:
        try:
            # 1. Telemetry ingest
            payload: TelemetryPayload = await self.telemetry.fetch_telemetry()
            ingest = asdict(payload)
            logger.info("INGEST: %s", json.dumps(ingest))
            await state_manager.broadcast(
                self.session_id, {"type": "telemetry", "cycle": cycle, **ingest}
            )

            # 2. DAG topological routing
            action_target: ActionTarget = await self.router.execute_routing(payload)

            # 3. Parallel evaluator confirmation (mesh swarm pattern)
            ph_eval = PhEvaluatorAgent()
            vol_eval = VolumeEvaluatorAgent()
            ph_result, vol_result = await asyncio.gather(
                ph_eval.evaluate(payload), vol_eval.evaluate(payload)
            )

            # Consistency check: if evaluators disagree with router on steady-state, escalate
            if action_target == ActionTarget.STEADY_STATE and (
                ph_result != ActionTarget.STEADY_STATE or vol_result != ActionTarget.STEADY_STATE
            ):
                action_target = ActionTarget.FAILSAFE

            if action_target == ActionTarget.FAILSAFE:
                logger.critical("[SYSTEM FAULT: DEFAULTING TO MECHANICAL FAILSAFE]")
                failsafe_node = self._agents.get("failsafe")
                if failsafe_node:
                    state_manager.update_agent_status(failsafe_node.agent_id, "error")
                await state_manager.broadcast(
                    self.session_id, {"type": "failsafe", "cycle": cycle}
                )
                await self.dispatcher.dispatch(action_target)
                self.is_active = False
                return

            # 4. Physical relay actuation
            dispatch_local = await self.dispatcher.dispatch(action_target)
            logger.info("[DAG ROUTE OPTIMIZED: %s]", action_target.value.upper())

            # 5. Encrypted local mesh broadcast (pre-actuation or post-actuation ack)
            encrypted_broadcast = await self.network.broadcast({
                "action": action_target.value,
                "relay_closed": action_target == ActionTarget.FAILSAFE,
                "timestamp": dispatch_local["timestamp"],
                "node_id": payload.node_id,
                "cycle": cycle,
            })
            logger.info(
                "[LOCAL ENCRYPTED BROADCAST] %d peers reached",
                len(encrypted_broadcast),
            )

            # Dashboard commit
            for role_key in (
                "telemetry", "dag_router", "ph_evaluator",
                "volume_evaluator", "actuator_dispatch", "network_relay",
            ):
                node = self._agents.get(role_key)
                if node:
                    state_manager.update_agent_status(node.agent_id, "committed")
                    state_manager.append_thought(
                        node.agent_id, "cycle_complete", f"cycle {cycle}: {action_target.value}"
                    )

            await state_manager.broadcast(
                self.session_id,
                {
                    "type": "cycle_complete",
                    "cycle": cycle,
                    "action": action_target.value,
                    "dispatch": dispatch_local,
                    "broadcast_peers": len(encrypted_broadcast),
                },
            )

        except Exception as exc:
            logger.critical("DAG execution fault: %s. Executing mechanical failsafe.", exc, exc_info=True)
            await self.failsafe.check(exc)
            self.is_active = False

    # ── Main Loop ──

    async def spin_up_swarm(self, max_cycles: int = 5) -> None:
        self._setup_signals()
        logger.info("=== ARCHIPELAGO MESH NODE ALPHA : ONLINE ===")

        try:
            cycle = 0
            while self.is_active and cycle < max_cycles:
                cycle += 1
                await self._execute_mesh_cycle(cycle)
                await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("Asynchronous task cancelled by host environment.")
        finally:
            await self.wiper.purge(self.session_id)
            logger.info("=== EPHEMERAL STATE WIPED. NODE DORMANT. ===")
            await state_manager.broadcast(
                self.session_id, {"type": "shutdown", "status": "dormant"}
            )


async def aquaculture_mesh_run(session_id: str, task: str, max_cycles: int = 5) -> None:
    """Top-level entrypoint for the aquaculture mesh mode."""
    orchestrator = EphemeralMeshOrchestrator(session_id, task)
    await orchestrator.spin_up_swarm(max_cycles)


if __name__ == "__main__":
    import uuid
    sid = f"aoe-mesh-{uuid.uuid4().hex[:8]}"
    asyncio.run(aquaculture_mesh_run(session_id=sid, task="bare-metal aquaculture mesh", max_cycles=5))
