"""Topological DAG router for aquaculture sensor telemetry."""
import graphlib
import json
import logging
from agents.base import Agent
from agents.aquaculture.types import ActionTarget, TelemetryPayload

logger = logging.getLogger(__name__)


class DAGRouterAgent(Agent):
    """Routes sensor telemetry through a DAG to select an actuator."""

    def __init__(self) -> None:
        super().__init__(
            name="DAGRouter",
            role="Topological DAG router for sensor telemetry",
            prompt_template="",
        )

    async def execute_routing(self, payload: TelemetryPayload) -> ActionTarget:
        """Evaluate payload via a topological DAG and return an action target."""
        try:
            graph = {
                "evaluate_ph": set(),
                "evaluate_volume": {"evaluate_ph"},
                "dispatch_actuator": {"evaluate_volume"},
            }
            ts = graphlib.TopologicalSorter(graph)

            for node in ts.static_order():
                if node == "dispatch_actuator":
                    if payload.ph_level < 6.5:
                        return ActionTarget.ALKALINE_PUMP
                    elif payload.fluid_volume_liters < 900.0:
                        return ActionTarget.INTAKE_VALVE
                    else:
                        return ActionTarget.STEADY_STATE

            return ActionTarget.FAILSAFE
        except Exception:
            logger.exception("DAG routing failed")
            return ActionTarget.FAILSAFE

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        """Accept a task string (JSON) and return the ActionTarget value."""
        try:
            if isinstance(task, str):
                data = json.loads(task)
                payload = TelemetryPayload(**data)
            elif isinstance(task, dict):
                payload = TelemetryPayload(**task)
            elif isinstance(task, TelemetryPayload):
                payload = task
            else:
                logger.error("Unsupported task type: %s", type(task))
                return ActionTarget.FAILSAFE.value
        except Exception:
            logger.exception("Failed to parse task into TelemetryPayload")
            return ActionTarget.FAILSAFE.value

        target = await self.execute_routing(payload)
        return target.value
