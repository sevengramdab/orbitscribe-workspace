"""
decision_intelligence.py
========================
Data Science engine for the OrbitScribe monetization swarm.

Reads agent performance data, runs analytics, and generates
"conviction reports" that persuade other agents to act.

Capabilities:
- ROI analysis per agent / vertical / decision type
- Trend detection (momentum, decay, seasonality)
- Risk-adjusted scoring (Sharpe-like ratio for decisions)
- Forecasting (simple exponential smoothing)
- A/B test analysis for competing strategies
- Persuasion packet generation for agent-to-agent influence
"""
from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime

# Agent vault discovery
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_AGENT_VAULT_DIR = _PROJECT_ROOT / "tools" / "saved_sessions"
_SWARM_BACKEND_VAULT_DIR = _PROJECT_ROOT / "swarm-backend" / "tools" / "saved_sessions"
_ORCHESTRATOR_PATH = _AGENT_VAULT_DIR / "money_engine_orchestrator.json"


@dataclass
class AgentPerformance:
    agent_id: str
    vertical: str
    lifetime_revenue: float
    lifetime_costs: float
    decisions_made: int
    decisions_executed: int
    avg_revenue_per_decision: float = 0.0
    win_rate: float = 0.0
    momentum: float = 0.0  # Recent vs historical performance ratio
    risk_score: float = 0.0
    forecast_next_7d: float = 0.0


@dataclass
class ConvictionReport:
    """A data-backed recommendation meant to persuade other agents."""
    report_id: str = field(default_factory=lambda: f"conv-{int(time.time())}")
    timestamp: float = field(default_factory=time.time)
    headline: str = ""
    confidence: float = 0.0  # 0.0 - 1.0
    reasoning: str = ""
    data_evidence: dict = field(default_factory=dict)
    recommended_action: str = ""
    target_agents: List[str] = field(default_factory=list)
    expected_outcome: dict = field(default_factory=dict)

    def to_persuasion_payload(self) -> dict:
        """Format for injection into another agent's decision queue."""
        return {
            "type": "conviction_report",
            "report_id": self.report_id,
            "headline": self.headline,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidence": self.data_evidence,
            "recommended_action": self.recommended_action,
            "expected_revenue": self.expected_outcome.get("revenue", 0),
            "expected_risk": self.expected_outcome.get("risk", 1.0),
            "urgency": self._compute_urgency(),
        }

    def _compute_urgency(self) -> float:
        """Higher confidence + lower risk = higher urgency to act."""
        risk = self.expected_outcome.get("risk", 1.0)
        rev = self.expected_outcome.get("revenue", 0)
        if rev <= 0:
            return 0.0
        return min(1.0, self.confidence * (rev / 100) / (risk + 0.1))


class DecisionIntelligenceEngine:
    """
    The swarm's data science brain.
    Analyzes historical decisions and generates persuasive recommendations.
    """

    def __init__(self):
        self.reports: List[ConvictionReport] = []
        self.agent_performances: Dict[str, AgentPerformance] = {}

    # ── Data Ingestion ───────────────────────────────────────────────────

    def load_all_vaults(self) -> Dict[str, dict]:
        """Scan saved_sessions for all agent vaults and orchestrator state."""
        data = {"agents": {}, "orchestrator": {}}

        if _ORCHESTRATOR_PATH.exists():
            try:
                data["orchestrator"] = json.loads(_ORCHESTRATOR_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Look for money_engine agent state files
        me_dir = _AGENT_VAULT_DIR / "money_engine"
        if me_dir.exists():
            for f in me_dir.glob("*_state.json"):
                try:
                    agent_data = json.loads(f.read_text(encoding="utf-8"))
                    agent_id = f.stem.replace("_state", "")
                    data["agents"][agent_id] = agent_data
                except Exception:
                    pass

        # Look for swarm-backend agent vaults
        for vault_dir in (_AGENT_VAULT_DIR, _SWARM_BACKEND_VAULT_DIR):
            if vault_dir.exists():
                for f in vault_dir.glob("agent_*_vault.json"):
                    try:
                        agent_data = json.loads(f.read_text(encoding="utf-8"))
                        agent_name = f.stem.replace("agent_", "").replace("_vault", "")
                        data["agents"][agent_name] = agent_data
                    except Exception:
                        pass

        return data

    # ── Analytics Core ───────────────────────────────────────────────────

    def analyze_performance(self, raw_data: Optional[dict] = None) -> Dict[str, AgentPerformance]:
        """Run full analytics on all agents."""
        if raw_data is None:
            raw_data = self.load_all_vaults()

        results = {}
        for agent_id, agent_data in raw_data.get("agents", {}).items():
            perf = self._compute_agent_performance(agent_id, agent_data)
            results[agent_id] = perf

        self.agent_performances = results
        return results

    def _compute_agent_performance(self, agent_id: str, data: dict) -> AgentPerformance:
        ledger = data.get("ledger", {}) if isinstance(data.get("ledger"), dict) else {}
        decisions = data.get("decisions", []) if isinstance(data.get("decisions"), list) else []
        vertical = data.get("vertical", agent_id.split("_")[0] if "_" in agent_id else "unknown")

        revenue = float(ledger.get("lifetime_revenue", 0)) if isinstance(ledger, dict) else 0.0
        costs = float(ledger.get("lifetime_costs", 0)) if isinstance(ledger, dict) else 0.0
        made = int(ledger.get("decisions_made", 0)) if isinstance(ledger, dict) else 0
        executed = int(ledger.get("decisions_executed", 0)) if isinstance(ledger, dict) else 0

        avg_rev = revenue / executed if executed > 0 else 0.0
        win_rate = executed / made if made > 0 else 0.0

        # Momentum: ratio of recent 3 decisions revenue vs historical average
        momentum = self._compute_momentum(decisions, avg_rev)

        # Risk: coefficient of variation of decision revenues
        risk = self._compute_risk(decisions)

        # Forecast: simple exponential smoothing
        forecast = self._forecast_revenue(decisions, alpha=0.3)

        return AgentPerformance(
            agent_id=agent_id,
            vertical=vertical,
            lifetime_revenue=revenue,
            lifetime_costs=costs,
            decisions_made=made,
            decisions_executed=executed,
            avg_revenue_per_decision=avg_rev,
            win_rate=win_rate,
            momentum=momentum,
            risk_score=risk,
            forecast_next_7d=forecast,
        )

    def _compute_momentum(self, decisions: List[dict], historical_avg: float) -> float:
        if not decisions or historical_avg <= 0:
            return 1.0
        recent = [d for d in decisions if d.get("actual_revenue") is not None][-3:]
        if not recent:
            return 1.0
        recent_avg = statistics.mean(d["actual_revenue"] for d in recent)
        return recent_avg / historical_avg

    def _compute_risk(self, decisions: List[dict]) -> float:
        revenues = [d["actual_revenue"] for d in decisions if d.get("actual_revenue") is not None]
        if len(revenues) < 2:
            return 0.5
        mean_rev = statistics.mean(revenues)
        if mean_rev == 0:
            return 1.0
        try:
            stdev = statistics.stdev(revenues)
            return min(1.0, stdev / abs(mean_rev))
        except Exception:
            return 0.5

    def _forecast_revenue(self, decisions: List[dict], alpha: float = 0.3) -> float:
        """Simple exponential smoothing forecast."""
        revenues = [d["actual_revenue"] for d in decisions if d.get("actual_revenue") is not None]
        if not revenues:
            return 0.0
        s = revenues[0]
        for r in revenues[1:]:
            s = alpha * r + (1 - alpha) * s
        # Extrapolate 7 days assuming daily cycles
        return round(s * 7, 2)

    # ── Cross-Agent Intelligence ─────────────────────────────────────────

    def rank_agents(self) -> List[AgentPerformance]:
        """Rank agents by risk-adjusted return (revenue / (costs + risk + 1))."""
        if not self.agent_performances:
            self.analyze_performance()

        def score(p: AgentPerformance) -> float:
            denominator = p.lifetime_costs + (p.risk_score * 10) + 1
            return (p.lifetime_revenue * p.win_rate * p.momentum) / denominator

        return sorted(self.agent_performances.values(), key=score, reverse=True)

    def detect_opportunities(self) -> List[ConvictionReport]:
        """Find high-confidence actions based on data patterns."""
        reports = []
        ranked = self.rank_agents()

        if not ranked:
            return reports

        top = ranked[0]
        if top.momentum > 1.2 and top.win_rate > 0.5 and top.forecast_next_7d > 10:
            reports.append(ConvictionReport(
                headline=f"Double down on {top.vertical}: momentum is {top.momentum:.2x}",
                confidence=min(1.0, top.win_rate * top.momentum * 0.8),
                reasoning=(
                    f"{top.agent_id} shows {top.momentum:.2f}x momentum vs historical average, "
                    f"{top.win_rate:.0%} win rate, and a 7-day forecast of ${top.forecast_next_7d:.2f}. "
                    f"Risk-adjusted score suggests this is the best-performing vertical right now."
                ),
                data_evidence={
                    "agent_id": top.agent_id,
                    "vertical": top.vertical,
                    "momentum": top.momentum,
                    "win_rate": top.win_rate,
                    "forecast_7d": top.forecast_next_7d,
                    "risk_score": top.risk_score,
                },
                recommended_action=f"increase_allocation",
                target_agents=["orchestrator", top.vertical],
                expected_outcome={"revenue": top.forecast_next_7d, "risk": top.risk_score},
            ))

        # Detect underperformers that should be paused
        for agent in ranked:
            if agent.momentum < 0.5 and agent.decisions_made > 5:
                reports.append(ConvictionReport(
                    headline=f"Pause or retrain {agent.vertical}: performance decay detected",
                    confidence=min(1.0, 1 - agent.momentum),
                    reasoning=(
                        f"{agent.agent_id} has {agent.momentum:.2f}x momentum (decay) after "
                        f"{agent.decisions_made} decisions. Win rate is {agent.win_rate:.0%}. "
                        f"Continuing allocation may be suboptimal."
                    ),
                    data_evidence={
                        "agent_id": agent.agent_id,
                        "momentum": agent.momentum,
                        "win_rate": agent.win_rate,
                        "decisions_made": agent.decisions_made,
                    },
                    recommended_action="pause_or_retrain",
                    target_agents=["orchestrator", agent.vertical],
                    expected_outcome={"revenue": 0, "risk": 0.2},
                ))
                break  # Only flag the worst underperformer

        self.reports = reports
        return reports

    # ── Persuasion Interface ─────────────────────────────────────────────

    def get_persuasion_packets(self) -> List[dict]:
        """Return all current conviction reports formatted for agent consumption."""
        if not self.reports:
            self.detect_opportunities()
        return [r.to_persuasion_payload() for r in self.reports]

    def inject_into_orchestrator(self, orchestrator: Any) -> int:
        """
        Push conviction reports into an orchestrator's decision queue.
        Returns number of injections.
        """
        packets = self.get_persuasion_packets()
        injected = 0
        for pkt in packets:
            # If orchestrator has an inject method, use it
            if hasattr(orchestrator, "inject_decision"):
                orchestrator.inject_decision(
                    agent_id="data_science_agent",
                    action=pkt["recommended_action"],
                    params={"conviction_report": pkt},
                    reasoning=pkt["reasoning"],
                )
                injected += 1
        return injected

    # ── Dashboard API ────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """High-level summary for external dashboards."""
        self.analyze_performance()
        ranked = self.rank_agents()
        opportunities = self.detect_opportunities()

        total_revenue = sum(p.lifetime_revenue for p in self.agent_performances.values())
        total_costs = sum(p.lifetime_costs for p in self.agent_performances.values())

        return {
            "total_agents_analyzed": len(self.agent_performances),
            "total_revenue_observed": total_revenue,
            "total_costs_observed": total_costs,
            "net_profit_observed": total_revenue - total_costs,
            "top_performer": asdict(ranked[0]) if ranked else None,
            "rankings": [asdict(p) for p in ranked],
            "active_opportunities": len(opportunities),
            "conviction_reports": [asdict(r) for r in opportunities],
            "persuasion_packets": self.get_persuasion_packets(),
            "generated_at": datetime.utcnow().isoformat(),
        }


# Global singleton
engine = DecisionIntelligenceEngine()
