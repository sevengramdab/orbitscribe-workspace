"""Volume Evaluator Agent for the aquaculture mesh."""
import json
from agents.base import Agent
from agents.aquaculture.types import ActionTarget, TelemetryPayload


class VolumeEvaluatorAgent(Agent):
    def __init__(self):
        super().__init__(
            name="VolumeEvaluator",
            role="Evaluates fluid volume against intake valve threshold",
            prompt_template="""You are VolumeEvaluator. Given telemetry, decide if the intake valve should open.

Task: {task}
Context: {context}""",
        )

    async def evaluate(self, payload: TelemetryPayload) -> ActionTarget:
        if payload.fluid_volume_liters < 900.0:
            return ActionTarget.INTAKE_VALVE
        return ActionTarget.STEADY_STATE

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        payload = TelemetryPayload(
            node_id="eval_node",
            fluid_volume_liters=850.0,
            ph_level=7.0,
            status=NodeStatus.ACTIVE,
        )
        result = await self.evaluate(payload)
        return json.dumps({"action": result.value})
