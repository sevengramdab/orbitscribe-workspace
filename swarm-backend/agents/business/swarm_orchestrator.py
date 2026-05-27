"""
Monetization Swarm Orchestrator
Coordinates 10 business agents to run autonomously, make decisions,
and generate revenue across multiple verticals.
"""

import asyncio
from typing import Any, Dict, List, Optional

from core.model_router import ModelRouter
from core.business_tools.vault import vault
from .base import BaseBusinessAgent, BusinessDecision
from . import _load_all_agents, BUSINESS_AGENT_REGISTRY


class MonetizationSwarmOrchestrator:
    """
    The central brain of the automated business suite.
    
    Manages 10 specialized business agents:
    1. DropshippingAgent      — E-commerce arbitrage across Etsy/Shopify/Amazon
    2. StripeAgent            — Payments, subscriptions, invoicing
    3. LeadGenAgent           — Scraping, enrichment, cold outreach
    4. AssetFactoryAgent      — AI images, videos, music, code templates
    5. PrintOnDemandAgent     — Printify integration, product creation
    6. ContentMarketingAgent  — Blogs, social, SEO, email funnels
    7. CryptoWeb3Agent        — NFTs, tokens, DeFi yield, affiliate
    8. SaasMicroAppAgent      — Spin up monetizable micro-SaaS apps
    9. MarketIntelligenceAgent— Competitor tracking, dynamic pricing
    10. AffiliateAgent        — Affiliate link automation, commission tracking
    """

    def __init__(self, model_router: ModelRouter, autonomy_tier: str = "AUTOPILOT"):
        self.model_router = model_router
        self.autonomy_tier = autonomy_tier
        self.agents: Dict[str, BaseBusinessAgent] = {}
        self.running = False
        self._load_all_agents()

    def _load_all_agents(self):
        """Lazy-load all business agent classes."""
        _load_all_agents()
        for name, agent_class in BUSINESS_AGENT_REGISTRY.items():
            if name not in self.agents:
                agent = agent_class(
                    model_router=self.model_router,
                    autonomy_tier=self.autonomy_tier,
                    decision_callback=self._on_decision,
                )
                self.agents[name] = agent

    async def _on_decision(self, decision: BusinessDecision) -> BusinessDecision:
        """
        Global decision gate. In AUTOPILOT mode most decisions pass through.
        High-risk or high-capital decisions get escalated to the swarm LLM.
        """
        if decision.risk_score > 0.8 or decision.estimated_revenue_impact > 1000:
            # Escalate to swarm-level review
            review = await self._swarm_review(decision)
            decision.status = "approved" if review.get("approve", False) else "rejected"
            decision.rationale += f" | Swarm review: {review.get('reasoning', '')}"
        else:
            decision.status = "approved"
        return decision

    async def _swarm_review(self, decision: BusinessDecision) -> Dict[str, Any]:
        """Ask the LLM to review a high-stakes decision."""
        prompt = f"""You are the Chief Risk Officer of an autonomous AI business swarm.
Review this business decision and approve or reject it.

Agent: {decision.agent_name}
Decision Type: {decision.decision_type}
Rationale: {decision.rationale}
Estimated Revenue Impact: ${decision.estimated_revenue_impact:.2f}
Risk Score: {decision.risk_score:.2f}
Confidence: {decision.confidence:.2f}
Action Payload: {decision.action_payload}

Respond in JSON:
{{
  "approve": true/false,
  "reasoning": "...",
  "conditions": ["condition 1", ...]  // optional guardrails
}}
"""
        messages = [
            {"role": "system", "content": "You are a conservative but growth-oriented business risk reviewer."},
            {"role": "user", "content": prompt},
        ]
        try:
            text = await self.model_router.chat(messages=messages, temperature=0.1)
            import json, re
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception:
            pass
        return {"approve": False, "reasoning": "Review failed, defaulting to reject for safety."}

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start_all(self, interval_seconds: int = 300):
        """Start all business agents."""
        self.running = True
        tasks = []
        for name, agent in self.agents.items():
            # Stagger starts to avoid thundering herd
            t = asyncio.create_task(self._staggered_start(agent, interval_seconds, len(tasks)))
            tasks.append(t)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _staggered_start(self, agent: BaseBusinessAgent, interval: int, index: int):
        await asyncio.sleep(index * 5)
        await agent.start(interval_seconds=interval)

    async def stop_all(self):
        """Stop all business agents."""
        self.running = False
        for agent in self.agents.values():
            await agent.stop()

    async def run_cycle_all(self):
        """Force one cycle on every agent (for manual triggers)."""
        results = await asyncio.gather(
            *[agent.cycle() for agent in self.agents.values()],
            return_exceptions=True,
        )
        return dict(zip(self.agents.keys(), results))

    # ── Status & Dashboard ────────────────────────────────────────────────

    def get_swarm_status(self) -> Dict[str, Any]:
        total_revenue = sum(a.ledger.lifetime_revenue for a in self.agents.values())
        total_costs = sum(a.ledger.lifetime_costs for a in self.agents.values())
        return {
            "running": self.running,
            "autonomy_tier": self.autonomy_tier,
            "agents": {name: agent.get_status() for name, agent in self.agents.items()},
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "net_profit": total_revenue - total_costs,
            "vault_summary": vault.summary(),
        }

    def get_agent(self, name: str) -> Optional[BaseBusinessAgent]:
        return self.agents.get(name)

    def force_decision(self, agent_name: str, decision_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manually inject a decision into an agent."""
        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": f"Agent {agent_name} not found"}
        decision = BusinessDecision(
            agent_name=agent_name,
            decision_type=decision_type,
            action_payload=payload,
            status="approved",
        )
        asyncio.create_task(agent.execute(decision))
        return {"status": "injected", "decision_id": decision.decision_id}
