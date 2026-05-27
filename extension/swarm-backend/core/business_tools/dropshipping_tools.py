"""
Dropshipping business tools for product research, profit analysis,
listing generation, and unified-vault persistence.

All tools are registered via the @business_tool decorator so they can be
discovered and executed by any BusinessToolRegistry instance.
"""

import asyncio
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.business_tools.registry import business_tool
from core.business_tools.vault import vault
from core.model_router import router


# ── Platform fee reference (simplified industry-standard estimates) ──────────
PLATFORM_FEES: Dict[str, Dict[str, float]] = {
    "etsy": {
        "listing_fee": 0.20,
        "transaction_pct": 0.065,
        "payment_processing_pct": 0.03,
        "payment_processing_fixed": 0.25,
        "offsite_ads_pct": 0.15,
    },
    "shopify": {
        "subscription_monthly": 29.0,
        "payment_processing_pct": 0.029,
        "payment_processing_fixed": 0.30,
        "listing_fee": 0.0,
        "transaction_pct": 0.0,
    },
    "amazon": {
        "referral_pct": 0.15,
        "fulfillment_per_unit": 5.0,
        "listing_fee": 0.0,
    },
    "ebay": {
        "final_value_pct": 0.1325,
        "insertion_fee": 0.30,
        "payment_processing_pct": 0.029,
        "payment_processing_fixed": 0.30,
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _ddg_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Search DuckDuckGo HTML API (no API key required)."""
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        results: List[Dict[str, str]] = []
        patterns = [
            r'<a[^>]*class="result__a"[^>]*href="(https?://[^"]+)"[^>]*>([^<]+)</a>',
            r'<a[^>]*href="(https?://[^"]+)"[^>]*class="result__a"[^>]*>([^<]+)</a>',
            r'<a[^>]*href="(https?://[^"]+)"[^>]*class="result__snippet"[^>]*>([^<]+)</a>',
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>([^<]{10,200})</a>',
        ]
        for pattern in patterns:
            if len(results) >= max_results:
                break
            for match in re.finditer(pattern, html, re.IGNORECASE):
                href = match.group(1)
                title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
                if href and title and len(title) > 5 and "duckduckgo" not in href.lower():
                    if not any(r["url"] == href for r in results):
                        results.append({"title": title, "url": href})
                if len(results) >= max_results:
                    break
        return results
    except Exception as exc:
        return [{"title": f"Search error: {exc}", "url": ""}]


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extraction from an LLM response string."""
    try:
        # Try the whole text first
        return json.loads(text)
    except Exception:
        pass
    # Look for a JSON object block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None


# ── Registered Tools ─────────────────────────────────────────────────────────


@business_tool(
    name="research_trends",
    description="Search the web for trending products in a given niche.",
    category="dropshipping",
)
async def research_trends(niche: str) -> Dict[str, Any]:
    """
    Perform a web search for trending products in the supplied niche.

    Args:
        niche: The product niche to research (e.g. "digital planners").

    Returns:
        Dict with "results" (list of title/url dicts), "query", and status.
    """
    if not niche or not niche.strip():
        return {"error": "niche is required", "results": []}

    query = f"trending products {niche} 2024 2025"
    results = await asyncio.get_event_loop().run_in_executor(
        None, _ddg_search, query, 5
    )
    return {
        "status": "ok",
        "query": query,
        "results": results,
        "count": len(results),
    }


@business_tool(
    name="calculate_profit",
    description="Calculate net profit for a product on a given platform after fees.",
    category="dropshipping",
)
def calculate_profit(cost: float, price: float, platform: str) -> Dict[str, Any]:
    """
    Compute net profit, margin, and fee breakdown for a product.

    Args:
        cost: Unit cost of goods sold (COGS) in USD.
        price: Target selling price in USD.
        platform: One of "etsy", "shopify", "amazon", "ebay".

    Returns:
        Dict containing profit, margin, fees, and a human-readable breakdown.
    """
    platform = platform.lower().strip()
    if platform not in PLATFORM_FEES:
        return {
            "error": f"Unsupported platform '{platform}'. Supported: {list(PLATFORM_FEES.keys())}",
        }

    if cost < 0 or price < 0:
        return {"error": "cost and price must be non-negative"}

    fees = PLATFORM_FEES[platform]
    total_fees = 0.0
    breakdown: Dict[str, float] = {}

    # Listing / insertion fee (per-sale approximation)
    listing = fees.get("listing_fee", 0.0) + fees.get("insertion_fee", 0.0)
    if listing:
        total_fees += listing
        breakdown["listing_fee"] = round(listing, 2)

    # Transaction / referral / final-value fee
    tx_pct = fees.get("transaction_pct", 0.0) or fees.get("referral_pct", 0.0) or fees.get("final_value_pct", 0.0)
    if tx_pct:
        tx_fee = price * tx_pct
        total_fees += tx_fee
        breakdown["transaction_fee"] = round(tx_fee, 2)

    # Payment processing
    pp_pct = fees.get("payment_processing_pct", 0.0)
    pp_fixed = fees.get("payment_processing_fixed", 0.0)
    if pp_pct or pp_fixed:
        pp_fee = price * pp_pct + pp_fixed
        total_fees += pp_fee
        breakdown["payment_processing"] = round(pp_fee, 2)

    # Amazon FBA simplified estimate
    fba = fees.get("fulfillment_per_unit", 0.0)
    if fba:
        total_fees += fba
        breakdown["fulfillment_fee"] = round(fba, 2)

    net_profit = price - cost - total_fees
    margin = (net_profit / price * 100) if price > 0 else 0.0

    return {
        "status": "ok",
        "platform": platform,
        "cost": round(cost, 2),
        "price": round(price, 2),
        "total_fees": round(total_fees, 2),
        "net_profit": round(net_profit, 2),
        "margin_pct": round(margin, 2),
        "breakdown": breakdown,
        "recommendation": (
            "profitable" if net_profit > 5 and margin > 20 else
            "thin_margin" if net_profit > 0 else
            "unprofitable"
        ),
    }


@business_tool(
    name="generate_listing",
    description="Use the LLM to generate an optimized title, description, and tags for a product.",
    category="dropshipping",
)
async def generate_listing(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate platform-optimized listing content via LLM.

    Args:
        product: Dict with keys like name, niche, platform, keywords, audience.

    Returns:
        Dict with "title", "description", "tags", and "platform".
    """
    name = product.get("name", "")
    niche = product.get("niche", "")
    platform = product.get("platform", "etsy").lower()
    keywords = product.get("keywords", "")
    audience = product.get("audience", "")

    system_prompt = (
        "You are an expert e-commerce copywriter. Generate a product listing "
        "optimized for the requested platform. Respond ONLY with valid JSON."
    )
    user_prompt = f"""Create a {platform} listing for this product:

Name: {name}
Niche: {niche}
Keywords: {keywords}
Target Audience: {audience}

Respond in JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", "tag2", ...]
}}
"""
    try:
        text = await router.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        data = _extract_json(text) or {}
        return {
            "status": "ok",
            "platform": platform,
            "title": data.get("title", name),
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
            "raw": text,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "platform": platform,
            "title": name,
            "description": "",
            "tags": [],
        }


@business_tool(
    name="save_product_to_vault",
    description="Persist a product idea or active listing to the unified vault.",
    category="dropshipping",
)
def save_product_to_vault(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a product document to the "products" collection and record an entry
    in "pricing_history" if cost/price data is present.

    Args:
        product: Product dict. Should include at least "name" and "platform".

    Returns:
        Dict with "product_id" and "pricing_history_id" (if applicable).
    """
    if not product or not product.get("name"):
        return {"error": "Product must include a 'name' field."}

    doc = dict(product)
    doc.setdefault("platform", "etsy")
    doc.setdefault("status", "idea")  # idea | active | paused | archived
    doc.setdefault("sales_count", 0)
    doc.setdefault("created_at", datetime.utcnow().isoformat())

    product_id = vault.insert("products", doc)

    # Also record pricing snapshot if available
    pricing_history_id = None
    if "cost" in doc and "price" in doc:
        pricing_history_id = vault.insert(
            "pricing_history",
            {
                "product_id": product_id,
                "cost": doc["cost"],
                "price": doc["price"],
                "platform": doc["platform"],
                "note": doc.get("pricing_note", "initial"),
            },
        )

    return {
        "status": "saved",
        "product_id": product_id,
        "pricing_history_id": pricing_history_id,
        "platform": doc["platform"],
    }


@business_tool(
    name="update_product_price",
    description="Update a product's selling price in the vault and log the change.",
    category="dropshipping",
)
def update_product_price(product_id: str, new_price: float) -> Dict[str, Any]:
    """
    Update the price of an existing product and append a pricing_history record.

    Args:
        product_id: The vault _id of the product.
        new_price: The new selling price in USD.

    Returns:
        Dict with update status and pricing_history record id.
    """
    if not product_id:
        return {"error": "product_id is required"}
    if new_price < 0:
        return {"error": "new_price must be non-negative"}

    product = vault.get("products", product_id)
    if not product:
        return {"error": f"Product {product_id} not found"}

    old_price = product.get("price")
    success = vault.update("products", product_id, {"price": new_price})

    history_id = vault.insert(
        "pricing_history",
        {
            "product_id": product_id,
            "old_price": old_price,
            "new_price": new_price,
            "platform": product.get("platform", "etsy"),
            "note": "price_update",
        },
    )

    return {
        "status": "updated" if success else "failed",
        "product_id": product_id,
        "old_price": old_price,
        "new_price": new_price,
        "pricing_history_id": history_id,
    }


@business_tool(
    name="get_underperforming_products",
    description="Query the vault for products with no sales in the last N days.",
    category="dropshipping",
)
def get_underperforming_products(days: int = 30) -> Dict[str, Any]:
    """
    Return products that have zero total sales OR no sale recorded in the last N days.

    Args:
        days: Lookback window in days (default 30).

    Returns:
        Dict with "products" list and "count".
    """
    if days < 0:
        return {"error": "days must be non-negative", "products": [], "count": 0}

    cutoff = datetime.utcnow() - timedelta(days=days)

    def _is_underperforming(doc: Dict[str, Any]) -> bool:
        sales_count = doc.get("sales_count", 0)
        if sales_count == 0:
            return True
        last_sale = doc.get("last_sale_date")
        if last_sale:
            try:
                parsed = datetime.fromisoformat(last_sale.replace("Z", "+00:00"))
                return parsed < cutoff
            except Exception:
                return True
        return True

    products = vault.find("products", filter_fn=_is_underperforming, limit=100)
    return {
        "status": "ok",
        "days": days,
        "count": len(products),
        "products": products,
    }


@business_tool(
    name="get_competitor_intel",
    description="Fetch and store competitor search results for a niche in the vault.",
    category="dropshipping",
)
async def get_competitor_intel(niche: str, platform: str = "etsy") -> Dict[str, Any]:
    """
    Search the web for competitor listings in a niche and persist the results
    to the "competitor_intel" vault collection.

    Args:
        niche: Product niche to research.
        platform: Platform filter (etsy, shopify, amazon, ebay).

    Returns:
        Dict with saved intel id, result count, and raw results.
    """
    if not niche:
        return {"error": "niche is required"}

    query = f"{niche} {platform} best seller listing"
    results = await asyncio.get_event_loop().run_in_executor(
        None, _ddg_search, query, 5
    )

    intel_doc = {
        "niche": niche,
        "platform": platform,
        "query": query,
        "results": results,
        "result_count": len(results),
    }
    intel_id = vault.insert("competitor_intel", intel_doc)

    return {
        "status": "ok",
        "intel_id": intel_id,
        "niche": niche,
        "platform": platform,
        "result_count": len(results),
        "results": results,
    }
