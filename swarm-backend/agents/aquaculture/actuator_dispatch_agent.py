"""Actuator Dispatch Agent for the aquaculture mesh."""
import json
import time
from agents.base import Agent
from agents.aquaculture.types import ActionTarget


class ActuatorDispatchAgent(Agent):
    def __init__(self):
        super().__init__(
            name="ActuatorDispatch",
            role="Dispatches final actuation commands to pumps and valves",
            prompt_template="""You are ActuatorDispatch. Route the final action target to hardware relays.

Task: {task}
Context: {context}""",
        )

    async def dispatch(self, target: ActionTarget) -> dict:
        return {
            "action": target.value,
            "relay_closed": target == ActionTarget.FAILSAFE,
            "timestamp": time.time(),
        }

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        result = await self.dispatch(ActionTarget.STEADY_STATE)
        return json.dumps(result)
