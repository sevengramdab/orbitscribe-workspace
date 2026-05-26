"""State Wipe Agent for the aquaculture mesh."""
import logging
from agents.base import Agent
from core.swarm_state import state_manager

logger = logging.getLogger("ArchipelagoNode")


class StateWipeAgent(Agent):
    def __init__(self):
        super().__init__(
            name="StateWipe",
            role="Ephemeral shutdown agent. Purges all session state and transitions node to dormant",
            prompt_template="""You are StateWipe. Purge memory footprint and transition to dormant.

Task: {task}
Context: {context}""",
        )

    async def purge(self, session_id: str) -> None:
        logger.info("Memory footprint purged. Node transitioning to dormant.")
        state_manager.remove_swarm(session_id)

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        return "stateless wipe complete"
