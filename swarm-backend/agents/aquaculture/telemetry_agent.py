"""Telemetry agent for aquaculture mesh sensors."""
import asyncio
import json
import secrets
from dataclasses import asdict

from agents.base import Agent
from agents.aquaculture.types import NodeStatus, TelemetryPayload


class TelemetryAgent(Agent):
    """Simulates sensor I/O for an aquaculture mesh."""

    def __init__(self):
        super().__init__(
            name="Telemetry",
            role="Sensor interface for aquaculture mesh",
            prompt_template="""You are a telemetry aggregator for an aquaculture mesh.

Task: {task}
Context: {context}

Respond with a concise JSON summary of node status."""
        )

    async def fetch_telemetry(self) -> TelemetryPayload:
        """Simulate async I/O to retrieve a sensor snapshot."""
        await asyncio.sleep(0.05)
        rng = secrets.SystemRandom()
        volume = rng.uniform(800.0, 1200.0)
        ph = rng.uniform(6.0, 8.0)
        status = NodeStatus.ACTIVE
        return TelemetryPayload(
            node_id=f"alpha_node_{secrets.token_hex(4)}",
            fluid_volume_liters=round(volume, 2),
            ph_level=round(ph, 2),
            status=status,
        )

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        payload = await self.fetch_telemetry()
        return json.dumps(asdict(payload))
