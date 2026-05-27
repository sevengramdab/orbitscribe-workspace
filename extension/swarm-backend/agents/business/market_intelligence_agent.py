"""
MarketIntelligenceAgent — the swarm's eyes and ears on the market.

Monitors competitor prices, tracks search & social trends, analyses customer
sentiment, detects new entrants, and broadcasts actionable signals to the rest
of the monetisation swarm via the unified vault.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.business_tools.vault import vault

# Ensure intelligence tools are registered in the global tool registry
try:
    import core.business_tools.intelligence_tools  # noqa: F401
except Exception as _tools_err:
    print(f"[{__name__}] Warning: could not load intelligence_tools: {_tools_err}")

from .base import BaseBusinessAgent, BusinessDecision


class MarketIntelligenceAgent(BaseBusinessAgent):
    """
    Autonomous market-intelligence agent.

    Responsibilities
    ----------------
    * Perceive — continuously scan competitor prices, trends, reviews, and gaps.
    * Decide  — determine whether to alert peers, recommend products, flag
      threats, or suggest positioning shifts.
    * Execute — persist intelligence reports to the vault and emit inter-agent
      signals so that Dropshipping, Content, SaaS, and other agents stay ahead
      of the curve.
    """

    def __init__(
        self,
        model_router: Any,
        autonomy_tier: str = "AUTOPILOT",
        decision_callback: Optional[Any] = None,
    ):
        super().__init__(
            name="market_intelligence",
            description="Competitor tracking, trend analysis, sentiment mining, and pricing intelligence for the swarm.",
            model_router=model_router,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )
        # Default watchlists — can be overridden by vault configuration.
        self._default_competitor_urls = [
            "https://example-marketplace.com/product-alpha",
            "https://example-marketplace.com/product-beta",
        ]
        self._default_trend_keywords = [
            "wireless earbuds",
            "sustainable packaging",
            "AI productivity tools",
        ]
        self._default_niches = [
            "pet accessories",
            "home office gear",
        ]

    # ── Configuration helpers ────────────────────────────────────────────────

    def _load_watchlist(self, key: str, defaults: List[str]) -> List[str]:
        """Pull a watchlist from the vault or fall back to defaults."""
        try:
            cfg = vault.find("competitor_intel", limit=1)
            if cfg and isinstance(cfg[0].get(key), list):
                return cfg[0][key]
        except Exception:
            pass
        return defaults

    def _save_watchlist(self, key: str, values: List[str]):
        """Persist a watchlist back to the vault configuration document."""
        try:
            docs = vault.find("competitor_intel", limit=1)
            if docs:
                doc_id = docs[0].get("_id")
                if doc_id:
                    vault.update("competitor_intel", doc_id, {key: values})
                    return
            # No existing doc — seed one.
            vault.insert("competitor_intel", {"config": True, key: values})
        except Exception as exc:
            print(f"[{self.name}] Failed to save watchlist: {exc}")

    # ── Perception ───────────────────────────────────────────────────────────

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather market data:
        1. Competitor price snapshots.
        2. Trend momentum for tracked keywords.
        3. Review sentiment for monitored products.
        4. Market-gap / new-entrant scans.

        Returns:
            Dict keyed by domain with raw tool outputs.
        """
        competitor_urls = self._load_watchlist("competitor_urls", self._default_competitor_urls)
        trend_keywords = self._load_watchlist("trend_keywords", self._default_trend_keywords)
        niches = self._load_watchlist("niches", self._default_niches)

        perception: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "prices": [],
            "trends": [],
            "reviews": [],
            "gaps": [],
            "errors": [],
        }

        # 1. Price monitoring
        for url in competitor_urls:
            try:
                result = await self.tools.execute("monitor_competitor_price", product_url=url)
                perception["prices"].append(result)
            except Exception as exc:
                perception["errors"].append(f"price_monitor({url}): {exc}")

        # 2. Trend tracking
        for kw in trend_keywords:
            try:
                result = await self.tools.execute("track_trend", keyword=kw)
                perception["trends"].append(result)
            except Exception as exc:
                perception["errors"].append(f"track_trend({kw}): {exc}")

        # 3. Review analysis (use same URLs as competitors for simplicity)
        for url in competitor_urls:
            try:
                result = await self.tools.execute("analyze_reviews", product_url=url)
                perception["reviews"].append(result)
            except Exception as exc:
                perception["errors"].append(f"analyze_reviews({url}): {exc}")

        # 4. Market-gap / new-entrant detection
        for niche in niches:
            try:
                result = await self.tools.execute("detect_market_gap", niche=niche)
                perception["gaps"].append(result)
            except Exception as exc:
                perception["errors"].append(f"detect_market_gap({niche}): {exc}")

        # Load recent signals so the agent knows what it already broadcast.
        try:
            signals = await self.tools.execute("get_active_signals")
            perception["active_signals_count"] = signals.get("count", 0)
        except Exception:
            perception["active_signals_count"] = 0

        return perception

    # ── Decision ─────────────────────────────────────────────────────────────

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Analyse perceptions and decide whether to act.

        Possible decision types:
        * alert_price_change   — notify peers that a competitor moved price.
        * recommend_product    — suggest a new product opportunity.
        * flag_threat          — warn about a competitive or market threat.
        * suggest_positioning  — advise a brand / pricing shift.
        * no_action            — nothing urgent detected.

        Returns:
            BusinessDecision or None.
        """
        system_prompt = (
            "You are the strategic decision core of the MarketIntelligenceAgent. "
            "Given raw market perception data, decide the single most impactful action. "
            "Respond ONLY in JSON with these keys:\n"
            "  decision_type: one of [alert_price_change, recommend_product, flag_threat, suggest_positioning, no_action]\n"
            "  rationale: concise reasoning (max 2 sentences)\n"
            "  confidence: 0.0-1.0\n"
            "  risk_score: 0.0-1.0\n"
            "  estimated_revenue_impact: float (monthly $ impact, positive or negative)\n"
            "  action_payload: dict with any parameters needed for execution\n"
        )

        # Build a concise summary so the LLM isn't overwhelmed by raw tool output.
        summary = self._summarise_perception(perception)
        user_prompt = f"Market perception summary:\n{summary}\n\nWhat should the MarketIntelligenceAgent do next?"

        try:
            llm_response = await self.llm_decide(system_prompt, user_prompt)
        except Exception as exc:
            print(f"[{self.name}] LLM decision failed: {exc}")
            return None

        decision_type = llm_response.get("decision_type", "no_action")
        if decision_type == "no_action":
            return None

        confidence = float(llm_response.get("confidence", 0.5))
        risk_score = float(llm_response.get("risk_score", 0.5))
        revenue_impact = float(llm_response.get("estimated_revenue_impact", 0.0))

        decision = BusinessDecision(
            agent_name=self.name,
            decision_type=decision_type,
            rationale=llm_response.get("rationale", "No rationale provided."),
            action_payload=llm_response.get("action_payload", {}),
            confidence=confidence,
            risk_score=risk_score,
            estimated_revenue_impact=revenue_impact,
            status="pending",
        )
        return decision

    def _summarise_perception(self, perception: Dict[str, Any]) -> str:
        """Compress perception data into a short textual summary for the LLM."""
        lines: List[str] = []

        prices = perception.get("prices", [])
        if prices:
            live = [p for p in prices if p.get("source") == "live"]
            lines.append(f"Competitor prices: {len(prices)} tracked ({len(live)} live).")
            for p in prices[:3]:
                lines.append(f"  - {p.get('url', 'unknown')}: ${p.get('price')} ({p.get('source')})")

        trends = perception.get("trends", [])
        if trends:
            lines.append(f"Trends: {len(trends)} keywords tracked.")
            for t in trends[:3]:
                lines.append(f"  - '{t.get('keyword')}': momentum {t.get('momentum_score')}/100")

        reviews = perception.get("reviews", [])
        if reviews:
            avg_sentiment = sum(r.get("sentiment_score", 0) for r in reviews) / max(len(reviews), 1)
            lines.append(f"Review sentiment avg: {round(avg_sentiment, 2)} across {len(reviews)} products.")

        gaps = perception.get("gaps", [])
        if gaps:
            lines.append(f"Market gaps: {len(gaps)} niches scanned.")
            for g in gaps[:2]:
                lines.append(f"  - '{g.get('niche')}': gap score {g.get('gap_score')}, {len(g.get('opportunities', []))} opportunities")

        lines.append(f"Active unread signals in vault: {perception.get('active_signals_count', 0)}")
        return "\n".join(lines)

    # ── Execution ────────────────────────────────────────────────────────────

    async def execute(self, decision: BusinessDecision):
        """
        Execute an approved market-intelligence decision.

        Actions:
        * Persist an intelligence report to the vault.
        * Emit a signal via ``create_market_signal`` for targeted agents.
        * Update pricing recommendations when applicable.
        """
        payload = decision.action_payload or {}
        decision_type = decision.decision_type

        try:
            if decision_type == "alert_price_change":
                await self._exec_alert_price_change(payload, decision)
            elif decision_type == "recommend_product":
                await self._exec_recommend_product(payload, decision)
            elif decision_type == "flag_threat":
                await self._exec_flag_threat(payload, decision)
            elif decision_type == "suggest_positioning":
                await self._exec_suggest_positioning(payload, decision)
            else:
                decision.result_summary = f"Unhandled decision type: {decision_type}"
        except Exception as exc:
            decision.status = "failed"
            decision.result_summary = f"Execution error: {exc}"
            self.log_decision(decision)
            return

        decision.status = "executed"
        self.log_decision(decision)
        self._save_vault()

    # ── Execution sub-routines ───────────────────────────────────────────────

    async def _exec_alert_price_change(self, payload: Dict[str, Any], decision: BusinessDecision):
        """Broadcast a price-change alert and update pricing recommendations."""
        product_id = payload.get("product_id", "unknown")
        target_agents = payload.get("target_agents", ["dropshipping", "affiliate", "saas_micro_app"])

        # Generate a fresh pricing recommendation.
        pricing = await self.tools.execute(
            "generate_pricing_recommendation",
            product_id=product_id,
            target_margin=payload.get("target_margin", 0.35),
        )

        message = (
            f"Price alert: competitor movement detected for {product_id}. "
            f"Recommended price ${pricing.get('recommended_price')} "
            f"(margin {pricing.get('target_margin', 0):.0%}). {decision.rationale}"
        )

        signal = await self.tools.execute(
            "create_market_signal",
            signal_type="price_alert",
            urgency=payload.get("urgency", "medium"),
            message=message,
            target_agents=target_agents,
        )

        # Persist full report.
        vault.insert("competitor_intel", {
            "report_type": "price_alert",
            "product_id": product_id,
            "pricing_recommendation": pricing,
            "signal_id": signal.get("signal_id"),
            "decision_id": decision.decision_id,
            "created_at": datetime.utcnow().isoformat(),
        })

        decision.result_summary = f"Price alert sent (signal {signal.get('signal_id')}). Pricing rec: ${pricing.get('recommended_price')}."
        decision.actual_revenue = pricing.get("estimated_revenue_impact", 0.0)

    async def _exec_recommend_product(self, payload: Dict[str, Any], decision: BusinessDecision):
        """Broadcast a new-product-opportunity signal."""
        niche = payload.get("niche", "general")
        target_agents = payload.get("target_agents", ["dropshipping", "asset_factory", "print_on_demand"])

        # Re-run gap detection for the niche to get fresh data.
        gap = await self.tools.execute("detect_market_gap", niche=niche)

        message = (
            f"New product opportunity in '{niche}': gap score {gap.get('gap_score')}. "
            f"Top opportunities: {', '.join(gap.get('opportunities', [])[:3])}. {decision.rationale}"
        )

        signal = await self.tools.execute(
            "create_market_signal",
            signal_type="new_opportunity",
            urgency=payload.get("urgency", "medium"),
            message=message,
            target_agents=target_agents,
        )

        vault.insert("competitor_intel", {
            "report_type": "product_recommendation",
            "niche": niche,
            "gap_data": gap,
            "signal_id": signal.get("signal_id"),
            "decision_id": decision.decision_id,
            "created_at": datetime.utcnow().isoformat(),
        })

        decision.result_summary = f"Product recommendation broadcast (signal {signal.get('signal_id')})."

    async def _exec_flag_threat(self, payload: Dict[str, Any], decision: BusinessDecision):
        """Broadcast a competitive-threat warning."""
        threat_description = payload.get("threat_description", decision.rationale)
        target_agents = payload.get("target_agents", ["dropshipping", "content_marketing", "saas_micro_app"])

        signal = await self.tools.execute(
            "create_market_signal",
            signal_type="competitive_threat",
            urgency=payload.get("urgency", "high"),
            message=threat_description,
            target_agents=target_agents,
        )

        vault.insert("competitor_intel", {
            "report_type": "threat_flag",
            "threat_description": threat_description,
            "signal_id": signal.get("signal_id"),
            "decision_id": decision.decision_id,
            "created_at": datetime.utcnow().isoformat(),
        })

        decision.result_summary = f"Threat flag raised (signal {signal.get('signal_id')})."

    async def _exec_suggest_positioning(self, payload: Dict[str, Any], decision: BusinessDecision):
        """Broadcast a positioning-shift suggestion."""
        positioning_note = payload.get("positioning_note", decision.rationale)
        target_agents = payload.get("target_agents", ["content_marketing", "affiliate", "lead_gen"])

        signal = await self.tools.execute(
            "create_market_signal",
            signal_type="positioning_shift",
            urgency=payload.get("urgency", "low"),
            message=positioning_note,
            target_agents=target_agents,
        )

        vault.insert("competitor_intel", {
            "report_type": "positioning_suggestion",
            "positioning_note": positioning_note,
            "signal_id": signal.get("signal_id"),
            "decision_id": decision.decision_id,
            "created_at": datetime.utcnow().isoformat(),
        })

        decision.result_summary = f"Positioning suggestion broadcast (signal {signal.get('signal_id')})."
