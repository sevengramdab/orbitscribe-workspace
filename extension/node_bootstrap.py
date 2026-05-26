import asyncio
import logging
import signal
import sys
import json
import secrets
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum, auto
from graphlib import TopologicalSorter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("ArchipelagoNode")

class NodeStatus(str, Enum):
    ACTIVE = "ephemeral_active"
    DORMANT = "stateless_dormant"
    CRITICAL = "failsafe_engaged"

class ActionTarget(str, Enum):
    ALKALINE_PUMP = "alkaline_pump_open"
    INTAKE_VALVE = "intake_valve_open"
    STEADY_STATE = "steady_state_idle"
    FAILSAFE = "mechanical_failsafe_engaged"

@dataclass(frozen=True)
class TelemetryPayload:
    node_id: str
    fluid_volume_liters: float
    ph_level: float
    status: NodeStatus

class SensorInterface:
    @staticmethod
    async def fetch_telemetry() -> TelemetryPayload:
        await asyncio.sleep(0.05)
        
        return TelemetryPayload(
            node_id=f"alpha_node_{secrets.token_hex(4)}",
            fluid_volume_liters=secrets.SystemRandom().uniform(800.0, 1200.0),
            ph_level=secrets.SystemRandom().uniform(6.0, 8.0),
            status=NodeStatus.ACTIVE
        )

class DAGRouter:
    def __init__(self):
        self.graph = TopologicalSorter()
        self._build_graph()

    def _build_graph(self) -> None:
        self.graph.add("evaluate_ph")
        self.graph.add("evaluate_volume", "evaluate_ph")
        self.graph.add("dispatch_actuator", "evaluate_volume")

    async def execute_routing(self, payload: TelemetryPayload) -> ActionTarget:
        try:
            execution_order = tuple(self.graph.static_order())
            for node in execution_order:
                logger.debug(f"Traversing DAG node: {node}")
            
            if payload.ph_level < 6.5:
                return ActionTarget.ALKALINE_PUMP
            elif payload.fluid_volume_liters < 900.0:
                return ActionTarget.INTAKE_VALVE
            return ActionTarget.STEADY_STATE
            
        except Exception as e:
            logger.error(f"DAG validation failure. Trace: {e}", exc_info=True)
            return ActionTarget.FAILSAFE

class EphemeralCoordinator:
    def __init__(self):
        self.running = True
        self.router = DAGRouter()
        self.sensor = SensorInterface()

    def _handle_shutdown_sync(self, sig: signal.Signals) -> None:
        logger.info(f"Termination signal {sig.name} caught. Initiating protocol stateless wipe...")
        self.running = False

    async def _handle_shutdown(self, sig: signal.Signals) -> None:
        self._handle_shutdown_sync(sig)

    async def run_lifecycle(self) -> None:
        loop = asyncio.get_running_loop()
        if sys.platform == 'win32':
            signal.signal(signal.SIGINT, lambda s, f: self._handle_shutdown_sync(signal.SIGINT))
        else:
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig, lambda s=sig: asyncio.create_task(self._handle_shutdown(s))
                )
        
        logger.info("--- BOOTING EPHEMERAL MESH NODE ---")
        try:
            while self.running:
                payload = await self.sensor.fetch_telemetry()
                logger.info(f"TELEMETRY_INGEST: {json.dumps(asdict(payload))}")
                
                target = await self.router.execute_routing(payload)
                
                if target == ActionTarget.FAILSAFE:
                    logger.critical("[SYSTEM FAULT: DEFAULTING TO MECHANICAL FAILSAFE]")
                    self.running = False
                    break
                    
                logger.info(f"[DAG ROUTE OPTIMIZED: {target.value.upper()}]")
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.warning("Asynchronous cycle manually interrupted.")
        except Exception as e:
            logger.critical(f"Fatal orchestration error: {e}", exc_info=True)
        finally:
            logger.info("Memory footprint purged. Node transitioning to dormant.")

if __name__ == "__main__":
    coordinator = EphemeralCoordinator()
    try:
        asyncio.run(coordinator.run_lifecycle())
    except KeyboardInterrupt:
        logger.info("Manual override triggered. Terminating.")
