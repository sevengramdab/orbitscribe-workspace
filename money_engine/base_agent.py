"""
base_agent.py
=============
Base class for all money-making agents.
Provides:
- BrowserController access
- State persistence
- Logging
- Decision loop with Kimi override support
- Integration with swarm-backend business tools
"""
from __future__ import annotations

import os
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from .browser_controller import BrowserController, BrowserState
from .vision_helper import VisionHelper


@dataclass
class AgentDecision:
    decision_id: str
    timestamp: float
    action: str
    params: Dict[str, Any]
    reasoning: str
    approved: bool = False
    executed: bool = False
    result: Optional[dict] = None


@dataclass
class AgentState:
    agent_id: str
    vertical: str
    status: str = "idle"  # idle, running, paused, error, waiting_approval
    revenue: float = 0.0
    costs: float = 0.0
    decisions_made: int = 0
    decisions_executed: int = 0
    last_run: Optional[float] = None
    ledger: List[Dict] = field(default_factory=list)
    session_log: List[str] = field(default_factory=list)


class BaseMoneyAgent(ABC):
    """
    Abstract base for money-making agents.
    Subclass and implement:
      - decide() -> AgentDecision
      - execute(decision) -> dict
      - get_default_interval() -> int
    """

    VERTICAL: str = "base"
    STATE_DIR = Path(__file__).parent.parent / "tools" / "saved_sessions" / "money_engine"

    def __init__(self, agent_id: Optional[str] = None, headless_browser: bool = False):
        self.agent_id = agent_id or f"{self.VERTICAL}_{uuid.uuid4().hex[:6]}"
        self.browser = BrowserController()
        self.vision = VisionHelper()
        self.state = self._load_state()
        self._stop_flag = False
        self._kimi_override: Optional[Callable] = None
        self._pending_decision: Optional[AgentDecision] = None

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _state_path(self) -> Path:
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)
        return self.STATE_DIR / f"{self.agent_id}_state.json"

    def _load_state(self) -> AgentState:
        path = self._state_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return AgentState(
                    agent_id=data.get("agent_id", self.agent_id),
                    vertical=data.get("vertical", self.VERTICAL),
                    status=data.get("status", "idle"),
                    revenue=data.get("revenue", 0.0),
                    costs=data.get("costs", 0.0),
                    decisions_made=data.get("decisions_made", 0),
                    decisions_executed=data.get("decisions_executed", 0),
                    last_run=data.get("last_run"),
                    ledger=data.get("ledger", []),
                    session_log=data.get("session_log", []),
                )
            except Exception:
                pass
        return AgentState(agent_id=self.agent_id, vertical=self.VERTICAL)

    def save_state(self):
        path = self._state_path()
        path.write_text(json.dumps({
            "agent_id": self.state.agent_id,
            "vertical": self.state.vertical,
            "status": self.state.status,
            "revenue": self.state.revenue,
            "costs": self.state.costs,
            "decisions_made": self.state.decisions_made,
            "decisions_executed": self.state.decisions_executed,
            "last_run": self.state.last_run,
            "ledger": self.state.ledger,
            "session_log": self.state.session_log,
        }, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(self, msg: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{self.VERTICAL}] {msg}"
        self.state.session_log.append(line)
        if len(self.state.session_log) > 500:
            self.state.session_log = self.state.session_log[-250:]
        print(line)

    # ------------------------------------------------------------------
    # Decision lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def decide(self) -> AgentDecision:
        """Produce the next decision for this agent. Must be implemented."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, decision: AgentDecision) -> dict:
        """Execute a decision. Must be implemented."""
        raise NotImplementedError

    @abstractmethod
    def get_default_interval(self) -> int:
        """Return default cycle interval in seconds."""
        return 300

    def set_kimi_override(self, callback: Callable):
        """Set a callback that receives (agent, decision) and returns approved decision."""
        self._kimi_override = callback

    def clear_kimi_override(self):
        self._kimi_override = None

    def run_cycle(self, require_approval: bool = False) -> dict:
        """
        One full decision + execute cycle.
        If require_approval is True and a kimi_override is set,
        the decision is paused until approved.
        """
        if self._stop_flag:
            return {"success": False, "error": "Agent stopped"}

        self.state.status = "running"
        self.log("Starting decision cycle...")

        try:
            decision = self.decide()
            self.state.decisions_made += 1
            self._pending_decision = decision

            if require_approval and self._kimi_override:
                self.state.status = "waiting_approval"
                self.log(f"Decision {decision.decision_id} waiting for Kimi approval: {decision.action}")
                decision = self._kimi_override(self, decision)
                if not decision.approved:
                    self.log("Decision rejected by Kimi.")
                    self.state.status = "idle"
                    self.save_state()
                    return {"success": False, "error": "Rejected by Kimi", "decision": decision}

            decision.approved = True
            self.log(f"Executing: {decision.action} | {decision.reasoning}")
            result = self.execute(decision)
            decision.result = result
            decision.executed = True
            self.state.decisions_executed += 1

            # Update P&L if result reports revenue/cost
            if isinstance(result, dict):
                self.state.revenue += result.get("revenue", 0.0)
                self.state.costs += result.get("costs", 0.0)

            self.state.ledger.append({
                "timestamp": time.time(),
                "decision_id": decision.decision_id,
                "action": decision.action,
                "revenue": result.get("revenue", 0.0) if isinstance(result, dict) else 0.0,
                "costs": result.get("costs", 0.0) if isinstance(result, dict) else 0.0,
                "success": result.get("success", False) if isinstance(result, dict) else False,
            })

            status = "completed" if (isinstance(result, dict) and result.get("success")) else "error"
            self.state.status = status
            self.state.last_run = time.time()
            self.save_state()

            self.log(f"Cycle complete: {status}")
            return {"success": True, "decision": decision, "result": result}

        except Exception as e:
            self.state.status = "error"
            self.log(f"Cycle failed: {e}")
            self.save_state()
            return {"success": False, "error": str(e)}

    def run_loop(self, interval: Optional[int] = None, require_approval: bool = False, max_cycles: int = 0):
        """Run continuous cycles."""
        interval = interval or self.get_default_interval()
        cycles = 0
        self._stop_flag = False
        while not self._stop_flag:
            self.run_cycle(require_approval=require_approval)
            cycles += 1
            if max_cycles > 0 and cycles >= max_cycles:
                self.log(f"Reached max_cycles ({max_cycles}). Stopping.")
                break
            self.log(f"Sleeping {interval}s until next cycle...")
            time.sleep(interval)
        self.state.status = "idle"
        self.save_state()

    def stop(self):
        self._stop_flag = True
        self.log("Stop flag set.")

    # ------------------------------------------------------------------
    # Shared utilities for subclasses
    # ------------------------------------------------------------------

    def generate_asset_via_registry(self, tool_name: str, **kwargs) -> dict:
        """Call swarm-backend business tool registry to generate an asset."""
        try:
            import sys
            backend = Path(__file__).parent.parent / "swarm-backend"
            if str(backend) not in sys.path:
                sys.path.insert(0, str(backend))
            from core.business_tools.registry import registry
            return asyncio_run(registry.execute(tool_name, **kwargs))
        except Exception as e:
            return {"success": False, "error": str(e)}

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "vertical": self.VERTICAL,
            "status": self.state.status,
            "revenue": self.state.revenue,
            "costs": self.state.costs,
            "net": round(self.state.revenue - self.state.costs, 2),
            "decisions_made": self.state.decisions_made,
            "decisions_executed": self.state.decisions_executed,
            "last_run": self.state.last_run,
        }


def asyncio_run(coro):
    import asyncio
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
