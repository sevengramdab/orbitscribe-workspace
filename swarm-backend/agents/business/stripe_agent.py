"""
StripeAgent — Autonomous payment, subscription, and revenue optimization.

Perceives Stripe dashboard state and vault records, decides on revenue-protecting
actions (retry failed payments, create invoices, adjust pricing, send dunning,
create coupons), and executes them through the business tool registry.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.business_tools.vault import vault
from .base import BaseBusinessAgent, BusinessDecision


class StripeAgent(BaseBusinessAgent):
    """
    Autonomous Stripe agent that manages:

    * Failed-payment recovery
    * Invoice creation & collection
    * Subscription churn prevention
    * Pricing experiments
    * Promotional coupons

    All decisions are tracked in the agent ledger and persisted to the vault.
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
            name="StripeAgent",
            description="Autonomous payment, subscription, and revenue optimization agent.",
            llm_client=client,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )
        # Eager-import so that the @business_tool decorators register globally.
        try:
            import core.business_tools.stripe_tools  # noqa: F401
        except Exception as exc:  # pragma: no cover
            print(f"[StripeAgent] Could not load stripe tools: {exc}")

    # -----------------------------------------------------------------------
    # Perception
    # -----------------------------------------------------------------------

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather Stripe dashboard data, vault records, and churn signals.

        Queries:
        * Recent failed payments via Stripe API
        * Pending invoices from the vault
        * Subscriptions, customers, and pricing experiments from the vault
        * Revenue summary (MRR, churn, etc.) for the trailing 30 days

        Returns:
            A dictionary of observations used by :meth:`decide`.
        """
        now = datetime.utcnow()
        start_date = (now - timedelta(days=30)).date().isoformat()
        end_date = now.date().isoformat()

        # --- Stripe API calls ---
        failed_resp = await self.tools.execute("stripe_list_failed_payments", limit=50)
        revenue_resp = await self.tools.execute(
            "stripe_get_revenue_summary",
            start_date=start_date,
            end_date=end_date,
        )

        # --- Vault queries ---
        pending_invoices = vault.find(
            "stripe_invoices",
            filter_fn=lambda d: d.get("status") in ("draft", "open", "uncollectible"),
            limit=100,
        )
        subscriptions = vault.find("stripe_subscriptions", limit=200)
        customers = vault.find("stripe_customers", limit=200)
        pricing_experiments = vault.find("pricing_experiments", limit=50)

        # --- Churn signals ---
        churn_signals: List[Dict[str, Any]] = []
        for sub in subscriptions:
            if sub.get("status") == "canceled":
                churn_signals.append(
                    {
                        "type": "subscription_canceled",
                        "subscription_id": sub.get("id"),
                        "customer_id": sub.get("customer"),
                    }
                )

        for fp in failed_resp.get("failed_payments", []):
            churn_signals.append(
                {
                    "type": "payment_failed",
                    "charge_id": fp.get("id"),
                    "customer_id": fp.get("customer"),
                    "amount": fp.get("amount"),
                    "failure_message": fp.get("failure_message"),
                }
            )

        perception = {
            "failed_payments": failed_resp.get("failed_payments", []),
            "failed_payments_count": failed_resp.get("count", 0),
            "pending_invoices": pending_invoices,
            "pending_invoices_count": len(pending_invoices),
            "subscriptions": subscriptions,
            "subscription_count": len(subscriptions),
            "customers": customers,
            "customer_count": len(customers),
            "pricing_experiments": pricing_experiments,
            "revenue_summary": revenue_resp,
            "churn_signals": churn_signals,
            "churn_signal_count": len(churn_signals),
            "timestamp": now.isoformat(),
        }
        # Cache for execute() lookups (e.g. finding an invoice to retry).
        self._last_perception = perception
        return perception

    # -----------------------------------------------------------------------
    # Decision
    # -----------------------------------------------------------------------

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Use the LLM to decide the single best revenue-protecting action.

        Possible decisions:
        * ``retry_failed_payment`` – retry an open invoice.
        * ``create_invoice`` – generate a new draft invoice.
        * ``adjust_pricing`` – launch a pricing experiment (new product + price).
        * ``send_dunning`` – record a dunning notice for a customer.
        * ``create_coupon`` – issue a promotional coupon.
        * ``no_action`` – nothing to do.

        Returns:
            A :class:`BusinessDecision` or ``None`` when no action is needed.
        """
        if (
            perception.get("churn_signal_count", 0) == 0
            and perception.get("pending_invoices_count", 0) == 0
        ):
            # Fast path when the pipeline looks healthy.
            return None

        system_prompt = (
            "You are StripeAgent, an autonomous revenue-optimization AI. "
            "Given the current payment and subscription state, choose ONE action from: "
            "retry_failed_payment, create_invoice, adjust_pricing, send_dunning, "
            "create_coupon, no_action.\n\n"
            "Respond with a JSON object exactly like this:\n"
            "{\n"
            '  "decision_type": "retry_failed_payment|create_invoice|adjust_pricing|send_dunning|create_coupon|no_action",\n'
            '  "rationale": "...",\n'
            '  "action_payload": {},\n'
            '  "estimated_revenue_impact": 0.0,\n'
            '  "risk_score": 0.0,\n'
            '  "confidence": 0.0\n'
            "}"
        )

        user_prompt = (
            f"Period: last 30 days\n"
            f"Failed Payments: {perception['failed_payments_count']}\n"
            f"Pending Invoices: {perception['pending_invoices_count']}\n"
            f"Active Subscriptions (vault): {perception['subscription_count']}\n"
            f"Churn Signals: {perception['churn_signal_count']}\n"
            f"Revenue Summary: {json.dumps(perception['revenue_summary'], indent=2, default=str)}\n\n"
            f"Top Failed Payments:\n"
            f"{json.dumps(perception['failed_payments'][:5], indent=2, default=str)}\n\n"
            f"Top Churn Signals:\n"
            f"{json.dumps(perception['churn_signals'][:5], indent=2, default=str)}\n\n"
            f"Pending Invoices:\n"
            f"{json.dumps(perception['pending_invoices'][:5], indent=2, default=str)}"
        )

        result = await self.llm_decide(system_prompt, user_prompt)

        decision_type = result.get("decision_type", "no_action")
        if decision_type == "no_action":
            return None

        return BusinessDecision(
            agent_name=self.name,
            decision_type=decision_type,
            rationale=result.get("rationale", ""),
            action_payload=result.get("action_payload", {}),
            estimated_revenue_impact=float(result.get("estimated_revenue_impact", 0.0)),
            risk_score=float(result.get("risk_score", 0.5)),
            confidence=float(result.get("confidence", 0.5)),
        )

    # -----------------------------------------------------------------------
    # Execution
    # -----------------------------------------------------------------------

    async def execute(self, decision: BusinessDecision):
        """
        Execute the approved decision, update the vault, and record revenue.

        Side effects:
        * Calls the relevant Stripe business tool.
        * Persists records to vault collections.
        * Updates ``decision.status``, ``decision.actual_revenue``, and the ledger.
        """
        payload = decision.action_payload or {}
        result: Dict[str, Any] = {}
        actual_revenue = 0.0

        try:
            if decision.decision_type == "retry_failed_payment":
                inv_id = payload.get("invoice_id")
                if not inv_id:
                    # Fall back to the most recent failed payment with an invoice.
                    perception = getattr(self, "_last_perception", {})
                    for fp in perception.get("failed_payments", []):
                        inv_id = fp.get("invoice")
                        if inv_id:
                            break
                if inv_id:
                    result = await self.tools.execute(
                        "stripe_retry_invoice", invoice_id=inv_id
                    )
                else:
                    result = {"warning": "No invoice_id found for retry."}

            elif decision.decision_type == "create_invoice":
                result = await self.tools.execute(
                    "stripe_create_invoice",
                    customer_id=payload.get("customer_id"),
                    items=payload.get("items", []),
                )

            elif decision.decision_type == "adjust_pricing":
                prod_result = await self.tools.execute(
                    "stripe_create_product",
                    name=payload.get("name", "Pricing Experiment"),
                    description=payload.get("description", ""),
                    price=int(payload.get("price", 0)),
                    recurring=payload.get("recurring", False),
                )
                vault.insert(
                    "pricing_experiments",
                    {
                        "experiment_name": payload.get("name"),
                        "decision_id": decision.decision_id,
                        "result": prod_result,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                result = prod_result

            elif decision.decision_type == "send_dunning":
                record = {
                    "type": "dunning_record",
                    "decision_id": decision.decision_id,
                    "customer_id": payload.get("customer_id"),
                    "invoice_id": payload.get("invoice_id"),
                    "message": payload.get(
                        "message",
                        "Your payment failed. Please update your payment method to avoid service interruption.",
                    ),
                    "status": "dunning_sent",
                    "sent_at": datetime.utcnow().isoformat(),
                }
                vault.insert("stripe_invoices", record)
                result = {"status": "dunning_recorded", "record": record}

            elif decision.decision_type == "create_coupon":
                result = await self.tools.execute(
                    "stripe_create_coupon",
                    percent_off=float(payload.get("percent_off", 10.0)),
                    duration=payload.get("duration", "once"),
                )
                # Coupons are a cost center — treat the estimated impact as a cost.
                actual_revenue = -abs(decision.estimated_revenue_impact)

            else:
                result = {
                    "warning": f"Unhandled decision type: {decision.decision_type}"
                }

        except Exception as exc:
            decision.status = "failed"
            result = {"error": str(exc), "decision_type": decision.decision_type}

        # Derive actual revenue from tool results when possible.
        if decision.status != "failed":
            if isinstance(result, dict) and result.get("success"):
                if "invoice" in result:
                    inv = result["invoice"]
                    if isinstance(inv, dict):
                        actual_revenue = float(inv.get("amount_paid", 0)) / 100.0
                        if actual_revenue == 0.0:
                            actual_revenue = float(inv.get("amount_due", 0)) / 100.0
                elif "customer" in result:
                    actual_revenue = 0.0
            decision.status = "executed"

        decision.result_summary = json.dumps(result, indent=2, default=str)
        decision.actual_revenue = actual_revenue
        self.log_decision(decision)
