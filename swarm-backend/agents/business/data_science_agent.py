"""
data_science_agent.py
=====================
An autonomous agent that continuously analyzes swarm performance
and publishes conviction reports to influence other agents.

Runs on a schedule (default: every 60 seconds) and injects
high-confidence recommendations into the orchestrator.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from .base import BaseBusinessAgent, BusinessDecision
from core.decision_intelligence import DecisionIntelligenceEngine


class DataScienceAgent(BaseBusinessAgent):
    """
    The swarm's data scientist.

    Does not make money directly. Instead, it makes OTHER agents
    make better decisions by feeding them analytics-backed convictions.
    """

    VERTICAL = "data_science"
    NAME = "Data Science Agent"
    DESCRIPTION = "Analyzes swarm performance and persuades other agents to optimize"

    def __init__(self, llm_client=None, model_router=None, autonomy_tier="AUTOPILOT", decision_callback=None):
        client = llm_client or model_router
        super().__init__(
            name=self.NAME,
            description=self.DESCRIPTION,
            llm_client=client,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )
        self.intelligence = DecisionIntelligenceEngine()
        self._last_analysis_time: float = 0.0

    # ── Autonomous Cycle ─────────────────────────────────────────────────

    async def cycle(self) -> Dict[str, Any]:
        """Run one analysis cycle and publish recommendations."""
        # Always load fresh data
        self.intelligence.analyze_performance()
        opportunities = self.intelligence.detect_opportunities()

        results = {
            "agents_analyzed": len(self.intelligence.agent_performances),
            "opportunities_found": len(opportunities),
            "injected": 0,
            "reports": [],
        }

        for report in opportunities:
            pkt = report.to_persuasion_payload()
            results["reports"].append(pkt)

            # If we have a decision callback (orchestrator), inject the recommendation
            if self.decision_callback:
                decision = BusinessDecision(
                    agent_name=self.NAME,
                    decision_type="publish_conviction",
                    action_payload={"packet": pkt},
                    estimated_revenue_impact=pkt.get("expected_revenue", 0),
                    confidence=pkt.get("confidence", 0.5),
                    rationale=pkt["reasoning"],
                )
                try:
                    # Some callbacks are async, some are sync
                    if asyncio.iscoroutinefunction(self.decision_callback):
                        await self.decision_callback(decision)
                    else:
                        self.decision_callback(decision)
                    results["injected"] += 1
                except Exception:
                    pass

        self._last_analysis_time = time.time()
        return results

    async def start(self, interval_seconds: int = 60):
        """Run continuous analysis loop."""
        self.running = True
        while self.running:
            try:
                await self.cycle()
            except Exception as e:
                # Log but don't crash the swarm
                print(f"[DataScienceAgent] Cycle error: {e}")
            await asyncio.sleep(interval_seconds)

    async def stop(self):
        self.running = False

    # ── Manual API ───────────────────────────────────────────────────────

    def get_latest_summary(self) -> dict:
        """Return current analytics summary for dashboards."""
        return self.intelligence.get_summary()

    def force_analysis(self) -> dict:
        """Trigger an immediate analysis cycle."""
        # Use asyncio.run_coroutine_threadsafe if called from sync context
        return self.intelligence.get_summary()
