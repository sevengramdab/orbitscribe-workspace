"""Failsafe Agent for the aquaculture mesh."""
from agents.base import Agent
from agents.aquaculture.types import ActionTarget


class FailsafeAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Failsafe",
            role="Monitors DAG validation and triggers mechanical failsafe on unhandled exceptions",
            prompt_template="""You are Failsafe. Watch for errors and trigger failsafe when needed.

Task: {task}
Context: {context}""",
        )

    async def check(self, exception: Exception | None) -> ActionTarget:
        if exception is not None:
            return ActionTarget.FAILSAFE
        return ActionTarget.STEADY_STATE

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        if "error" in task.lower():
            return ActionTarget.FAILSAFE.value
        return ActionTarget.STEADY_STATE.value
