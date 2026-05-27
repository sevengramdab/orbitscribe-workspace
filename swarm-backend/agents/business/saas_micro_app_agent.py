"""
SaasMicroAppAgent

Autonomous business agent that spins up monetizable micro-SaaS applications,
manages their lifecycle, adds features, adjusts pricing, and sunsets
underperforming apps based on vault data and LLM-driven decisions.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.business_tools.vault import vault
from core.model_router import ModelRouter

from .base import BaseBusinessAgent, BusinessDecision

# Ensure SaaS tools are registered in the global tool registry
import core.business_tools.saas_tools  # noqa: F401


class SaasMicroAppAgent(BaseBusinessAgent):
    """
    Autonomous agent for the micro-SaaS vertical.

    Capabilities:
    - Research and validate micro-SaaS ideas.
    - Generate real, runnable app code (Flask or static HTML/JS).
    - Create Stripe payment links for monetization.
    - Package apps for deployment (Docker manifests).
    - Analyze performance and sunset failing apps.

    Vault collections used:
    - micro_apps: Active and sunset app records.
    - app_ideas: Researched ideas waiting to be built.
    - app_analytics: Usage and revenue metrics.
    - user_feedback: Feature requests and votes.
    """

    def __init__(
        self,
        model_router: ModelRouter,
        autonomy_tier: str = "AUTOPILOT",
        decision_callback=None,
    ):
        super().__init__(
            name="SaasMicroAppAgent",
            description=(
                "Spins up monetizable micro-SaaS apps, manages their lifecycle, "
                "and sunsets underperformers."
            ),
            model_router=model_router,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )
        self.vault = vault

    # ── Perception ──────────────────────────────────────────────────────────

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather market signals from the unified vault.

        Checks:
        - Existing micro-apps (active vs. sunset).
        - App ideas inventory.
        - User feedback volume and demand signals.
        - App analytics (revenue, users, churn).
        - Market gaps (app types not yet built).
        """
        apps = self.vault.find("micro_apps", limit=200)
        ideas = self.vault.find("app_ideas", limit=200)
        feedback = self.vault.find("user_feedback", limit=200)
        analytics = self.vault.find("app_analytics", limit=200)

        active_apps = [a for a in apps if a.get("status") == "active"]
        sunset_apps = [a for a in apps if a.get("status") == "sunset"]

        # Identify low performers (low revenue + low users + >30 days old)
        low_performers: List[Dict[str, Any]] = []
        for app in active_apps:
            app_id = app.get("_id") or app.get("app_id")
            app_analytics = [an for an in analytics if an.get("app_id") == app_id]
            total_revenue = sum(an.get("revenue", 0) for an in app_analytics)
            total_users = sum(an.get("users", 0) for an in app_analytics)

            created_at_str = app.get("created_at", datetime.utcnow().isoformat())
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except Exception:
                created_at = datetime.utcnow()

            age_days = (datetime.utcnow() - created_at).days
            if total_revenue < 10.0 and total_users < 5 and age_days > 30:
                low_performers.append(
                    {
                        "app_id": app_id,
                        "app_type": app.get("app_type"),
                        "age_days": age_days,
                        "total_revenue": total_revenue,
                        "total_users": total_users,
                    }
                )

        # High-demand feedback (votes > 5)
        high_demand_feedback = [
            f for f in feedback if f.get("votes", 0) > 5
        ]

        # Detect market gaps
        existing_types = {a.get("app_type") for a in apps}
        known_types = {
            "url_shortener",
            "qr_generator",
            "password_generator",
            "meme_maker",
            "json_formatter",
            "unit_converter",
            "todo_micro",
        }
        market_gaps = sorted(known_types - existing_types)

        return {
            "active_apps_count": len(active_apps),
            "sunset_apps_count": len(sunset_apps),
            "total_apps_count": len(apps),
            "ideas_count": len(ideas),
            "feedback_count": len(feedback),
            "low_performers": low_performers,
            "high_demand_feedback": high_demand_feedback,
            "market_gaps": market_gaps,
            "recent_apps": apps[:5],
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ── Decision ────────────────────────────────────────────────────────────

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Use LLM reasoning to choose the next best action.

        Decision types:
        - spin_up_app: Build a new micro-SaaS.
        - add_feature: Extend an existing app.
        - adjust_pricing: Modify price or billing model.
        - sunset_app: Deprecate a failing app.
        - noop: Do nothing this cycle.
        """
        system_prompt = """You are a SaaS product manager AI. Given market data, decide the next best action.

Available decision types:
- spin_up_app: Create a new micro-SaaS app
- add_feature: Add a feature to an existing app
- adjust_pricing: Change pricing for an existing app
- sunset_app: Mark a failing app as deprecated
- noop: Do nothing

Guidelines:
- If market_gaps exist and active_apps_count < 5, prefer spin_up_app.
- If low_performers exist, prefer sunset_app for the worst one.
- If high_demand_feedback exists for an existing app, prefer add_feature.
- Price new apps between $3 and $29.

Respond ONLY with valid JSON:
{
  "decision_type": "spin_up_app|add_feature|adjust_pricing|sunset_app|noop",
  "rationale": "...",
  "app_id": "existing app id or null",
  "app_type": "url_shortener|qr_generator|password_generator|meme_maker|json_formatter|unit_converter|todo_micro|custom",
  "features": ["feature1", "feature2"],
  "price": 9.99,
  "recurring": false,
  "confidence": 0.85,
  "risk_score": 0.2,
  "estimated_revenue_impact": 150.0
}
"""
        user_prompt = f"""Perception data:
{json.dumps(perception, indent=2, default=str)}
"""
        result = await self.llm_decide(system_prompt, user_prompt)

        decision_type = result.get("decision_type", "noop")
        if decision_type == "noop":
            return None

        # Validate decision_type to prevent injection or typos
        valid_types = {"spin_up_app", "add_feature", "adjust_pricing", "sunset_app"}
        if decision_type not in valid_types:
            return None

        decision = BusinessDecision(
            agent_name=self.name,
            decision_type=decision_type,
            rationale=str(result.get("rationale", "")),
            action_payload={
                "app_id": result.get("app_id"),
                "app_type": result.get("app_type") or "custom",
                "features": result.get("features", []),
                "price": float(result.get("price", 9.99)),
                "recurring": bool(result.get("recurring", False)),
            },
            estimated_revenue_impact=float(result.get("estimated_revenue_impact", 0.0)),
            risk_score=float(result.get("risk_score", 0.5)),
            confidence=float(result.get("confidence", 0.5)),
        )
        return decision

    # ── Execution ───────────────────────────────────────────────────────────

    async def execute(self, decision: BusinessDecision):
        """
        Execute the approved decision using registered business tools.

        Routes to:
        - spin_up_app: research → generate code → stripe link → package → vault.
        - add_feature: regenerate code with extended features → vault update.
        - adjust_pricing: new stripe link → vault update.
        - sunset_app: mark deprecated in vault.
        """
        payload = decision.action_payload
        app_id: Optional[str] = payload.get("app_id")
        app_type: str = payload.get("app_type") or "custom"
        features: List[str] = list(payload.get("features", []))
        price: float = float(payload.get("price", 9.99))
        recurring: bool = bool(payload.get("recurring", False))

        try:
            if decision.decision_type == "spin_up_app":
                await self._execute_spin_up(app_id, app_type, features, price, recurring, decision)
            elif decision.decision_type == "add_feature":
                await self._execute_add_feature(app_id, features, decision)
            elif decision.decision_type == "adjust_pricing":
                await self._execute_adjust_pricing(app_id, price, recurring, decision)
            elif decision.decision_type == "sunset_app":
                await self._execute_sunset(app_id, decision)
            else:
                decision.status = "failed"
                decision.result_summary = f"Unknown decision type: {decision.decision_type}"
        except Exception as exc:
            decision.status = "failed"
            decision.result_summary = str(exc)
            raise
        finally:
            self.log_decision(decision)
            self._save_vault()

    # ── Execution Helpers ───────────────────────────────────────────────────

    async def _execute_spin_up(
        self,
        app_id: Optional[str],
        app_type: str,
        features: List[str],
        price: float,
        recurring: bool,
        decision: BusinessDecision,
    ):
        """Create a brand-new micro-SaaS app end-to-end."""
        new_app_id = app_id or f"{app_type}_{uuid.uuid4().hex[:8]}"

        # 1. Ensure idea inventory is healthy
        ideas = self.vault.find("app_ideas", limit=5)
        if not ideas:
            research = await self.tools.execute("research_micro_saas_ideas", niche="general")
            for idea in research.get("ideas", []):
                self.vault.insert("app_ideas", idea)

        # 2. Generate runnable code
        code_result = await self.tools.execute(
            "generate_app_code", app_type=app_type, features=features, tech_stack="flask"
        )
        if "error" in code_result:
            raise RuntimeError(f"Code generation failed: {code_result['error']}")

        # 3. Create Stripe payment link
        stripe_result = await self.tools.execute(
            "create_stripe_payment_link_for_app",
            app_id=new_app_id,
            price=price,
            recurring=recurring,
        )

        # 4. Package for deployment
        # Save a preliminary record so package_app_for_deploy can read tech_stack
        prelim_doc = {
            "app_id": new_app_id,
            "app_type": app_type,
            "features": features,
            "price": price,
            "recurring": recurring,
            "status": "active",
            "tech_stack": code_result.get("tech_stack", "flask"),
            "code_files": code_result.get("files", {}),
            "main_file": code_result.get("main_file", "app.py"),
            "decision_id": decision.decision_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.vault.insert("micro_apps", prelim_doc, doc_id=new_app_id)

        deploy_result = await self.tools.execute("package_app_for_deploy", app_id=new_app_id)

        # 5. Finalize vault record
        self.vault.update(
            "micro_apps",
            new_app_id,
            {
                "payment_link": stripe_result.get("payment_link"),
                "stripe_price_id": stripe_result.get("price_id"),
                "stripe_product_id": stripe_result.get("product_id"),
                "stripe_status": stripe_result.get("status"),
                "deploy_manifest": deploy_result.get("manifest", {}),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )

        # 6. Seed analytics
        await self.tools.execute("get_app_analytics", app_id=new_app_id)

        decision.status = "executed"
        decision.result_summary = (
            f"Created {app_type} app '{new_app_id}' with {len(features)} features. "
            f"Payment link: {stripe_result.get('payment_link')}. "
            f"Deploy manifest: {deploy_result.get('status')}."
        )
        decision.actual_revenue = 0.0

    async def _execute_add_feature(
        self,
        app_id: Optional[str],
        features: List[str],
        decision: BusinessDecision,
    ):
        """Add features to an existing app and regenerate its code."""
        if not app_id:
            raise ValueError("app_id is required for add_feature")

        existing = self.vault.get("micro_apps", app_id)
        if not existing:
            raise ValueError(f"App {app_id} not found")

        merged_features = list(set(existing.get("features", []) + features))
        code_result = await self.tools.execute(
            "generate_app_code",
            app_type=existing.get("app_type", "custom"),
            features=merged_features,
            tech_stack=existing.get("tech_stack", "flask"),
        )

        self.vault.update(
            "micro_apps",
            app_id,
            {
                "features": merged_features,
                "code_files": code_result.get("files", {}),
                "main_file": code_result.get("main_file", "app.py"),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )

        decision.status = "executed"
        decision.result_summary = f"Updated app '{app_id}' with features: {features}"

    async def _execute_adjust_pricing(
        self,
        app_id: Optional[str],
        price: float,
        recurring: bool,
        decision: BusinessDecision,
    ):
        """Update pricing and generate a new Stripe payment link."""
        if not app_id:
            raise ValueError("app_id is required for adjust_pricing")

        stripe_result = await self.tools.execute(
            "create_stripe_payment_link_for_app",
            app_id=app_id,
            price=price,
            recurring=recurring,
        )

        self.vault.update(
            "micro_apps",
            app_id,
            {
                "price": price,
                "recurring": recurring,
                "payment_link": stripe_result.get("payment_link"),
                "stripe_price_id": stripe_result.get("price_id"),
                "stripe_product_id": stripe_result.get("product_id"),
                "stripe_status": stripe_result.get("status"),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )

        decision.status = "executed"
        decision.result_summary = (
            f"Updated pricing for '{app_id}' to ${price:.2f} "
            f"({'recurring' if recurring else 'one-time'})."
        )

    async def _execute_sunset(
        self,
        app_id: Optional[str],
        decision: BusinessDecision,
    ):
        """Sunset a failing or obsolete app."""
        if not app_id:
            raise ValueError("app_id is required for sunset_app")

        sunset_result = await self.tools.execute("sunset_app", app_id=app_id)
        if "error" in sunset_result:
            raise RuntimeError(sunset_result["error"])

        decision.status = "executed"
        decision.result_summary = sunset_result.get("message", f"App '{app_id}' has been sunset.")
