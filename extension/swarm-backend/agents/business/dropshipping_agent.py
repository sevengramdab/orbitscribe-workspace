"""
DropshippingAgent — Autonomous e-commerce arbitrage agent.

Operates across Etsy, Shopify, Amazon, and eBay mental models.
While current tooling is optimized for Etsy, the architecture is designed
to scale to additional platforms as integrations mature.

Business cycle:
  1. perceive()  → Gather vault state, competitor intel, and trending data.
  2. decide()    → LLM-driven decision with confidence / risk / revenue scoring.
  3. execute()   → Perform the action via registered business tools.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from core.business_tools.registry import BusinessToolRegistry
from core.business_tools.vault import vault
from core.model_router import ModelRouter

from .base import BaseBusinessAgent, BusinessDecision

# Trigger registration of dropshipping tools on module import
import core.business_tools.dropshipping_tools  # noqa: F401


class DropshippingAgent(BaseBusinessAgent):
    """
    Autonomous dropshipping agent for multi-platform e-commerce arbitrage.

    Supports mental models for:
        - Etsy (active tooling)
        - Shopify (structured for future integration)
        - Amazon  (structured for future integration)
        - eBay    (structured for future integration)

    Vault collections used:
        - products
        - listings
        - pricing_history
        - competitor_intel
    """

    SUPPORTED_PLATFORMS: List[str] = ["etsy", "shopify", "amazon", "ebay"]
    DEFAULT_PLATFORM: str = "etsy"

    def __init__(
        self,
        model_router: ModelRouter,
        autonomy_tier: str = "AUTOPILOT",
        decision_callback=None,
    ):
        super().__init__(
            name="DropshippingAgent",
            description=(
                "Autonomous e-commerce arbitrage agent for Etsy, Shopify, "
                "Amazon, and eBay"
            ),
            model_router=model_router,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )

    # ── Perception ────────────────────────────────────────────────────────────

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather market data, internal state, and competitive intelligence.

        Returns a structured perception dict containing:
            - vault_summary: counts across collections
            - existing_products: current product catalogue
            - underperformers: products with no recent sales
            - competitor_intel: latest competitor data from web search
            - trending_analysis: LLM-synthesized trend report
            - platform_focus: which platform the agent is optimizing for
        """
        perception: Dict[str, Any] = {
            "agent": self.name,
            "platform_focus": self.DEFAULT_PLATFORM,
        }

        # 1. Vault snapshot
        perception["vault_summary"] = vault.summary()
        existing_products = vault.find("products", limit=50)
        perception["existing_products"] = existing_products
        perception["product_count"] = len(existing_products)

        # 2. Underperformers
        underperformers = await self.tools.execute(
            "get_underperforming_products", days=30
        )
        perception["underperformers"] = underperformers.get("products", [])
        perception["underperformer_count"] = underperformers.get("count", 0)

        # 3. Competitor intel — research top niches from existing products or defaults
        niches_to_research = self._extract_niches(existing_products)
        competitor_results: List[Dict[str, Any]] = []
        for niche in niches_to_research[:3]:
            try:
                result = await self.tools.execute(
                    "get_competitor_intel",
                    niche=niche,
                    platform=self.DEFAULT_PLATFORM,
                )
                competitor_results.append(result)
            except Exception as exc:
                competitor_results.append(
                    {"niche": niche, "error": str(exc)}
                )
        perception["competitor_intel"] = competitor_results

        # 4. Trending research via web search + LLM synthesis
        trend_research = await self.tools.execute(
            "research_trends",
            niche=niches_to_research[0] if niches_to_research else "home decor",
        )
        perception["raw_trend_results"] = trend_research.get("results", [])

        # 5. LLM synthesis of opportunities
        trending_analysis = await self._analyze_trends(perception)
        perception["trending_analysis"] = trending_analysis

        return perception

    # ── Decision ──────────────────────────────────────────────────────────────

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Given perceptions, decide the next highest-ROI business action.

        Possible decision types:
            - create_listing   : Launch a new product listing.
            - adjust_price     : Modify price of an existing product.
            - pause_product    : Pause an underperforming listing.
            - source_product   : Research and save a new product idea.

        Returns a BusinessDecision with confidence, risk_score, and
        estimated_revenue_impact, or None if no action is warranted.
        """
        system_prompt = (
            "You are the Dropshipping Strategy Engine. Given market data, "
            "decide the single best action to take. Respond ONLY with valid JSON "
            "matching the schema below."
        )

        user_prompt = self._build_decision_prompt(perception)

        try:
            raw = await self.model_router.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
        except Exception as exc:
            # Fallback: log and take no action
            print(f"[{self.name}] LLM decision error: {exc}")
            return None

        decision_data = self._extract_json(raw)
        if not decision_data:
            print(f"[{self.name}] Could not parse decision JSON: {raw[:200]}")
            return None

        decision_type = decision_data.get("decision_type", "noop")
        if decision_type == "noop":
            return None

        decision = BusinessDecision(
            agent_name=self.name,
            decision_type=decision_type,
            rationale=decision_data.get("rationale", ""),
            action_payload=decision_data.get("action_payload", {}),
            estimated_revenue_impact=float(
                decision_data.get("estimated_revenue_impact", 0.0)
            ),
            risk_score=float(decision_data.get("risk_score", 0.5)),
            confidence=float(decision_data.get("confidence", 0.5)),
            status="pending",
        )
        return decision

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute(self, decision: BusinessDecision):
        """
        Execute an approved decision using registered business tools.

        Updates the decision object with result summary and status.
        """
        payload = decision.action_payload
        result_summary = ""
        actual_revenue = 0.0
        status = "failed"

        try:
            if decision.decision_type == "create_listing":
                result = await self._execute_create_listing(payload)
                result_summary = result.get("summary", "")
                status = result.get("status", "failed")

            elif decision.decision_type == "adjust_price":
                result = await self._execute_adjust_price(payload)
                result_summary = result.get("summary", "")
                status = result.get("status", "failed")
                actual_revenue = result.get("projected_delta", 0.0)

            elif decision.decision_type == "pause_product":
                result = await self._execute_pause_product(payload)
                result_summary = result.get("summary", "")
                status = result.get("status", "failed")

            elif decision.decision_type == "source_product":
                result = await self._execute_source_product(payload)
                result_summary = result.get("summary", "")
                status = result.get("status", "failed")

            else:
                result_summary = f"Unknown decision type: {decision.decision_type}"
                status = "failed"

        except Exception as exc:
            result_summary = f"Execution error: {exc}"
            status = "failed"

        decision.status = status
        decision.result_summary = result_summary
        decision.actual_revenue = actual_revenue
        self.log_decision(decision)
        self._save_vault()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _extract_niches(self, products: List[Dict[str, Any]]) -> List[str]:
        """Derive unique niches from existing products or return defaults."""
        niches: List[str] = []
        for p in products:
            niche = p.get("niche") or p.get("category")
            if niche and niche not in niches:
                niches.append(niche)
        if not niches:
            niches = ["home decor", "digital planners", "personalized gifts"]
        return niches

    async def _analyze_trends(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Use the LLM to synthesize raw trend data into actionable insights."""
        raw_results = perception.get("raw_trend_results", [])
        products = perception.get("existing_products", [])
        underperformers = perception.get("underperformers", [])

        trend_text = "\n".join(
            f"- {r.get('title', '')} ({r.get('url', '')})" for r in raw_results[:10]
        )
        product_text = "\n".join(
            f"- {p.get('name', 'Unnamed')} ({p.get('platform', 'etsy')}, sales={p.get('sales_count', 0)})"
            for p in products[:10]
        )
        underperf_text = "\n".join(
            f"- {p.get('name', 'Unnamed')}" for p in underperformers[:10]
        )

        prompt = f"""Analyze the following dropshipping market data and respond with JSON.

Existing Products:
{product_text or "None"}

Underperforming Products:
{underperf_text or "None"}

Trending Web Results:
{trend_text or "No data"}

Respond in JSON:
{{
  "top_opportunity": "...",
  "recommended_niche": "...",
  "recommended_platform": "etsy|shopify|amazon|ebay",
  "risk_level": "low|medium|high",
  "reasoning": "..."
}}
"""
        try:
            text = await self.model_router.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a market research analyst specializing in "
                            "e-commerce trends. Be concise."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            return self._extract_json(text) or {"raw": text}
        except Exception as exc:
            return {"error": str(exc)}

    def _build_decision_prompt(self, perception: Dict[str, Any]) -> str:
        """Construct the structured prompt for the decision LLM."""
        analysis = perception.get("trending_analysis", {})
        product_count = perception.get("product_count", 0)
        underperformer_count = perception.get("underperformer_count", 0)

        return f"""You are the Dropshipping Strategy Engine.

Current State:
- Active products in vault: {product_count}
- Underperforming products: {underperformer_count}
- Platform focus: {perception.get('platform_focus', 'etsy')}

Market Analysis:
- Top opportunity: {analysis.get('top_opportunity', 'N/A')}
- Recommended niche: {analysis.get('recommended_niche', 'N/A')}
- Risk level: {analysis.get('risk_level', 'N/A')}
- Reasoning: {analysis.get('reasoning', 'N/A')}

Choose ONE decision type and respond in JSON:
{{
  "decision_type": "create_listing|adjust_price|pause_product|source_product|noop",
  "rationale": "...",
  "confidence": 0.0-1.0,
  "risk_score": 0.0-1.0,
  "estimated_revenue_impact": float,
  "action_payload": {{
    // For create_listing:  {{ "product_name": "...", "niche": "...", "cost": float, "price": float, "platform": "..." }}
    // For adjust_price:    {{ "product_id": "...", "new_price": float }}
    // For pause_product:   {{ "product_id": "..." }}
    // For source_product:  {{ "product_name": "...", "niche": "...", "cost": float, "price": float, "platform": "..." }}
    // For noop: {{}}
  }}
}}

Rules:
- If underperformer_count > 3, strongly consider pause_product.
- If product_count < 5, strongly consider source_product or create_listing.
- Confidence > 0.8 and risk_score < 0.4 for high-conviction moves.
"""

    async def _execute_create_listing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate listing content and save the product + listing to vault."""
        product_name = payload.get("product_name", "")
        niche = payload.get("niche", "")
        platform = payload.get("platform", self.DEFAULT_PLATFORM)
        cost = float(payload.get("cost", 0.0))
        price = float(payload.get("price", 0.0))

        if not product_name:
            return {"status": "failed", "summary": "Missing product_name"}

        # 1. Generate listing copy
        listing_result = await self.tools.execute(
            "generate_listing",
            product={
                "name": product_name,
                "niche": niche,
                "platform": platform,
                "keywords": niche,
                "audience": "general",
            },
        )

        # 2. Calculate profit
        profit_result = await self.tools.execute(
            "calculate_profit", cost=cost, price=price, platform=platform
        )

        # 3. Save product
        save_result = await self.tools.execute(
            "save_product_to_vault",
            product={
                "name": product_name,
                "niche": niche,
                "platform": platform,
                "cost": cost,
                "price": price,
                "status": "active",
                "listing_title": listing_result.get("title", product_name),
                "listing_description": listing_result.get("description", ""),
                "listing_tags": listing_result.get("tags", []),
                "profit_analysis": profit_result,
            },
        )

        product_id = save_result.get("product_id")

        # 4. Save listing record separately
        if product_id:
            vault.insert(
                "listings",
                {
                    "product_id": product_id,
                    "platform": platform,
                    "title": listing_result.get("title", product_name),
                    "description": listing_result.get("description", ""),
                    "tags": listing_result.get("tags", []),
                    "status": "live",
                },
            )

        return {
            "status": "executed",
            "summary": (
                f"Created '{product_name}' on {platform}. "
                f"Profit: {profit_result.get('recommendation', 'unknown')}. "
                f"Product ID: {product_id}"
            ),
            "product_id": product_id,
        }

    async def _execute_adjust_price(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update product price and record the change."""
        product_id = payload.get("product_id", "")
        new_price = float(payload.get("new_price", 0.0))

        if not product_id or new_price <= 0:
            return {
                "status": "failed",
                "summary": "Missing product_id or invalid new_price",
            }

        result = await self.tools.execute(
            "update_product_price", product_id=product_id, new_price=new_price
        )

        if result.get("status") == "updated":
            old_price = result.get("old_price", 0.0)
            projected_delta = (new_price - old_price) * 0.5  # heuristic
            return {
                "status": "executed",
                "summary": (
                    f"Updated price for {product_id}: ${old_price} → ${new_price}"
                ),
                "projected_delta": projected_delta,
            }
        return {
            "status": "failed",
            "summary": result.get("error", "Price update failed"),
        }

    async def _execute_pause_product(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Pause an underperforming product."""
        product_id = payload.get("product_id", "")
        if not product_id:
            return {"status": "failed", "summary": "Missing product_id"}

        success = vault.update("products", product_id, {"status": "paused"})
        # Also update any live listings
        listings = vault.find("listings", limit=200)
        for lst in listings:
            if lst.get("product_id") == product_id:
                vault.update("listings", lst.get("_id", ""), {"status": "paused"})

        return {
            "status": "executed" if success else "failed",
            "summary": f"Paused product {product_id} and associated listings.",
        }

    async def _execute_source_product(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Research and save a new product idea to the vault."""
        product_name = payload.get("product_name", "")
        niche = payload.get("niche", "")
        platform = payload.get("platform", self.DEFAULT_PLATFORM)
        cost = float(payload.get("cost", 0.0))
        price = float(payload.get("price", 0.0))

        if not product_name:
            return {"status": "failed", "summary": "Missing product_name"}

        profit_result = await self.tools.execute(
            "calculate_profit", cost=cost, price=price, platform=platform
        )

        save_result = await self.tools.execute(
            "save_product_to_vault",
            product={
                "name": product_name,
                "niche": niche,
                "platform": platform,
                "cost": cost,
                "price": price,
                "status": "idea",
                "profit_analysis": profit_result,
                "source": "agent_research",
            },
        )

        product_id = save_result.get("product_id")
        return {
            "status": "executed",
            "summary": (
                f"Sourced '{product_name}' ({platform}) as idea. "
                f"Profit outlook: {profit_result.get('recommendation', 'unknown')}. "
                f"Product ID: {product_id}"
            ),
            "product_id": product_id,
        }

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Best-effort JSON extraction from an LLM response."""
        try:
            return json.loads(text)
        except Exception:
            pass
        import re

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return None
