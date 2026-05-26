"""
Lifecycle coordinator agent for managing async lifecycle loops and signal handling.
"""

import asyncio
import logging
import signal
import sys
from typing import List, Dict

from agents.base import Agent

logger = logging.getLogger(__name__)


class LifecycleCoordinatorAgent(Agent):
    """Manages the async lifecycle loop and signal handling for mesh nodes."""

    def __init__(self) -> None:
        super().__init__(
            name="LifecycleCoordinator",
            role="Manages the async lifecycle loop and signal handling for mesh nodes",
            prompt_template=""
        )
        self.running: bool = True

    async def handle_shutdown(self, sig_name: str) -> None:
        logger.info("Termination signal %s caught. Initiating protocol stateless wipe...", sig_name)
        self.running = False

    async def run(self, task: str, context: str = "", history: List[Dict] = None) -> str:
        return "Lifecycle coordinator standing by."

    def setup_signals(self, loop) -> None:
        try:
            loop.add_signal_handler(
                signal.SIGINT,
                lambda: asyncio.create_task(self.handle_shutdown("SIGINT"))
            )
            loop.add_signal_handler(
                signal.SIGTERM,
                lambda: asyncio.create_task(self.handle_shutdown("SIGTERM"))
            )
        except NotImplementedError:
            def _sigint_handler(signum, frame):
                def _schedule_shutdown():
                    loop.create_task(self.handle_shutdown("SIGINT"))
                loop.call_soon_threadsafe(_schedule_shutdown)

            signal.signal(signal.SIGINT, _sigint_handler)
