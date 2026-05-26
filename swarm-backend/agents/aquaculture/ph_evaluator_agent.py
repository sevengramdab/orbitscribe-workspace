"""pH evaluator agent for aquaculture systems."""

import json
from agents.base import Agent
from agents.aquaculture.types import ActionTarget, TelemetryPayload


class PhEvaluatorAgent(Agent):
    """Evaluates pH levels against alkaline pump threshold."""

    def __init__(self):
        super().__init__(
            name="PhEvaluator",
            role="Evaluates pH levels against alkaline pump threshold",
            prompt_template=(
                "You are a pH evaluator for an aquaculture system.\n"
                "Given telemetry data, determine whether to activate the alkaline pump or maintain steady state.\n"
                "Task: {task}\n"
                "Context: {context}\n"
                "Respond with a JSON object containing the recommended action target."
            ),
        )

    async def evaluate(self, payload: TelemetryPayload) -> ActionTarget:
        """Evaluate pH level and return the appropriate action target."""
        if payload.ph_level < 6.5:
            return ActionTarget.ALKALINE_PUMP
        return ActionTarget.STEADY_STATE

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        """Parse telemetry from task, evaluate pH, and return a JSON result."""
        data = json.loads(task)
        payload = TelemetryPayload(ph_level=float(data["ph_level"]))
        action = await self.evaluate(payload)
        return json.dumps({"action": action.value, "agent": self.name})
