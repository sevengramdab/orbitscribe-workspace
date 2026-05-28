"""
PrintOnDemandAgent — Autonomous print-on-demand business agent.

Operates the full POD lifecycle:
  1. Perceive market signals, vault state, and bestseller data
  2. Decide whether to design, publish, price, promote, or retire
  3. Execute via business tools and LLM-driven concept generation

Vault collections used:
  - pod_designs  : Concepts, briefs, mockup descriptions, profit tracking
  - pod_products : Simulated/real Printify product records
  - pod_orders   : Order snapshots for revenue reconciliation
  - pod_niches   : Researched niche metadata and trend signals
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.business_tools.vault import vault
from core.mode_guard import mode_guard, ModeGuardError
from core import config

from .base import BaseBusinessAgent, BusinessDecision

# Thresholds tuned for autonomous operation
_DESIGN_AGE_STALE_DAYS = 60
_MAX_ACTIVE_DESIGNS = 50
_TARGET_MARGIN_PERCENT = 35.0

# ── Realistic Printify base costs (Bella+Canvas 3001, standard mugs, etc.) ──
# Sources: Printify catalog 2024-2025, Print Provider pricing
_REALISTIC_COSTS = {
    "t-shirt":    {"base_cost": 8.86, "shipping": 4.00, "selling_price": 24.99},
    "mug":        {"base_cost": 4.80, "shipping": 4.50, "selling_price": 19.99},
    "poster":     {"base_cost": 5.50, "shipping": 5.00, "selling_price": 22.99},
    "sticker":    {"base_cost": 1.25, "shipping": 1.00, "selling_price": 5.99},
    "tote-bag":   {"base_cost": 7.50, "shipping": 4.00, "selling_price": 21.99},
    "phone-case": {"base_cost": 5.50, "shipping": 3.50, "selling_price": 19.99},
}

# Etsy fee model (2025):
#   6.5% transaction fee + 3% payment processing + $0.25 fixed + $0.20 listing
# Effective ~12.5% on $20-30 AOV; we keep it conservative.
_ETSY_PLATFORM_FEES_PERCENT = 12.5

# Design output directory (project-relative)
_DESIGNS_DIR = Path(config.WORKSPACE_ROOT) / "products" / "pod" / "designs"


class PrintOnDemandAgent(BaseBusinessAgent):
    """
    Autonomous Print-on-Demand agent.

    Generates design concepts, simulates or live-publishes via Printify,
    tracks per-design profit, and manages the design portfolio lifecycle.
    """

    def __init__(
        self,
        llm_client=None,
        model_router=None,
        autonomy_tier: str = "AUTOPILOT",
        decision_callback=None,
    ):
        client = llm_client or model_router
        super().__init__(
            name="print_on_demand",
            description="Autonomous POD agent: design → publish → profit → retire",
            llm_client=client,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )
        # Ensure design storage exists
        _DESIGNS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Perception ──────────────────────────────────────────────────────────

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather market data, vault state, and portfolio health metrics.

        Returns:
            Dict of observations used by decide().
        """
        now = datetime.utcnow()

        # Raw vault snapshots
        designs = vault.find("pod_designs", limit=500)
        products = vault.find("pod_products", limit=500)
        orders = vault.find("pod_orders", limit=500)
        niches = vault.find("pod_niches", limit=100)

        # Portfolio composition
        active_designs = [d for d in designs if d.get("status") not in ("retired", "archived")]
        published_designs = [d for d in designs if d.get("status") == "published"]
        retired_designs = [d for d in designs if d.get("status") == "retired"]
        concept_designs = [d for d in designs if d.get("status") == "concept"]

        # Stale detection
        stale_designs: List[Dict[str, Any]] = []
        for d in active_designs:
            updated = d.get("_updated_at") or d.get("created_at") or ""
            try:
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if (now - dt).days > _DESIGN_AGE_STALE_DAYS:
                    stale_designs.append(d)
            except Exception:
                pass

        # Profit tracking per design
        design_profits: Dict[str, float] = {}
        for d in designs:
            did = d.get("_id", "")
            if not did:
                continue
            pt = d.get("profit_tracking", {})
            profit_per_unit = pt.get("net_profit_per_unit", 0.0)
            sales = d.get("simulated_sales", 0) or len(
                [o for o in orders if o.get("design_id") == did]
            )
            design_profits[did] = round(profit_per_unit * sales, 2)

        total_profit = sum(design_profits.values())
        avg_margin = (
            sum(d.get("profit_tracking", {}).get("margin_percent", 0) for d in active_designs)
            / max(len(active_designs), 1)
        )

        # Bestsellers (via tool)
        bestseller_result = await self.tools.execute("get_pod_best_sellers", limit=5)
        bestsellers = bestseller_result.get("data", {}).get("designs", []) if bestseller_result.get("status") == "ok" else []

        # Promotion candidates (published but no recent promo)
        promo_candidates = [
            d for d in published_designs
            if not d.get("last_promotion_at")
        ]

        # Capacity signal
        at_capacity = len(active_designs) >= _MAX_ACTIVE_DESIGNS

        perception = {
            "timestamp": now.isoformat(),
            "portfolio": {
                "total_designs": len(designs),
                "active": len(active_designs),
                "published": len(published_designs),
                "retired": len(retired_designs),
                "concepts": len(concept_designs),
                "products": len(products),
                "orders": len(orders),
                "niches_researched": len(niches),
            },
            "health": {
                "total_profit": total_profit,
                "avg_margin_percent": round(avg_margin, 2),
                "stale_designs_count": len(stale_designs),
                "at_capacity": at_capacity,
            },
            "signals": {
                "stale_design_ids": [d.get("_id") for d in stale_designs],
                "promo_candidate_ids": [d.get("_id") for d in promo_candidates],
                "bestseller_ids": [d.get("_id") for d in bestsellers],
                "recent_niches": [n.get("niche") for n in niches[-5:]],
            },
            "simulate_mode": mode_guard.is_simulation,
            "is_live": mode_guard.is_live,
            "live_ready_printify": mode_guard.get_status()["live_ready"].get("printify", False),
        }

        return perception

    # ── Decision ────────────────────────────────────────────────────────────

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Use LLM reasoning to choose the next POD action.

        Returns:
            BusinessDecision or None if no action is warranted.
        """
        portfolio = perception.get("portfolio", {})
        health = perception.get("health", {})
        signals = perception.get("signals", {})

        system_prompt = (
            "You are the strategic brain of an autonomous Print-on-Demand business. "
            "Given portfolio metrics and market signals, choose ONE next action. "
            "Respond ONLY with valid JSON. No markdown, no prose."
        )

        user_prompt = f"""POD Portfolio State:
- Total designs: {portfolio.get('total_designs', 0)}
- Active designs: {portfolio.get('active', 0)}
- Published: {portfolio.get('published', 0)}
- Concepts waiting: {portfolio.get('concepts', 0)}
- Stale designs (>60d): {health.get('stale_designs_count', 0)}
- Avg margin: {health.get('avg_margin_percent', 0)}%
- Total profit tracked: ${health.get('total_profit', 0):.2f}
- At capacity: {health.get('at_capacity', False)}
- Recent niches: {signals.get('recent_niches', [])}
- Promo candidates: {len(signals.get('promo_candidate_ids', []))}
- Mode: {'LIVE' if perception.get('is_live') else 'SIMULATION'}

Choose the single best action from:
  create_new_design, publish_to_printify, adjust_pricing, run_promotion, retire_stale_design, no_op

Respond in this exact JSON shape:
{{
  "decision_type": "create_new_design|publish_to_printify|adjust_pricing|run_promotion|retire_stale_design|no_op",
  "rationale": "why this action now",
  "confidence": 0.0-1.0,
  "risk_score": 0.0-1.0,
  "estimated_revenue_impact": 0.0,
  "action_payload": {{}}
}}
"""

        try:
            llm_response = await self.llm_decide(system_prompt, user_prompt)
        except Exception as exc:
            # Graceful degradation: if LLM fails, do nothing this cycle
            return BusinessDecision(
                agent_name=self.name,
                decision_type="no_op",
                rationale=f"LLM decision failed: {exc}",
                confidence=0.0,
                risk_score=0.0,
                status="executed",
                result_summary="No action taken due to LLM error",
            )

        decision_type = llm_response.get("decision_type", "no_op")
        if decision_type == "no_op":
            return None

        decision = BusinessDecision(
            agent_name=self.name,
            decision_type=decision_type,
            rationale=llm_response.get("rationale", ""),
            confidence=float(llm_response.get("confidence", 0.5)),
            risk_score=float(llm_response.get("risk_score", 0.5)),
            estimated_revenue_impact=float(llm_response.get("estimated_revenue_impact", 0.0)),
            action_payload=llm_response.get("action_payload", {}),
        )
        return decision

    # ── Execution ───────────────────────────────────────────────────────────

    async def execute(self, decision: BusinessDecision):
        """
        Execute the approved decision using POD business tools.

        Updates the decision object with results and logs it.
        """
        decision_type = decision.decision_type
        payload = decision.action_payload or {}
        result_summary = ""
        actual_revenue = 0.0

        try:
            if decision_type == "create_new_design":
                result = await self._execute_create_design(payload)
                result_summary = result.get("summary", "Design created")
                actual_revenue = result.get("estimated_profit", 0.0)

            elif decision_type == "publish_to_printify":
                result = await self._execute_publish(payload)
                result_summary = result.get("summary", "Published to channels")
                actual_revenue = result.get("actual_profit", result.get("estimated_profit", 0.0))

            elif decision_type == "adjust_pricing":
                result = await self._execute_adjust_pricing(payload)
                result_summary = result.get("summary", "Pricing adjusted")
                actual_revenue = result.get("profit_delta", 0.0)

            elif decision_type == "run_promotion":
                result = await self._execute_promotion(payload)
                result_summary = result.get("summary", "Promotion launched")
                actual_revenue = result.get("actual_uplift", result.get("estimated_uplift", 0.0))

            elif decision_type == "retire_stale_design":
                result = await self._execute_retire(payload)
                result_summary = result.get("summary", "Stale designs retired")
                actual_revenue = result.get("cost_savings", 0.0)

            else:
                result_summary = f"Unknown decision type: {decision_type}"
                decision.status = "failed"

        except Exception as exc:
            decision.status = "failed"
            result_summary = f"Execution error: {exc}"
            actual_revenue = 0.0

        if decision.status != "failed":
            decision.status = "executed"

        decision.result_summary = result_summary
        decision.actual_revenue = actual_revenue
        self.log_decision(decision)
        self._save_vault()

    # ── Action implementations ──────────────────────────────────────────────

    async def _execute_create_design(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a design brief, save it to disk, and persist to the vault."""
        niche = payload.get("niche") or self._pick_niche()
        style = payload.get("style", "minimalist")

        # Ensure niche is researched
        niche_result = await self.tools.execute("research_pod_niche", niche=niche)
        if niche_result.get("status") != "ok":
            # Fallback: insert a minimal niche doc so we can continue
            vault.insert("pod_niches", {"niche": niche, "researched_at": datetime.utcnow().isoformat()})

        brief_result = await self.tools.execute("generate_design_brief", niche=niche, style=style)
        if brief_result.get("status") != "ok":
            return {"summary": f"Design brief generation failed for {niche}", "estimated_profit": 0.0}

        design_id = brief_result["data"]["design_id"]
        brief = brief_result["data"]["brief"]

        # Calculate profit estimate for the primary suggested product using REALISTIC costs
        suggested = brief.get("suggested_products", ["t-shirt"])
        primary = suggested[0] if suggested else "t-shirt"
        economics = _REALISTIC_COSTS.get(primary, _REALISTIC_COSTS["t-shirt"])
        base_cost = economics["base_cost"]
        shipping = economics["shipping"]
        selling_price = economics["selling_price"]
        platform_fees = _ETSY_PLATFORM_FEES_PERCENT

        profit_result = await self.tools.execute(
            "calculate_pod_profit",
            base_cost=base_cost,
            shipping=shipping,
            selling_price=selling_price,
            platform_fees_percent=platform_fees,
        )
        profit_data = profit_result.get("data", {}) if profit_result.get("status") == "ok" else {}

        # Enrich vault doc with profit tracking
        vault.update("pod_designs", design_id, {
            "profit_tracking": {
                "primary_product": primary,
                "base_cost": base_cost,
                "shipping": shipping,
                "selling_price": selling_price,
                "platform_fees_percent": platform_fees,
                "net_profit_per_unit": profit_data.get("net_profit", 0.0),
                "margin_percent": profit_data.get("margin_percent", 0.0),
                "total_units_sold": 0,
                "total_profit": 0.0,
            },
            "status": "concept",
        })

        # Save design brief to disk in proper directory structure
        self._save_design_to_disk(design_id, brief, niche, style)

        return {
            "summary": f"Created design '{brief.get('title')}' for niche '{niche}' (id={design_id})",
            "design_id": design_id,
            "estimated_profit": profit_data.get("net_profit", 0.0),
        }

    async def _execute_publish(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Printify product and publish to sales channels."""
        design_id = payload.get("design_id")
        if not design_id:
            # Auto-select the highest-margin concept
            concepts = vault.find("pod_designs", lambda d: d.get("status") == "concept", limit=10)
            if not concepts:
                return {"summary": "No concept designs available to publish", "estimated_profit": 0.0}
            concepts.sort(
                key=lambda d: d.get("profit_tracking", {}).get("margin_percent", 0),
                reverse=True,
            )
            design_id = concepts[0]["_id"]

        design = vault.get("pod_designs", design_id)
        if not design:
            return {"summary": f"Design {design_id} not found", "estimated_profit": 0.0}

        brief = design.get("brief", {})
        title = brief.get("title", "Untitled Design")
        description = brief.get("concept", "") + "\n\n" + brief.get("visual_description", "")
        blueprint_id = payload.get("blueprint_id", "5")  # Default unisex tee
        print_provider_id = payload.get("print_provider_id", "1")
        variants = payload.get("variants", [
            {"id": 1, "size": "S", "color": "Black", "price": 2999},
            {"id": 2, "size": "M", "color": "Black", "price": 2999},
            {"id": 3, "size": "L", "color": "Black", "price": 2999},
        ])

        profit = design.get("profit_tracking", {}).get("net_profit_per_unit", 0.0)

        # ── LIVE mode guard ────────────────────────────────────────────────
        if mode_guard.is_live:
            # Gate check: will raise ModeGuardError if credentials missing
            try:
                mode_guard.check_gate("printify", action="create_product")
            except ModeGuardError as exc:
                return {
                    "summary": f"LIVE publish blocked: {exc}",
                    "actual_profit": 0.0,
                }

            create_result = await self.tools.execute(
                "create_pod_product",
                design_id=design_id,
                blueprint_id=blueprint_id,
                print_provider_id=print_provider_id,
                title=title,
                description=description,
                variants=variants,
            )
            if create_result.get("status") != "ok":
                return {
                    "summary": f"Product creation failed: {create_result.get('error')}",
                    "actual_profit": 0.0,
                }

            product_id = create_result["data"]["product_id"]
            publish_result = await self.tools.execute("publish_pod_product", product_id=product_id)
            if publish_result.get("status") != "ok":
                return {
                    "summary": f"Created product but publish failed: {publish_result.get('error')}",
                    "actual_profit": 0.0,
                }

            return {
                "summary": f"[LIVE] Published '{title}' to sales channels (product={product_id})",
                "product_id": product_id,
                "actual_profit": profit,
            }

        # ── SIMULATION mode ────────────────────────────────────────────────
        # Simulate product creation without hitting real APIs
        product_id = vault.insert(
            "pod_products",
            {
                "design_id": design_id,
                "title": title,
                "description": description,
                "blueprint_id": blueprint_id,
                "print_provider_id": print_provider_id,
                "variants": variants,
                "status": "published",
                "simulate_mode": True,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        vault.update("pod_designs", design_id, {"product_id": product_id, "status": "published"})

        return {
            "summary": f"[SIM] Published '{title}' to sales channels (product={product_id})",
            "product_id": product_id,
            "estimated_profit": profit,
        }

    async def _execute_adjust_pricing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust selling prices to hit target margin using realistic costs."""
        target_margin = float(payload.get("target_margin_percent", _TARGET_MARGIN_PERCENT))
        designs = vault.find("pod_products", limit=100)
        adjusted = 0
        profit_delta = 0.0

        for product in designs:
            if product.get("status") == "retired":
                continue
            design_id = product.get("design_id")
            if not design_id:
                continue
            design = vault.get("pod_designs", design_id)
            if not design:
                continue

            pt = design.get("profit_tracking", {})
            primary = pt.get("primary_product", "t-shirt")
            economics = _REALISTIC_COSTS.get(primary, _REALISTIC_COSTS["t-shirt"])
            base_cost = pt.get("base_cost", economics["base_cost"])
            shipping = pt.get("shipping", economics["shipping"])
            platform_fees = pt.get("platform_fees_percent", _ETSY_PLATFORM_FEES_PERCENT)

            # Solve for selling_price given target margin
            # net = price*(1 - platform/100) - base - shipping
            # margin = net / price
            # price = (base + shipping) / (1 - platform/100 - margin/100)
            denominator = 1.0 - (platform_fees / 100.0) - (target_margin / 100.0)
            if denominator <= 0:
                continue
            new_price = round((base_cost + shipping) / denominator, 2)

            old_price = pt.get("selling_price", economics["selling_price"])
            pt["selling_price"] = new_price
            pt["margin_percent"] = target_margin

            # Recalculate profit
            profit_result = await self.tools.execute(
                "calculate_pod_profit",
                base_cost=base_cost,
                shipping=shipping,
                selling_price=new_price,
                platform_fees_percent=platform_fees,
            )
            if profit_result.get("status") == "ok":
                pd = profit_result["data"]
                old_profit = pt.get("net_profit_per_unit", 0.0) or 0.0
                pt["net_profit_per_unit"] = pd.get("net_profit", 0.0)
                pt["margin_percent"] = pd.get("margin_percent", 0.0)
                profit_delta += (pd.get("net_profit", 0.0) - old_profit)

            vault.update("pod_designs", design_id, {"profit_tracking": pt, "pricing_adjusted_at": datetime.utcnow().isoformat()})
            adjusted += 1

        return {
            "summary": f"Adjusted pricing for {adjusted} designs to target {target_margin}% margin",
            "adjusted_count": adjusted,
            "profit_delta": round(profit_delta, 2),
        }

    async def _execute_promotion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run a promotion on published products. In LIVE mode, only log; in SIM, simulate uplift."""
        candidate_ids = payload.get("design_ids", [])
        if not candidate_ids:
            # Auto-pick published designs not recently promoted
            candidates = vault.find(
                "pod_designs",
                lambda d: d.get("status") == "published" and not d.get("last_promotion_at"),
                limit=5,
            )
            candidate_ids = [c["_id"] for c in candidates]

        promoted = 0
        actual_uplift = 0.0
        for did in candidate_ids:
            design = vault.get("pod_designs", did)
            if not design:
                continue
            pt = design.get("profit_tracking", {})
            profit_per_unit = pt.get("net_profit_per_unit", 0.0)

            if mode_guard.is_live:
                # In LIVE mode, do NOT simulate sales; just mark promotion
                uplift_units = 0
                uplift_profit = 0.0
            else:
                # Simulate a 20% sales uplift from a promotion
                uplift_units = 5
                uplift_profit = profit_per_unit * uplift_units
                pt["total_units_sold"] = pt.get("total_units_sold", 0) + uplift_units
                pt["total_profit"] = pt.get("total_profit", 0.0) + uplift_profit

                # Simulated order record
                vault.insert("pod_orders", {
                    "design_id": did,
                    "product_id": design.get("product_id"),
                    "quantity": uplift_units,
                    "profit": uplift_profit,
                    "order_type": "promotion_simulated",
                    "created_at": datetime.utcnow().isoformat(),
                })

            vault.update("pod_designs", did, {
                "profit_tracking": pt,
                "last_promotion_at": datetime.utcnow().isoformat(),
                "promotion_count": design.get("promotion_count", 0) + 1,
            })
            promoted += 1
            actual_uplift += uplift_profit

        return {
            "summary": f"Ran promotions on {promoted} designs ({'LIVE' if mode_guard.is_live else 'SIM'})",
            "promoted_count": promoted,
            "estimated_uplift": round(actual_uplift, 2) if not mode_guard.is_live else 0.0,
            "actual_uplift": round(actual_uplift, 2),
        }

    async def _execute_retire(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Retire stale or underperforming designs."""
        design_ids = payload.get("design_ids", [])
        if not design_ids:
            # Auto-select stale designs
            stale = vault.find("pod_designs", lambda d: d.get("status") not in ("retired", "archived"), limit=100)
            cutoff = datetime.utcnow() - timedelta(days=_DESIGN_AGE_STALE_DAYS)
            design_ids = []
            for d in stale:
                updated = d.get("_updated_at") or d.get("created_at") or ""
                try:
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if dt < cutoff:
                        design_ids.append(d["_id"])
                except Exception:
                    pass

        retired = 0
        cost_savings = 0.0
        for did in design_ids:
            result = await self.tools.execute("retire_pod_design", design_id=did)
            if result.get("status") == "ok":
                retired += 1
                # Opportunity cost savings: no longer maintaining old designs
                cost_savings += 2.0  # Nominal maintenance cost

        return {
            "summary": f"Retired {retired} stale designs",
            "retired_count": retired,
            "cost_savings": round(cost_savings, 2),
        }

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _pick_niche(self) -> str:
        """Pick a niche to research, favoring under-explored areas."""
        existing = vault.find("pod_niches", limit=200)
        existing_niches = {n.get("niche", "").lower() for n in existing}

        fallback_niches = [
            "coffee lover quotes",
            "vintage astronomy",
            "dog mom life",
            "minimalist botanical",
            "gamer aesthetic",
            "hiking adventure",
            "bookworm bibliophile",
            "yoga mindfulness",
            "retro synthwave",
            "cat dad energy",
        ]

        for n in fallback_niches:
            if n.lower() not in existing_niches:
                return n

        # All fallbacks exhausted; return a random one with a twist
        import random

        base = random.choice(fallback_niches)
        return f"{base} {random.randint(2025, 2030)}"

    def _save_design_to_disk(self, design_id: str, brief: Dict[str, Any], niche: str, style: str) -> None:
        """Persist the design brief to the products/pod/ directory tree."""
        design_dir = _DESIGNS_DIR / niche.replace(" ", "_").lower()
        design_dir.mkdir(parents=True, exist_ok=True)
        file_path = design_dir / f"{design_id}.json"
        doc = {
            "design_id": design_id,
            "niche": niche,
            "style": style,
            "brief": brief,
            "saved_at": datetime.utcnow().isoformat(),
        }
        try:
            file_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        except Exception:
            # Non-fatal: vault is the source of truth
            pass
