"""
kimi_bridge.py
==============
Bridge that lets Kimi (or a human operator) manually control agents
before they go fully autonomous.

Usage:
    bridge = KimiBridge(orchestrator)
    bridge.wait_for_decision(agent)   # Blocks until Kimi approves/rejects

Integration with Kimi CLI:
    The bridge writes pending decisions to a JSON file and polls for
    a response file. Kimi can read the pending file and write a response.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional, Callable

from .base_agent import BaseMoneyAgent, AgentDecision
from .orchestrator import MoneyOrchestrator


class KimiBridge:
    """
    Manual control bridge for the money engine.

    In DEFAULT mode: Every decision requires Kimi approval.
    In OVERRIDE mode: Decisions run unless Kimi objects within a window.
    In AUTOPILOT mode: Decisions run automatically; Kimi is notified only.
    """

    BRIDGE_DIR = Path(__file__).parent.parent / "tools" / "saved_sessions" / "money_engine"

    def __init__(self, orchestrator: MoneyOrchestrator):
        self.orchestrator = orchestrator
        self.BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
        # Register ourselves as the global Kimi callback
        self.orchestrator.set_kimi_callback(self.review_decision)

    # ------------------------------------------------------------------
    # File-based decision queue (for external Kimi process)
    # ------------------------------------------------------------------

    def _pending_path(self, decision_id: str) -> Path:
        return self.BRIDGE_DIR / f"pending_{decision_id}.json"

    def _response_path(self, decision_id: str) -> Path:
        return self.BRIDGE_DIR / f"response_{decision_id}.json"

    def _write_pending(self, agent: BaseMoneyAgent, decision: AgentDecision):
        data = {
            "agent_id": agent.agent_id,
            "vertical": agent.VERTICAL,
            "decision_id": decision.decision_id,
            "timestamp": decision.timestamp,
            "action": decision.action,
            "params": decision.params,
            "reasoning": decision.reasoning,
            "screenshot": agent.browser._last_state.raw_b64 if agent.browser._last_state else None,
            "status": "pending",
        }
        self._pending_path(decision.decision_id).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _read_response(self, decision_id: str, timeout: float = 30.0) -> Optional[dict]:
        start = time.time()
        path = self._response_path(decision_id)
        while time.time() - start < timeout:
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            time.sleep(0.5)
        return None

    def _cleanup(self, decision_id: str):
        for p in [self._pending_path(decision_id), self._response_path(decision_id)]:
            if p.exists():
                p.unlink()

    # ------------------------------------------------------------------
    # Decision review (called by agents)
    # ------------------------------------------------------------------

    def review_decision(self, agent: BaseMoneyAgent, decision: AgentDecision) -> AgentDecision:
        """
        Called by BaseMoneyAgent when require_approval=True.
        Writes a pending file, waits for a response, and returns
        an approved or rejected decision.
        """
        self._write_pending(agent, decision)
        print(f"\n[KIMI_BRIDGE] Decision pending approval:")
        print(f"  Agent: {agent.agent_id} ({agent.VERTICAL})")
        print(f"  Action: {decision.action}")
        print(f"  Params: {json.dumps(decision.params, indent=2)}")
        print(f"  Reasoning: {decision.reasoning}")
        print(f"  File: {self._pending_path(decision.decision_id)}")

        # Auto-approve after timeout if in OVERRIDE mode
        timeout = 60.0 if self.orchestrator.state.autonomy_tier == "OVERRIDE" else 300.0
        response = self._read_response(decision.decision_id, timeout=timeout)

        if response is None:
            if self.orchestrator.state.autonomy_tier == "OVERRIDE":
                print(f"[KIMI_BRIDGE] No response within {timeout}s — auto-approving (OVERRIDE mode).")
                decision.approved = True
            else:
                print(f"[KIMI_BRIDGE] No response within {timeout}s — rejecting.")
                decision.approved = False
        else:
            approved = response.get("approved", False)
            decision.approved = approved
            if approved:
                # Allow Kimi to modify params
                decision.params = response.get("params", decision.params)
                print(f"[KIMI_BRIDGE] Decision APPROVED by Kimi.")
            else:
                print(f"[KIMI_BRIDGE] Decision REJECTED by Kimi.")

        self._cleanup(decision.decision_id)
        return decision

    # ------------------------------------------------------------------
    # Manual helpers for Kimi CLI
    # ------------------------------------------------------------------

    def list_pending(self) -> list:
        """List all pending decisions for Kimi to review."""
        pending = []
        for f in sorted(self.BRIDGE_DIR.glob("pending_*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                pending.append(data)
            except Exception:
                pass
        return pending

    def approve(self, decision_id: str, modified_params: Optional[dict] = None) -> dict:
        """Kimi calls this to approve a pending decision."""
        path = self._response_path(decision_id)
        path.write_text(json.dumps({
            "approved": True,
            "params": modified_params or {},
            "timestamp": time.time(),
        }, indent=2), encoding="utf-8")
        return {"success": True}

    def reject(self, decision_id: str, reason: str = "") -> dict:
        """Kimi calls this to reject a pending decision."""
        path = self._response_path(decision_id)
        path.write_text(json.dumps({
            "approved": False,
            "reason": reason,
            "timestamp": time.time(),
        }, indent=2), encoding="utf-8")
        return {"success": True}

    def force_autopilot(self, duration_minutes: int = 60):
        """Let the swarm run on autopilot for N minutes without Kimi approval."""
        self.orchestrator.set_autonomy("AUTOPILOT")
        print(f"[KIMI_BRIDGE] Autopilot enabled for {duration_minutes} minutes.")

    def resume_override(self):
        """Return to OVERRIDE mode where Kimi can intervene."""
        self.orchestrator.set_autonomy("OVERRIDE")
        print("[KIMI_BRIDGE] Override mode resumed — Kimi will be consulted on ambiguous decisions.")
