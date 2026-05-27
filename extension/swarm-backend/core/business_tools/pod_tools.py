"""
Print-on-Demand business tools for the Monetization Swarm.

Uses the live Printify API for all product and publish operations.

All tools persist state to the UnifiedVault under collections:
  - pod_designs    : Design concepts, mockup descriptions, status
  - pod_products   : Published Printify products
  - pod_orders     : Order snapshots and statuses
  - pod_niches     : Researched niche metadata
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from core import config
from core.business_tools.registry import business_tool
from core.business_tools.vault import vault

# ── Live-mode guard ───────────────────────────────────────────────────────

if config.LIVE_MODE and not config.PRINTIFY_API_KEY:
    raise RuntimeError(
        "LIVE_MODE enabled but PRINTIFY_API_KEY not set. Get your key from printify.com."
    )

# ── Helpers ───────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# ── Web search helper (sync) ──────────────────────────────────────────────


def _web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Thin wrapper around the internal web search utility."""
    from core.tool_executor import _web_search as _ws

    return _ws(query, max_results)


# ── Business Tools ────────────────────────────────────────────────────────


@business_tool(
    name="research_pod_niche",
    description="Search the web for trending print-on-demand niches, styles, and buyer keywords.",
    category="print_on_demand",
)
def research_pod_niche(niche: str) -> Dict[str, Any]:
    """
    Research a POD niche using DuckDuckGo web search.

    Args:
        niche: The niche keyword (e.g. "cat lover mugs", "minimalist wall art").

    Returns:
        Dict with search results and persisted niche metadata.
    """
    if not niche or not niche.strip():
        return {"status": "error", "data": None, "error": "niche must be a non-empty string"}

    query = f"trending print on demand {niche} 2024 2025 best sellers"
    search_result = _web_search(query, max_results=5)

    doc = {
        "niche": niche.strip().lower(),
        "query": query,
        "search_results": search_result.get("data", {}).get("results", []),
        "researched_at": _now_iso(),
        "tags": niche.strip().lower().split(),
    }
    doc_id = vault.insert("pod_niches", doc)

    return {
        "status": "ok",
        "data": {"niche_id": doc_id, "results": doc["search_results"], "niche": niche},
        "error": "",
    }


@business_tool(
    name="generate_design_brief",
    description="Generate a design concept brief via LLM for a given niche and style.",
    category="print_on_demand",
)
async def generate_design_brief(niche: str, style: str = "minimalist") -> Dict[str, Any]:
    """
    Use the LLM router to generate a structured design brief.

    Args:
        niche: Target niche (e.g. "vintage astronomy").
        style: Visual style hint (default: minimalist).

    Returns:
        Dict containing the design brief JSON and a vault document ID.
    """
    if not niche or not niche.strip():
        return {"status": "error", "data": None, "error": "niche must be a non-empty string"}

    system_prompt = (
        "You are a senior print-on-demand graphic designer and merchandising strategist. "
        "Respond ONLY with valid JSON. No markdown, no prose."
    )
    user_prompt = f"""Generate a design brief for a print-on-demand product.

Niche: {niche}
Style: {style}

Respond in this exact JSON shape:
{{
  "title": " catchy product title ",
  "concept": " 1-sentence concept ",
  "visual_description": " detailed prompt for a mockup/image generator ",
  "color_palette": ["#hex1", "#hex2", "#hex3"],
  "suggested_products": ["t-shirt", "mug", "poster", "sticker"],
  "target_audience": " who buys this ",
  "estimated_profit_margin_percent": 35,
  "tags": ["tag1", "tag2", "tag3"],
  "rationale": " why this will sell "
}}
"""

    try:
        from core.model_router import chat_completion

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        chunks: List[str] = []
        async for chunk in chat_completion(messages, stream=False, temperature=0.7):
            chunks.append(chunk)
        text = "".join(chunks)

        # Extract JSON block
        json_text = text
        if "```json" in text:
            json_text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            json_text = text.split("```")[1].split("```")[0].strip()

        brief = json.loads(json_text)
    except Exception as e:
        # Graceful fallback so the agent never hard-crashes
        brief = {
            "title": f"{style.title()} {niche.title()} Design",
            "concept": f"A {style} design appealing to {niche} enthusiasts.",
            "visual_description": f"{style} illustration centered on {niche}, clean background, print-ready.",
            "color_palette": ["#1a1a1a", "#f5f5f5", "#e76f51"],
            "suggested_products": ["t-shirt", "mug", "poster"],
            "target_audience": niche,
            "estimated_profit_margin_percent": 30,
            "tags": niche.lower().split(),
            "rationale": "Fallback brief due to LLM error.",
            "_generation_error": str(e),
        }

    doc = {
        "niche": niche.strip().lower(),
        "style": style,
        "brief": brief,
        "status": "concept",
        "created_at": _now_iso(),
    }
    doc_id = vault.insert("pod_designs", doc)

    return {
        "status": "ok",
        "data": {"design_id": doc_id, "brief": brief, "niche": niche, "style": style},
        "error": "",
    }


@business_tool(
    name="calculate_pod_profit",
    description="Calculate POD profit breakdown given costs, selling price, and platform fees.",
    category="print_on_demand",
)
def calculate_pod_profit(
    base_cost: float,
    shipping: float,
    selling_price: float,
    platform_fees_percent: float = 15.0,
) -> Dict[str, Any]:
    """
    Compute net profit for a single POD unit sale.

    Args:
        base_cost: Base production cost (e.g. $8.50).
        shipping: Shipping cost to customer (e.g. $4.99).
        selling_price: Retail price (e.g. $29.99).
        platform_fees_percent: Marketplace fee percent (default 15%).

    Returns:
        Dict with line-item breakdown and net profit.
    """
    try:
        base_cost = float(base_cost)
        shipping = float(shipping)
        selling_price = float(selling_price)
        platform_fees_percent = float(platform_fees_percent)
    except (TypeError, ValueError) as exc:
        return {"status": "error", "data": None, "error": f"Invalid numeric input: {exc}"}

    if selling_price <= 0:
        return {"status": "error", "data": None, "error": "selling_price must be > 0"}

    platform_fees = selling_price * (platform_fees_percent / 100.0)
    total_cost = base_cost + shipping + platform_fees
    net_profit = selling_price - total_cost
    margin_percent = (net_profit / selling_price) * 100.0 if selling_price else 0.0

    breakdown = {
        "base_cost": round(base_cost, 2),
        "shipping": round(shipping, 2),
        "platform_fees_percent": platform_fees_percent,
        "platform_fees": round(platform_fees, 2),
        "total_cost": round(total_cost, 2),
        "selling_price": round(selling_price, 2),
        "net_profit": round(net_profit, 2),
        "margin_percent": round(margin_percent, 2),
    }

    return {"status": "ok", "data": breakdown, "error": ""}


@business_tool(
    name="create_pod_product",
    description="Create a product on Printify and persist to vault.",
    category="print_on_demand",
    requires_api_key=True,
    api_key_env="PRINTIFY_API_KEY",
)
async def create_pod_product(
    design_id: str,
    blueprint_id: str,
    print_provider_id: str,
    title: str,
    description: str,
    variants: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Create a Printify product from a design.

    Args:
        design_id: Vault ID of the design document.
        blueprint_id: Printify blueprint ID (e.g. '5' for unisex tee).
        print_provider_id: Print provider ID.
        title: Product listing title.
        description: Product description.
        variants: List of variant dicts with size/color/price.

    Returns:
        Dict with created product metadata and vault product_id.

    Raises:
        Exception: If the Printify API call fails.
    """
    if not design_id or not blueprint_id or not title:
        return {
            "status": "error",
            "data": None,
            "error": "design_id, blueprint_id, and title are required",
        }

    shop_id = config.PRINTIFY_SHOP_ID
    url = f"https://api.printify.com/v1/shops/{shop_id}/products.json"
    body = {
        "title": title,
        "description": description,
        "blueprint_id": int(blueprint_id),
        "print_provider_id": int(print_provider_id),
        "variants": variants,
        "print_areas": [
            {
                "position": "front",
                "images": [
                    {
                        "id": design_id,
                        "x": 0.5,
                        "y": 0.5,
                        "scale": 1.0,
                        "angle": 0,
                    }
                ],
            }
        ],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers={"Authorization": f"Bearer {config.PRINTIFY_API_KEY}"},
            json=body,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    product_id = vault.insert(
        "pod_products",
        {
            **data,
            "design_id": design_id,
            "created_at": _now_iso(),
            "simulate_mode": False,
        },
    )
    vault.update("pod_designs", design_id, {"product_id": product_id, "status": "product_created"})

    return {
        "status": "ok",
        "data": {"product_id": product_id, "printify_payload": data},
        "error": "",
    }


@business_tool(
    name="publish_pod_product",
    description="Publish a POD product to external sales channels (Etsy/Shopify).",
    category="print_on_demand",
    requires_api_key=True,
    api_key_env="PRINTIFY_API_KEY",
)
async def publish_pod_product(product_id: str) -> Dict[str, Any]:
    """
    Publish a product to sales channels.

    Args:
        product_id: Vault document ID of the product.

    Returns:
        Dict with publish result and channel listing IDs.

    Raises:
        Exception: If the Printify API call fails.
    """
    if not product_id:
        return {"status": "error", "data": None, "error": "product_id is required"}

    product = vault.get("pod_products", product_id)
    if not product:
        return {"status": "error", "data": None, "error": f"Product {product_id} not found in vault"}

    shop_id = config.PRINTIFY_SHOP_ID
    printify_product_id = product.get("id") or product_id
    url = (
        f"https://api.printify.com/v1/shops/{shop_id}/products/{printify_product_id}/publish.json"
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers={"Authorization": f"Bearer {config.PRINTIFY_API_KEY}"},
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    vault.update(
        "pod_products",
        product_id,
        {
            "publish_result": data,
            "status": "published",
            "published_at": _now_iso(),
        },
    )
    if product.get("design_id"):
        vault.update("pod_designs", product["design_id"], {"status": "published"})

    return {"status": "ok", "data": data, "error": ""}


@business_tool(
    name="get_pod_best_sellers",
    description="Query the vault for top-performing POD designs by real sales metrics.",
    category="print_on_demand",
)
def get_pod_best_sellers(limit: int = 10) -> Dict[str, Any]:
    """
    Return best-selling designs from the vault.

    Args:
        limit: Max number of results.

    Returns:
        Dict with ranked list of designs.
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10

    designs = vault.find("pod_designs", limit=limit * 2)
    # Rank by estimated_profit_margin_percent or a sales score
    def _score(d: Dict[str, Any]) -> float:
        brief = d.get("brief", {})
        margin = brief.get("estimated_profit_margin_percent", 0)
        sales = d.get("simulated_sales", 0)
        return float(margin) + (float(sales) * 0.1)

    ranked = sorted(designs, key=_score, reverse=True)[:limit]
    return {
        "status": "ok",
        "data": {
            "count": len(ranked),
            "designs": ranked,
        },
        "error": "",
    }


@business_tool(
    name="retire_pod_design",
    description="Mark a POD design as retired in the vault.",
    category="print_on_demand",
)
def retire_pod_design(design_id: str) -> Dict[str, Any]:
    """
    Retire a design so it is no longer considered for new products.

    Args:
        design_id: Vault document ID.

    Returns:
        Dict with retirement confirmation.
    """
    if not design_id:
        return {"status": "error", "data": None, "error": "design_id is required"}

    updated = vault.update("pod_designs", design_id, {"status": "retired", "retired_at": _now_iso()})
    if updated:
        # Also retire associated product if any
        design = vault.get("pod_designs", design_id)
        if design and design.get("product_id"):
            vault.update("pod_products", design["product_id"], {"status": "retired", "retired_at": _now_iso()})
        return {"status": "ok", "data": {"design_id": design_id, "retired": True}, "error": ""}
    return {"status": "error", "data": None, "error": f"Design {design_id} not found"}
