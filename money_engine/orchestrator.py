"""
orchestrator.py
===============
Coordinates all 10 money-making agents.
- Starts/stops agents
- Collects P&L
- Routes Kimi override requests
- Provides FastAPI-compatible state API
"""
from __future__ import annotations

import json
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

from .base_agent import BaseMoneyAgent, AgentDecision

# Agent registry will be populated after agents are imported
_AGENT_REGISTRY: Dict[str, type] = {}


def register_agent(cls: type):
    """Decorator to register an agent class by its VERTICAL."""
    _AGENT_REGISTRY[cls.VERTICAL] = cls
    return cls


def get_agent_class(vertical: str) -> Optional[type]:
    return _AGENT_REGISTRY.get(vertical)


def list_agent_verticals() -> List[str]:
    return sorted(_AGENT_REGISTRY.keys())


@dataclass
class OrchestratorState:
    running: bool = False
    autonomy_tier: str = "DEFAULT"  # DEFAULT, OVERRIDE, AUTOPILOT
    total_revenue: float = 0.0
    total_costs: float = 0.0
    cycle_interval: int = 300
    agents: Dict[str, dict] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)


class MoneyOrchestrator:
    """
    Central orchestrator for the money-making swarm.
    """

    STATE_PATH = __import__("pathlib").Path(__file__).parent.parent / "tools" / "saved_sessions" / "money_engine_orchestrator.json"

    def __init__(self):
        self.agents: Dict[str, BaseMoneyAgent] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self.state = self._load_state()
        self._kimi_callback: Optional[Callable] = None
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> OrchestratorState:
        if self.STATE_PATH.exists():
            try:
                data = json.loads(self.STATE_PATH.read_text(encoding="utf-8"))
                return OrchestratorState(
                    running=data.get("running", False),
                    autonomy_tier=data.get("autonomy_tier", "DEFAULT"),
                    total_revenue=data.get("total_revenue", 0.0),
                    total_costs=data.get("total_costs", 0.0),
                    cycle_interval=data.get("cycle_interval", 300),
                    agents=data.get("agents", {}),
                    logs=data.get("logs", []),
                )
            except Exception:
                pass
        return OrchestratorState()

    def save_state(self):
        with self._lock:
            self.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.STATE_PATH.write_text(json.dumps({
                "running": self.state.running,
                "autonomy_tier": self.state.autonomy_tier,
                "total_revenue": self.state.total_revenue,
                "total_costs": self.state.total_costs,
                "cycle_interval": self.state.cycle_interval,
                "agents": self.state.agents,
                "logs": self.state.logs,
            }, indent=2), encoding="utf-8")

    def log(self, msg: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [ORCHESTRATOR] {msg}"
        with self._lock:
            self.state.logs.append(line)
            if len(self.state.logs) > 500:
                self.state.logs = self.state.logs[-250:]
        print(line)

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def spawn_agent(self, vertical: str, agent_id: Optional[str] = None) -> BaseMoneyAgent:
        """Create and register an agent instance."""
        cls = get_agent_class(vertical)
        if not cls:
            raise ValueError(f"Unknown vertical: {vertical}. Registered: {list_agent_verticals()}")
        agent = cls(agent_id=agent_id)
        # Wire Kimi override if set
        if self._kimi_callback:
            agent.set_kimi_override(self._kimi_callback)
        self.agents[agent.agent_id] = agent
        self.log(f"Spawned {vertical} agent: {agent.agent_id}")
        return agent

    def start_agent(self, vertical: str, agent_id: Optional[str] = None, one_shot: bool = False) -> dict:
        """Start an agent running in its own thread."""
        try:
            agent = self.spawn_agent(vertical, agent_id)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        stop_event = threading.Event()
        self._stop_events[agent.agent_id] = stop_event

        require_approval = self.state.autonomy_tier != "AUTOPILOT"
        max_cycles = 1 if one_shot else 0

        def _run():
            try:
                agent.run_loop(
                    interval=self.state.cycle_interval,
                    require_approval=require_approval,
                    max_cycles=max_cycles,
                )
            except Exception as e:
                agent.log(f"Thread crashed: {e}")
            finally:
                with self._lock:
                    self.state.agents[agent.agent_id] = agent.to_dict()
                self.save_state()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        self._threads[agent.agent_id] = t
        return {"success": True, "agent_id": agent.agent_id, "vertical": vertical}

    def stop_agent(self, agent_id: str) -> dict:
        if agent_id in self.agents:
            self.agents[agent_id].stop()
            self._stop_events.pop(agent_id, None)
            self.log(f"Stop requested for {agent_id}")
            return {"success": True}
        return {"success": False, "error": "Agent not found"}

    def stop_all(self):
        for agent_id in list(self.agents.keys()):
            self.stop_agent(agent_id)
        self.state.running = False
        self.save_state()
        self.log("All agents stopped.")

    def start_swarm(self, verticals: Optional[List[str]] = None, one_shot: bool = False) -> dict:
        """Start all (or selected) agents."""
        verticals = verticals or list_agent_verticals()
        results = []
        self.state.running = True
        for v in verticals:
            if v not in _AGENT_REGISTRY:
                results.append({"vertical": v, "success": False, "error": "Not registered"})
                continue
            res = self.start_agent(v, one_shot=one_shot)
            results.append(res)
            time.sleep(1.0)  # Stagger starts to avoid screen contention
        self.save_state()
        return {"success": True, "results": results}

    # ------------------------------------------------------------------
    # P&L & status
    # ------------------------------------------------------------------

    def update_pl(self):
        """Recompute global P&L from all agents."""
        rev = 0.0
        costs = 0.0
        agent_states = dict(self.state.agents)  # start with saved state
        for aid, agent in self.agents.items():
            d = agent.to_dict()
            rev += d.get("revenue", 0.0)
            costs += d.get("costs", 0.0)
            agent_states[aid] = d
        # If no live agents, use saved totals
        if not self.agents:
            rev = self.state.total_revenue
            costs = self.state.total_costs
        with self._lock:
            self.state.total_revenue = rev
            self.state.total_costs = costs
            self.state.agents = agent_states
        self.save_state()

    def get_status(self) -> dict:
        self.update_pl()
        return {
            "running": self.state.running,
            "autonomy_tier": self.state.autonomy_tier,
            "total_revenue": self.state.total_revenue,
            "total_costs": self.state.total_costs,
            "net_profit": round(self.state.total_revenue - self.state.total_costs, 2),
            "cycle_interval": self.state.cycle_interval,
            "agents": self.state.agents,
            "registered_verticals": list_agent_verticals(),
            "logs": self.state.logs[-50:],
        }

    # ------------------------------------------------------------------
    # Kimi bridge
    # ------------------------------------------------------------------

    def set_kimi_callback(self, callback: Callable[[BaseMoneyAgent, AgentDecision], AgentDecision]):
        """Set global Kimi override callback."""
        self._kimi_callback = callback
        for agent in self.agents.values():
            agent.set_kimi_override(callback)
        self.log("Kimi override callback set.")

    def inject_decision(self, agent_id: str, action: str, params: dict, reasoning: str = "manual") -> dict:
        """Manually inject a decision into an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}
        decision = AgentDecision(
            decision_id=f"inject_{int(time.time())}",
            timestamp=time.time(),
            action=action,
            params=params,
            reasoning=reasoning,
            approved=True,
        )
        result = agent.execute(decision)
        decision.result = result
        decision.executed = True
        return {"success": True, "decision": decision, "result": result}

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def set_autonomy(self, tier: str):
        assert tier in ("DEFAULT", "OVERRIDE", "AUTOPILOT")
        self.state.autonomy_tier = tier
        self.save_state()
        self.log(f"Autonomy set to {tier}")

    def set_interval(self, seconds: int):
        self.state.cycle_interval = max(60, seconds)
        self.save_state()
        self.log(f"Interval set to {seconds}s")
