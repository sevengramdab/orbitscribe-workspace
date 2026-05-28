"""
DropshippingAgent — Autonomous e-commerce arbitrage agent.

Operates across Etsy, Shopify, Amazon, and eBay mental models.
While current tooling is optimized for Etsy, the architecture is designed
to scale to additional platforms as integrations mature.

Business cycle:
  1. perceive()  → Gather vault state, competitor intel, and trending data.
  2. decide()    → LLM-driven decision with confidence / risk / revenue scoring.
  3. execute()   → Perform the action via registered business tools.

Live-readiness:
  - In SIMULATION mode: uses realistic product costs and shipping estimates.
  - In LIVE mode: checks mode_guard.is_live before calling real supplier APIs
    (Spocket, AliExpress, or Oberlo when configured).
  - actual_revenue reflects real net margins after fees.
"""

import asyncio
import json
import os
import random
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from core.business_tools.registry import BusinessToolRegistry
from core.business_tools.vault import vault
from core.llm_client import LLMClient
from core.mode_guard import mode_guard, ModeGuardError

from .base import BaseBusinessAgent, BusinessDecision

# Trigger registration of dropshipping tools on module import
import core.business_tools.dropshipping_tools  # noqa: F401


# ── Realistic simulation ranges by niche ──────────────────────────────────────
_SIM_COST_RANGES: Dict[str, tuple] = {
    "electronics": (5.0, 25.0),
    "accessories": (3.0, 15.0),
    "home decor": (4.0, 20.0),
    "digital planners": (1.0, 5.0),
    "personalized gifts": (4.0, 18.0),
    "kitchen": (5.0, 22.0),
    "beauty": (3.0, 14.0),
    "toys": (4.0, 16.0),
    "sports": (6.0, 28.0),
    "pet supplies": (4.0, 18.0),
}

_SIM_SHIPPING_RANGES: Dict[str, tuple] = {
    "electronics": (2.5, 6.0),
    "accessories": (1.5, 4.0),
    "home decor": (3.0, 8.0),
    "digital planners": (0.0, 1.0),
    "personalized gifts": (2.0, 5.5),
    "kitchen": (3.5, 8.5),
    "beauty": (1.5, 4.5),
    "toys": (2.5, 6.5),
    "sports": (3.0, 7.5),
    "pet supplies": (2.0, 5.0),
}

_DEFAULT_COST_RANGE = (5.0, 20.0)
_DEFAULT_SHIPPING_RANGE = (2.0, 5.0)


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
        llm_client: LLMClient = None,
        model_router=None,
        autonomy_tier: str = "AUTOPILOT",
        decision_callback=None,
    ):
        client = llm_client or model_router
        super().__init__(
            name="DropshippingAgent",
            description=(
                "Autonomous e-commerce arbitrage agent for Etsy, Shopify, "
                "Amazon, and eBay"
            ),
            llm_client=client,
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
            - mode: current SIMULATION / LIVE mode
        """
        perception: Dict[str, Any] = {
            "agent": self.name,
            "platform_focus": self.DEFAULT_PLATFORM,
            "mode": mode_guard.mode.value,
            "is_live": mode_guard.is_live,
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
            raw = await self.llm_client.chat(
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
        actual_revenue is set to the real net margin (profit per unit),
        not gross revenue, so the ledger tracks true earnings.
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
                actual_revenue = result.get("net_profit_per_unit", 0.0)

            elif decision.decision_type == "adjust_price":
                result = await self._execute_adjust_price(payload)
                result_summary = result.get("summary", "")
                status = result.get("status", "failed")
                actual_revenue = result.get("projected_delta", 0.0)

            elif decision.decision_type == "pause_product":
                result = await self._execute_pause_product(payload)
                result_summary = result.get("summary", "")
                status = result.get("status", "failed")
                actual_revenue = result.get("saved_loss", 0.0)

            elif decision.decision_type == "source_product":
                result = await self._execute_source_product(payload)
                result_summary = result.get("summary", "")
                status = result.get("status", "failed")
                actual_revenue = 0.0  # research has no immediate revenue

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

    # ── Supplier integration (LIVE vs SIMULATION) ─────────────────────────────

    async def _fetch_supplier_cost(self, product_name: str, niche: str = "") -> Dict[str, Any]:
        """
        Fetch real supplier cost + shipping or fall back to simulation.

        In LIVE mode with supplier API keys configured, attempts calls to
        Spocket, AliExpress, or Oberlo in that order.
        In SIMULATION mode (or if LIVE keys are missing), returns realistic
        synthetic cost data.
        """
        if not mode_guard.is_live:
            return self._simulate_supplier_data(product_name, niche)

        # Live mode — try configured supplier APIs
        for supplier, api_key in [
            ("spocket", os.getenv("SPOCKET_API_KEY")),
            ("aliexpress", os.getenv("ALIEXPRESS_API_KEY")),
            ("oberlo", os.getenv("OBERLO_API_KEY")),
        ]:
            if api_key:
                try:
                    if supplier == "spocket":
                        return await self._fetch_spocket_cost(product_name, api_key)
                    elif supplier == "aliexpress":
                        return await self._fetch_aliexpress_cost(product_name, api_key)
                    elif supplier == "oberlo":
                        return await self._fetch_oberlo_cost(product_name, api_key)
                except Exception as exc:
                    print(f"[{self.name}] {supplier} API error: {exc}")
                    continue

        # No supplier APIs configured — fall back to simulation
        return self._simulate_supplier_data(product_name, niche)

    def _simulate_supplier_data(self, product_name: str, niche: str = "") -> Dict[str, Any]:
        """Return realistic synthetic cost and shipping for SIMULATION mode."""
        niche_key = niche.lower().strip() if niche else ""
        cost_min, cost_max = _SIM_COST_RANGES.get(niche_key, _DEFAULT_COST_RANGE)
        ship_min, ship_max = _SIM_SHIPPING_RANGES.get(niche_key, _DEFAULT_SHIPPING_RANGE)

        base_cost = round(random.uniform(cost_min, cost_max), 2)
        shipping = round(random.uniform(ship_min, ship_max), 2)
        return {
            "base_cost": base_cost,
            "shipping_cost": shipping,
            "total_cost": round(base_cost + shipping, 2),
            "supplier": "simulated",
            "currency": "USD",
            "lead_time_days": random.randint(7, 21),
            "mode": "SIMULATION",
        }

    async def _fetch_spocket_cost(self, product_name: str, api_key: str) -> Dict[str, Any]:
        """Call Spocket search API for product cost data."""
        query = urllib.parse.quote_plus(product_name)
        url = f"https://api.spocket.co/v1/products?search={query}&limit=1"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "OrbitScribe-DropshippingAgent/1.0",
            },
        )
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, urllib.request.urlopen, req)
        data = json.loads(resp.read().decode("utf-8"))
        items = data.get("products", data.get("data", []))
        if not items:
            raise ValueError("No Spocket products found")
        item = items[0]
        cost = float(item.get("price", 0) or item.get("cost", 0))
        shipping = float(item.get("shipping_cost", 0) or 0)
        return {
            "base_cost": round(cost, 2),
            "shipping_cost": round(shipping, 2),
            "total_cost": round(cost + shipping, 2),
            "supplier": "spocket",
            "currency": item.get("currency", "USD"),
            "lead_time_days": item.get("processing_time", 14),
            "mode": "LIVE",
        }

    async def _fetch_aliexpress_cost(self, product_name: str, api_key: str) -> Dict[str, Any]:
        """Call AliExpress Dropshipping API for product cost data."""
        query = urllib.parse.quote_plus(product_name)
        url = f"https://api.alibaba.com/v1/products?keywords={query}&limit=1"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "OrbitScribe-DropshippingAgent/1.0",
            },
        )
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, urllib.request.urlopen, req)
        data = json.loads(resp.read().decode("utf-8"))
        items = data.get("products", data.get("data", []))
        if not items:
            raise ValueError("No AliExpress products found")
        item = items[0]
        cost = float(item.get("price", 0) or item.get("sale_price", 0))
        shipping = float(item.get("shipping_cost", 0) or 0)
        return {
            "base_cost": round(cost, 2),
            "shipping_cost": round(shipping, 2),
            "total_cost": round(cost + shipping, 2),
            "supplier": "aliexpress",
            "currency": item.get("currency", "USD"),
            "lead_time_days": item.get("delivery_time", 14),
            "mode": "LIVE",
        }

    async def _fetch_oberlo_cost(self, product_name: str, api_key: str) -> Dict[str, Any]:
        """Call Oberlo API for product cost data (legacy / Shopify-based)."""
        query = urllib.parse.quote_plus(product_name)
        url = f"https://api.oberlo.com/v1/products?search={query}&limit=1"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "OrbitScribe-DropshippingAgent/1.0",
            },
        )
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, urllib.request.urlopen, req)
        data = json.loads(resp.read().decode("utf-8"))
        items = data.get("products", data.get("data", []))
        if not items:
            raise ValueError("No Oberlo products found")
        item = items[0]
        cost = float(item.get("price", 0) or item.get("cost", 0))
        shipping = float(item.get("shipping_cost", 0) or 0)
        return {
            "base_cost": round(cost, 2),
            "shipping_cost": round(shipping, 2),
            "total_cost": round(cost + shipping, 2),
            "supplier": "oberlo",
            "currency": item.get("currency", "USD"),
            "lead_time_days": item.get("processing_time", 14),
            "mode": "LIVE",
        }

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
            text = await self.llm_client.chat(
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
        mode = perception.get("mode", "SIMULATION")

        return f"""You are the Dropshipping Strategy Engine.

Current State:
- Active products in vault: {product_count}
- Underperforming products: {underperformer_count}
- Platform focus: {perception.get('platform_focus', 'etsy')}
- Mode: {mode}

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
    // For create_listing:  {{ "product_name": "...", "niche": "...", "price": float, "platform": "..." }}
    // For adjust_price:    {{ "product_id": "...", "new_price": float }}
    // For pause_product:   {{ "product_id": "..." }}
    // For source_product:  {{ "product_name": "...", "niche": "...", "price": float, "platform": "..." }}
    // For noop: {{}}
  }}
}}

Rules:
- If underperformer_count > 3, strongly consider pause_product.
- If product_count < 5, strongly consider source_product or create_listing.
- Confidence > 0.8 and risk_score < 0.4 for high-conviction moves.
- In SIMULATION mode, cost will be auto-estimated; in LIVE mode, real supplier APIs will be used.
"""

    async def _execute_create_listing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate listing content, fetch supplier cost, and save product + listing."""
        product_name = payload.get("product_name", "")
        niche = payload.get("niche", "")
        platform = payload.get("platform", self.DEFAULT_PLATFORM)
        price = float(payload.get("price", 0.0))

        if not product_name:
            return {"status": "failed", "summary": "Missing product_name"}

        # 1. Fetch real or simulated supplier cost
        supplier_data = await self._fetch_supplier_cost(product_name, niche)
        cost = supplier_data["total_cost"]

        # 2. Generate listing copy
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

        # 3. Calculate profit using real cost
        profit_result = await self.tools.execute(
            "calculate_profit", cost=cost, price=price, platform=platform
        )

        # 4. Save product with full supplier metadata
        save_result = await self.tools.execute(
            "save_product_to_vault",
            product={
                "name": product_name,
                "niche": niche,
                "platform": platform,
                "cost": cost,
                "base_cost": supplier_data.get("base_cost", cost),
                "shipping_cost": supplier_data.get("shipping_cost", 0.0),
                "price": price,
                "status": "active",
                "listing_title": listing_result.get("title", product_name),
                "listing_description": listing_result.get("description", ""),
                "listing_tags": listing_result.get("tags", []),
                "profit_analysis": profit_result,
                "supplier": supplier_data.get("supplier", "unknown"),
                "lead_time_days": supplier_data.get("lead_time_days", 14),
                "mode": supplier_data.get("mode", "SIMULATION"),
            },
        )

        product_id = save_result.get("product_id")

        # 5. Save listing record separately
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

        net_profit = profit_result.get("net_profit", 0.0)
        return {
            "status": "executed",
            "summary": (
                f"Created '{product_name}' on {platform}. "
                f"Supplier: {supplier_data.get('supplier', 'unknown')} "
                f"(${supplier_data.get('base_cost', cost)} + ${supplier_data.get('shipping_cost', 0)} shipping). "
                f"Net profit/unit: ${net_profit}. "
                f"Product ID: {product_id}"
            ),
            "product_id": product_id,
            "net_profit_per_unit": net_profit,
        }

    async def _execute_adjust_price(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update product price and record the change with margin-based delta."""
        product_id = payload.get("product_id", "")
        new_price = float(payload.get("new_price", 0.0))

        if not product_id or new_price <= 0:
            return {
                "status": "failed",
                "summary": "Missing product_id or invalid new_price",
            }

        # Retrieve existing product to get cost for margin recalculation
        product = vault.get("products", product_id)
        if not product:
            return {
                "status": "failed",
                "summary": f"Product {product_id} not found",
            }

        cost = product.get("cost", 0.0)
        old_price = product.get("price", 0.0)
        platform = product.get("platform", self.DEFAULT_PLATFORM)

        result = await self.tools.execute(
            "update_product_price", product_id=product_id, new_price=new_price
        )

        if result.get("status") == "updated":
            # Recalculate profit at new price for accurate revenue impact
            new_profit_result = await self.tools.execute(
                "calculate_profit", cost=cost, price=new_price, platform=platform
            )
            old_profit_result = await self.tools.execute(
                "calculate_profit", cost=cost, price=old_price, platform=platform
            )

            new_net_profit = new_profit_result.get("net_profit", 0.0)
            old_net_profit = old_profit_result.get("net_profit", 0.0)
            # Assume 10 unit/month volume for projected delta
            projected_delta = (new_net_profit - old_net_profit) * 10

            return {
                "status": "executed",
                "summary": (
                    f"Updated price for {product_id}: ${old_price} → ${new_price}. "
                    f"Net profit/unit: ${old_net_profit} → ${new_net_profit}."
                ),
                "projected_delta": round(projected_delta, 2),
                "old_net_profit": old_net_profit,
                "new_net_profit": new_net_profit,
            }
        return {
            "status": "failed",
            "summary": result.get("error", "Price update failed"),
        }

    async def _execute_pause_product(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Pause an underperforming product and estimate saved losses."""
        product_id = payload.get("product_id", "")
        if not product_id:
            return {"status": "failed", "summary": "Missing product_id"}

        product = vault.get("products", product_id)
        saved_loss = 0.0
        if product:
            cost = product.get("cost", 0.0)
            price = product.get("price", 0.0)
            # Rough estimate: if margin is negative, pausing saves that loss
            profit_result = await self.tools.execute(
                "calculate_profit", cost=cost, price=price, platform=product.get("platform", "etsy")
            )
            net_profit = profit_result.get("net_profit", 0.0)
            if net_profit < 0:
                saved_loss = abs(net_profit) * 10  # 10 units/month avoided loss

        success = vault.update("products", product_id, {"status": "paused"})
        # Also update any live listings
        listings = vault.find("listings", limit=200)
        for lst in listings:
            if lst.get("product_id") == product_id:
                vault.update("listings", lst.get("_id", ""), {"status": "paused"})

        return {
            "status": "executed" if success else "failed",
            "summary": f"Paused product {product_id} and associated listings.",
            "saved_loss": round(saved_loss, 2),
        }

    async def _execute_source_product(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Research and save a new product idea to the vault with supplier cost."""
        product_name = payload.get("product_name", "")
        niche = payload.get("niche", "")
        platform = payload.get("platform", self.DEFAULT_PLATFORM)
        price = float(payload.get("price", 0.0))

        if not product_name:
            return {"status": "failed", "summary": "Missing product_name"}

        # Fetch supplier cost (real or simulated)
        supplier_data = await self._fetch_supplier_cost(product_name, niche)
        cost = supplier_data["total_cost"]

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
                "base_cost": supplier_data.get("base_cost", cost),
                "shipping_cost": supplier_data.get("shipping_cost", 0.0),
                "price": price,
                "status": "idea",
                "profit_analysis": profit_result,
                "source": "agent_research",
                "supplier": supplier_data.get("supplier", "unknown"),
                "lead_time_days": supplier_data.get("lead_time_days", 14),
                "mode": supplier_data.get("mode", "SIMULATION"),
            },
        )

        product_id = save_result.get("product_id")
        return {
            "status": "executed",
            "summary": (
                f"Sourced '{product_name}' ({platform}) as idea. "
                f"Supplier: {supplier_data.get('supplier', 'unknown')} "
                f"(${supplier_data.get('base_cost', cost)} + ${supplier_data.get('shipping_cost', 0)} shipping). "
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
