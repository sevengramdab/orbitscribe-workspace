"""
Stripe business tools for the monetization swarm.

All functions are registered as business tools and wrapped for async execution.
They call the real Stripe API when STRIPE_API_KEY is configured and raise
otherwise.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import config
from core.business_tools.registry import business_tool
from core.business_tools.vault import vault

try:
    import stripe

    _STRIPE_AVAILABLE = True
except ImportError:  # pragma: no cover
    stripe = None  # type: ignore
    _STRIPE_AVAILABLE = False

if config.LIVE_MODE and not config.STRIPE_API_KEY:
    raise RuntimeError(
        "LIVE_MODE is enabled but STRIPE_API_KEY is not set. "
        "Add your Stripe key to environment variables."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api_key() -> Optional[str]:
    """Return the Stripe API key from configuration."""
    return config.STRIPE_API_KEY


def _iso_to_timestamp(iso_date: str) -> int:
    """Convert an ISO-8601 date string to a Unix timestamp."""
    dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    return int(dt.timestamp())


async def _run_sync(fn, *args, **kwargs):
    """Run a blocking Stripe SDK call in the default thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


# ---------------------------------------------------------------------------
# Business tools
# ---------------------------------------------------------------------------


@business_tool(
    name="stripe_create_customer",
    description="Create a Stripe customer and persist the record to the vault.",
    category="payments",
    requires_api_key=True,
    api_key_env="STRIPE_API_KEY",
)
async def stripe_create_customer(
    email: str,
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a new Stripe customer.

    Args:
        email: Customer email address.
        name: Customer display name.
        metadata: Optional key-value metadata dictionary.

    Returns:
        Dict containing the created customer.
    """
    metadata = metadata or {}
    key = _api_key()

    if not _STRIPE_AVAILABLE or not key:
        raise ValueError("STRIPE_API_KEY required in LIVE_MODE")

    try:
        customer = await _run_sync(
            stripe.Customer.create,
            email=email,
            name=name,
            metadata=metadata,
            api_key=key,
        )
        record = {
            "id": customer.id,
            "email": customer.email,
            "name": customer.name,
            "metadata": dict(customer.metadata) if customer.metadata else {},
            "created": customer.created,
        }
        vault.insert("stripe_customers", record)
        return {"success": True, "customer": record}
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "tool": "stripe_create_customer"}


@business_tool(
    name="stripe_create_product",
    description=(
        "Create a Stripe product and an associated price. "
        "Persist the pricing experiment to the vault."
    ),
    category="payments",
    requires_api_key=True,
    api_key_env="STRIPE_API_KEY",
)
async def stripe_create_product(
    name: str,
    description: str,
    price: int,
    recurring: bool = False,
) -> Dict[str, Any]:
    """
    Create a product and a price in Stripe.

    Args:
        name: Product name.
        description: Product description.
        price: Unit amount in the smallest currency unit (e.g. cents).
        recurring: Whether the price should be recurring (monthly).

    Returns:
        Dict with product and price IDs.
    """
    key = _api_key()

    if not _STRIPE_AVAILABLE or not key:
        raise ValueError("STRIPE_API_KEY required in LIVE_MODE")

    try:
        product = await _run_sync(
            stripe.Product.create,
            name=name,
            description=description,
            api_key=key,
        )

        price_data: Dict[str, Any] = {
            "unit_amount": price,
            "currency": "usd",
            "product": product.id,
        }
        if recurring:
            price_data["recurring"] = {"interval": "month"}

        price_obj = await _run_sync(stripe.Price.create, api_key=key, **price_data)

        record = {
            "product_id": product.id,
            "price_id": price_obj.id,
            "name": name,
            "unit_amount": price,
            "currency": "usd",
            "recurring": recurring,
        }
        vault.insert("pricing_experiments", record)
        return {"success": True, "product": record}
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "tool": "stripe_create_product"}


@business_tool(
    name="stripe_create_invoice",
    description="Create a draft invoice for a customer and add line items.",
    category="payments",
    requires_api_key=True,
    api_key_env="STRIPE_API_KEY",
)
async def stripe_create_invoice(
    customer_id: str,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Create a draft invoice and attach line items.

    Args:
        customer_id: Stripe customer ID.
        items: List of dicts, each with ``price`` (str) and
               optional ``quantity`` (int).

    Returns:
        Dict with invoice details.
    """
    key = _api_key()

    if not _STRIPE_AVAILABLE or not key:
        raise ValueError("STRIPE_API_KEY required in LIVE_MODE")

    try:
        invoice = await _run_sync(
            stripe.Invoice.create,
            customer=customer_id,
            auto_advance=True,  # draft state
            api_key=key,
        )

        for it in items:
            await _run_sync(
                stripe.InvoiceItem.create,
                customer=customer_id,
                invoice=invoice.id,
                price=it["price"],
                quantity=it.get("quantity", 1),
                api_key=key,
            )

        record = {
            "id": invoice.id,
            "customer": customer_id,
            "status": "draft",
            "lines": items,
            "amount_due": getattr(invoice, "amount_due", 0),
        }
        vault.insert("stripe_invoices", record)
        return {"success": True, "invoice": record}
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "tool": "stripe_create_invoice"}


@business_tool(
    name="stripe_create_checkout_session",
    description="Create a Stripe Checkout session and return the payment URL.",
    category="payments",
    requires_api_key=True,
    api_key_env="STRIPE_API_KEY",
)
async def stripe_create_checkout_session(
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> Dict[str, Any]:
    """
    Create a hosted checkout session.

    Args:
        price_id: Stripe Price ID.
        success_url: Redirect URL after successful payment.
        cancel_url: Redirect URL after cancelled payment.

    Returns:
        Dict containing ``checkout_url``.
    """
    key = _api_key()

    if not _STRIPE_AVAILABLE or not key:
        raise ValueError("STRIPE_API_KEY required in LIVE_MODE")

    try:
        # Determine mode from the price object when possible.
        price_obj = await _run_sync(
            stripe.Price.retrieve,
            price_id,
            api_key=key,
        )
        mode = "subscription" if getattr(price_obj, "recurring", None) else "payment"

        session = await _run_sync(
            stripe.checkout.Session.create,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode=mode,
            success_url=success_url,
            cancel_url=cancel_url,
            api_key=key,
        )
        return {
            "success": True,
            "session_id": session.id,
            "checkout_url": session.url,
        }
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "tool": "stripe_create_checkout_session"}


@business_tool(
    name="stripe_list_failed_payments",
    description="List recent failed charges from Stripe.",
    category="payments",
    requires_api_key=True,
    api_key_env="STRIPE_API_KEY",
)
async def stripe_list_failed_payments(limit: int = 50) -> Dict[str, Any]:
    """
    Retrieve recent charges with ``status == 'failed'``.

    Args:
        limit: Maximum number of failed charges to return.

    Returns:
        Dict with a ``failed_payments`` list.
    """
    key = _api_key()

    if not _STRIPE_AVAILABLE or not key:
        raise ValueError("STRIPE_API_KEY required in LIVE_MODE")

    try:
        charges = await _run_sync(
            stripe.Charge.list,
            limit=limit,
            api_key=key,
        )
        failed: List[Dict[str, Any]] = []
        for ch in charges.auto_paging_iter():
            if ch.status == "failed":
                failed.append(
                    {
                        "id": ch.id,
                        "customer": ch.customer,
                        "amount": ch.amount,
                        "currency": ch.currency,
                        "status": ch.status,
                        "failure_message": ch.failure_message,
                        "invoice": getattr(ch, "invoice", None),
                        "created": ch.created,
                    }
                )
            if len(failed) >= limit:
                break

        return {
            "success": True,
            "failed_payments": failed,
            "count": len(failed),
        }
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "tool": "stripe_list_failed_payments"}


@business_tool(
    name="stripe_retry_invoice",
    description="Attempt to collect payment on an open invoice.",
    category="payments",
    requires_api_key=True,
    api_key_env="STRIPE_API_KEY",
)
async def stripe_retry_invoice(invoice_id: str) -> Dict[str, Any]:
    """
    Retry payment collection for an invoice.

    Args:
        invoice_id: Stripe Invoice ID.

    Returns:
        Dict with payment result.
    """
    key = _api_key()

    if not _STRIPE_AVAILABLE or not key:
        raise ValueError("STRIPE_API_KEY required in LIVE_MODE")

    try:
        invoice = await _run_sync(
            stripe.Invoice.pay,
            invoice_id,
            api_key=key,
        )
        record = {
            "id": invoice.id,
            "status": invoice.status,
            "amount_paid": invoice.amount_paid,
            "customer": invoice.customer,
        }
        # Upsert in vault
        existing = vault.find(
            "stripe_invoices", filter_fn=lambda d: d.get("id") == invoice.id
        )
        if existing:
            vault.update("stripe_invoices", existing[0]["_id"], record)
        else:
            vault.insert("stripe_invoices", record)
        return {"success": True, "invoice": record}
    except Exception as exc:  # pragma: no cover
        return {
            "error": str(exc),
            "tool": "stripe_retry_invoice",
            "invoice_id": invoice_id,
        }


@business_tool(
    name="stripe_create_coupon",
    description="Create a promotional coupon (e.g. for churn recovery).",
    category="payments",
    requires_api_key=True,
    api_key_env="STRIPE_API_KEY",
)
async def stripe_create_coupon(
    percent_off: float,
    duration: str = "once",
) -> Dict[str, Any]:
    """
    Create a Stripe coupon.

    Args:
        percent_off: Percentage discount (0-100).
        duration: ``once``, ``repeating``, or ``forever``.

    Returns:
        Dict with coupon details.
    """
    key = _api_key()

    if not _STRIPE_AVAILABLE or not key:
        raise ValueError("STRIPE_API_KEY required in LIVE_MODE")

    try:
        coupon = await _run_sync(
            stripe.Coupon.create,
            percent_off=percent_off,
            duration=duration,
            api_key=key,
        )
        record = {
            "id": coupon.id,
            "percent_off": coupon.percent_off,
            "duration": coupon.duration,
        }
        return {"success": True, "coupon": record}
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "tool": "stripe_create_coupon"}


@business_tool(
    name="stripe_get_revenue_summary",
    description="Compute MRR, churn, and revenue for a date range.",
    category="analytics",
    requires_api_key=True,
    api_key_env="STRIPE_API_KEY",
)
async def stripe_get_revenue_summary(
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """
    Aggregate revenue metrics from Stripe for the given period.

    Args:
        start_date: ISO-8601 date string (inclusive).
        end_date: ISO-8601 date string (inclusive).

    Returns:
        Dict with ``mrr``, ``total_revenue``, ``new_subscriptions``,
        ``churned_subscriptions``, and ``failed_payments_count``.
    """
    key = _api_key()

    if not _STRIPE_AVAILABLE or not key:
        raise ValueError("STRIPE_API_KEY required in LIVE_MODE")

    try:
        start_ts = _iso_to_timestamp(start_date)
        end_ts = _iso_to_timestamp(end_date) + 86400  # inclusive end date

        # Paid invoices in period
        invoices = await _run_sync(
            stripe.Invoice.list,
            status="paid",
            created={"gte": start_ts, "lte": end_ts},
            limit=100,
            api_key=key,
        )
        total_revenue = 0
        for inv in invoices.auto_paging_iter():
            total_revenue += getattr(inv, "amount_paid", 0) or 0

        # Active subscriptions for MRR
        subs = await _run_sync(
            stripe.Subscription.list,
            status="active",
            limit=100,
            api_key=key,
        )
        mrr_cents = 0
        for sub in subs.auto_paging_iter():
            for item in sub.items.data:
                plan = item.plan
                if not plan:
                    continue
                amount = getattr(plan, "amount", 0) or 0
                qty = getattr(item, "quantity", 1) or 1
                interval = getattr(plan, "interval", "month")
                if interval == "month":
                    mrr_cents += amount * qty
                elif interval == "year":
                    mrr_cents += (amount * qty) / 12
                elif interval == "week":
                    mrr_cents += (amount * qty) * 4.33
                elif interval == "day":
                    mrr_cents += (amount * qty) * 30

        # New subscriptions created in period
        new_subs = await _run_sync(
            stripe.Subscription.list,
            status="all",
            created={"gte": start_ts, "lte": end_ts},
            limit=100,
            api_key=key,
        )
        new_subscriptions = sum(1 for _ in new_subs.auto_paging_iter())

        # Canceled subscriptions in period
        canceled_subs = await _run_sync(
            stripe.Subscription.list,
            status="canceled",
            ended_at={"gte": start_ts, "lte": end_ts},
            limit=100,
            api_key=key,
        )
        churned = sum(1 for _ in canceled_subs.auto_paging_iter())

        # Failed payments in period
        failed_charges = await _run_sync(
            stripe.Charge.list,
            created={"gte": start_ts, "lte": end_ts},
            limit=100,
            api_key=key,
        )
        failed_count = sum(
            1 for ch in failed_charges.auto_paging_iter() if ch.status == "failed"
        )

        return {
            "success": True,
            "mrr": round(mrr_cents / 100, 2),
            "total_revenue": round(total_revenue / 100, 2),
            "new_subscriptions": new_subscriptions,
            "churned_subscriptions": churned,
            "failed_payments_count": failed_count,
            "period": {"start": start_date, "end": end_date},
        }
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "tool": "stripe_get_revenue_summary"}
