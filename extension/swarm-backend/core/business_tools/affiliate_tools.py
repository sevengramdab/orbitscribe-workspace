"""
Affiliate marketing tools for the Monetization Swarm.

Provides web research, program registration, tracking-link generation,
content creation (reviews / comparisons), link insertion, and
commission-estimation utilities.
"""

import json
import os
import urllib.parse
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import config
from core.business_tools.registry import business_tool
from core.business_tools.vault import vault


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Create a URL-friendly slug from arbitrary text."""
    slug = text.lower().replace(" ", "-").replace("_", "-")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    slug = "".join(ch for ch in slug if ch in allowed)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _build_affiliate_url(program: str, landing_page: str) -> str:
    """
    Construct a real affiliate URL using ref codes from config.

    Supported programs: amazon, binance.
    """
    program = program.lower().strip()

    if program == "amazon":
        tag = config.AMAZON_ASSOCIATES_TAG
        if config.LIVE_MODE and not tag:
            raise ValueError("AMAZON_ASSOCIATES_TAG not configured in LIVE_MODE")
        base = landing_page.rstrip("/") if landing_page else "https://www.amazon.com"
        return f"{base}?tag={tag}" if tag else base

    if program == "binance":
        ref = config.BINANCE_REF
        if config.LIVE_MODE and not ref:
            raise ValueError("BINANCE_REF not configured in LIVE_MODE")
        base = landing_page.rstrip("/") if landing_page else "https://www.binance.com"
        return f"{base}?ref={ref}" if ref else base

    if config.LIVE_MODE:
        raise ValueError(
            f"Unknown affiliate program '{program}' in LIVE_MODE"
        )

    return landing_page or f"https://example.com/{program}"


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

@business_tool(
    name="research_affiliate_programs",
    description="Search the web for relevant affiliate programs in a given niche.",
    category="affiliate",
)
def research_affiliate_programs(niche: str) -> Dict[str, Any]:
    """
    Search DuckDuckGo for affiliate programs related to *niche*.

    Args:
        niche: The market niche to research (e.g. "software", "fitness").

    Returns:
        Dict with ``status``, ``message``, and a ``programs`` list.
    """
    try:
        import urllib.request
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover
        return {
            "status": "error",
            "message": f"Missing dependency: {exc}. Install beautifulsoup4.",
            "programs": [],
        }

    query = f"best affiliate programs {niche} 2024 2025"
    search_url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)

    try:
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Web search failed: {exc}",
            "programs": [],
        }

    programs: List[Dict[str, str]] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        for result in soup.select(".result__a")[:10]:
            title = result.get_text(strip=True)
            href = result.get("href", "")
            if title and href:
                programs.append(
                    {
                        "title": title,
                        "url": href,
                        "niche": niche,
                        "discovered_at": datetime.utcnow().isoformat(),
                    }
                )
    except Exception as exc:
        return {
            "status": "error",
            "message": f"HTML parsing failed: {exc}",
            "programs": [],
        }

    return {
        "status": "ok",
        "message": f"Found {len(programs)} potential affiliate programs for '{niche}'",
        "programs": programs,
    }


# ---------------------------------------------------------------------------
# Program lifecycle
# ---------------------------------------------------------------------------

@business_tool(
    name="join_affiliate_program",
    description="Save affiliate program details to the vault after joining.",
    category="affiliate",
)
def join_affiliate_program(
    program_name: str,
    url: str,
    commission_rate: Optional[float] = None,
    cookie_duration: Optional[int] = None,
    payout_threshold: Optional[float] = None,
    niche: Optional[str] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Register a newly-joined affiliate program in the unified vault.

    Args:
        program_name: Human-readable program name.
        url: Program homepage or application URL.
        commission_rate: Percentage commission (e.g. 15.0 for 15%).
        cookie_duration: Tracking cookie lifetime in days.
        payout_threshold: Minimum payout amount in USD.
        niche: Market category.
        notes: Free-form notes.

    Returns:
        Dict with ``status``, ``message``, and the generated ``program_id``.
    """
    doc: Dict[str, Any] = {
        "program_name": program_name,
        "url": url,
        "status": "joined",
        "joined_at": datetime.utcnow().isoformat(),
        "commission_rate": commission_rate,
        "cookie_duration": cookie_duration,
        "payout_threshold": payout_threshold,
        "niche": niche,
        "notes": notes,
    }
    doc_id = vault.insert("affiliate_programs", doc)
    return {
        "status": "ok",
        "message": f"Joined affiliate program '{program_name}'",
        "program_id": doc_id,
    }


# ---------------------------------------------------------------------------
# Tracking links
# ---------------------------------------------------------------------------

@business_tool(
    name="generate_tracking_link",
    description="Generate a tracking link for an affiliate program and save it to the vault.",
    category="affiliate",
)
def generate_tracking_link(
    program_id: str,
    landing_page: str,
    campaign: str,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create a tracking URL for an affiliate campaign using real ref codes from config.

    Args:
        program_id: Vault ID of the affiliate program.
        landing_page: Destination URL for the link.
        campaign: Campaign name for grouping analytics.
        tags: Optional list of descriptive tags.

    Returns:
        Dict with ``status``, ``link_id``, ``tracking_url``, etc.
    """
    program = vault.get("affiliate_programs", program_id)
    if not program:
        return {
            "status": "error",
            "message": f"Affiliate program '{program_id}' not found in vault.",
            "link_id": None,
        }

    program_name = program.get("program_name", "").lower()
    link_id = str(uuid.uuid4())[:8]
    safe_campaign = campaign.strip().replace(" ", "_").lower()

    if "amazon" in program_name:
        tag = config.AMAZON_ASSOCIATES_TAG
        if config.LIVE_MODE and not tag:
            raise ValueError("AMAZON_ASSOCIATES_TAG not configured in LIVE_MODE")
        base = landing_page.rstrip("/")
        tracking_url = (
            f"{base}?tag={tag}&linkId={link_id}"
            f"&camp={urllib.parse.quote(safe_campaign)}"
        )
    elif "binance" in program_name:
        ref = config.BINANCE_REF
        if config.LIVE_MODE and not ref:
            raise ValueError("BINANCE_REF not configured in LIVE_MODE")
        base = landing_page.rstrip("/")
        tracking_url = (
            f"{base}?ref={ref}&utm_campaign={urllib.parse.quote(safe_campaign)}"
        )
    else:
        if config.LIVE_MODE:
            raise ValueError(
                f"Program '{program_name}' has no configured affiliate URL in LIVE_MODE"
            )
        base = landing_page.rstrip("/")
        separator = "&" if "?" in base else "?"
        tracking_url = (
            f"{base}{separator}ref={link_id}"
            f"&campaign={urllib.parse.quote(campaign)}"
        )

    doc: Dict[str, Any] = {
        "link_id": link_id,
        "program_id": program_id,
        "program_name": program.get("program_name", "Unknown"),
        "landing_page": landing_page,
        "campaign": campaign,
        "tracking_url": tracking_url,
        "tracking_code": link_id,
        "clicks": 0,
        "conversions": 0,
        "estimated_revenue": 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "tags": tags or [],
    }
    vault_id = vault.insert("affiliate_links", doc, doc_id=link_id)
    return {
        "status": "ok",
        "message": f"Generated tracking link for campaign '{campaign}'",
        "link_id": link_id,
        "tracking_url": tracking_url,
        "vault_id": vault_id,
    }


# ---------------------------------------------------------------------------
# Content operations
# ---------------------------------------------------------------------------

@business_tool(
    name="insert_affiliate_links",
    description="Rewrite existing content to naturally include affiliate links.",
    category="affiliate",
)
def insert_affiliate_links(
    content_id: str,
    product_urls: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Update a content document in the vault with embedded affiliate links.

    Each item in *product_urls* should contain at minimum:
    ``anchor_text`` and ``url``. The first occurrence of *anchor_text* in the
    body is replaced with a tagged HTML anchor.

    Args:
        content_id: Vault document ID of the content piece.
        product_urls: List of ``{"anchor_text": "...", "url": "..."}`` mappings.

    Returns:
        Dict with ``status``, ``links_inserted``, and ``updated_content``.
    """
    content_doc = vault.get("affiliate_content", content_id)
    if not content_doc:
        # Fallback to a generic content collection
        content_doc = vault.get("content", content_id)

    if not content_doc:
        return {
            "status": "error",
            "message": f"Content '{content_id}' not found in vault.",
            "updated_content": None,
        }

    body = content_doc.get("body") or content_doc.get("content", "")
    if not body:
        return {
            "status": "error",
            "message": f"Content '{content_id}' has no body to update.",
            "updated_content": None,
        }

    updated_body = body
    links_inserted = 0
    for mapping in product_urls:
        anchor = mapping.get("anchor_text", "")
        url = mapping.get("url", "")
        if anchor and url and anchor in updated_body:
            updated_body = updated_body.replace(
                anchor,
                f'<a href="{url}" rel="nofollow sponsored">{anchor}</a>',
                1,
            )
            links_inserted += 1

    updates: Dict[str, Any] = {
        "body": updated_body,
        "affiliate_links": product_urls,
        "links_inserted": links_inserted,
        "updated_at": datetime.utcnow().isoformat(),
    }
    vault.update("affiliate_content", content_id, updates)
    return {
        "status": "ok",
        "message": f"Inserted {links_inserted} affiliate links into content '{content_id}'",
        "updated_content": updated_body,
        "links_inserted": links_inserted,
    }


@business_tool(
    name="generate_product_review",
    description="Generate a product review article, write it to disk, and save it to the vault.",
    category="affiliate",
)
def generate_product_review(
    product_name: str,
    features: List[str],
    program: str = "amazon",
    landing_page: str = "https://www.amazon.com",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a structured product review article ready for publication.

    Args:
        product_name: Name of the product being reviewed.
        features: Key features to highlight.
        program: Affiliate program key (amazon, binance, etc.).
        landing_page: Base landing page URL.
        title: Optional override for the article title.

    Returns:
        Dict with ``status``, ``content_id``, ``title``, ``filepath``, and a text ``preview``.
    """
    affiliate_link = _build_affiliate_url(program, landing_page)
    year = datetime.utcnow().year
    review_title = title or f"{product_name} Review: Is It Worth It in {year}?"

    slug = _slugify(review_title)
    content_dir = os.path.join(config.WORKSPACE_ROOT, "content", "affiliate")
    os.makedirs(content_dir, exist_ok=True)
    filepath = os.path.join(content_dir, f"{slug}.md")

    sections: List[str] = [
        f"# {review_title}\n",
        "## Introduction\n",
        (
            f"**{product_name}** has gained significant attention this year. "
            f"In this review we examine its real-world performance, break down the features that matter, "
            f"and help you decide whether it deserves a spot in your setup. "
            f"If you already know you want it, [you can grab it here]({affiliate_link}).\n"
        ),
        "## What We Tested\n",
    ]
    for feature in features:
        sections.append(f"- {feature}\n")

    sections.extend(
        [
            "\n## Pros and Cons\n",
            "### Pros\n",
        ]
    )
    for feature in features[:3]:
        sections.append(f"- {feature} delivers measurable value.\n")
    sections.append("\n### Cons\n")
    sections.append("- Individual results depend on your specific use case and environment.\n")
    sections.append("- Some users may need time to unlock the full feature set.\n")

    sections.extend(
        [
            "\n## Final Verdict\n",
            (
                f"**{product_name}** is a strong contender in its category. "
                f"The feature set is competitive, and the overall experience justifies the investment for most buyers. "
                f"[Get {product_name} →]({affiliate_link})\n"
            ),
            "\n---\n",
            "*Disclosure: This post contains affiliate links. We earn a commission when you purchase through these links, at no extra cost to you.*",
        ]
    )

    body = "\n".join(sections)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(body)

    doc: Dict[str, Any] = {
        "title": review_title,
        "product_name": product_name,
        "body": body,
        "affiliate_link": affiliate_link,
        "content_type": "review",
        "features": features,
        "published": False,
        "created_at": datetime.utcnow().isoformat(),
        "filepath": filepath,
    }
    doc_id = vault.insert("affiliate_content", doc)
    return {
        "status": "ok",
        "message": f"Generated review for '{product_name}'",
        "content_id": doc_id,
        "title": review_title,
        "filepath": filepath,
        "preview": body[:500],
    }


@business_tool(
    name="generate_comparison_post",
    description="Generate a comparison article, write it to disk, and save it to the vault.",
    category="affiliate",
)
def generate_comparison_post(
    product_a: str,
    product_b: str,
    programs: Dict[str, str],
    landing_pages: Optional[Dict[str, str]] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a structured product-comparison article.

    Args:
        product_a: First product name.
        product_b: Second product name.
        programs: Mapping of product names to affiliate program keys
            (e.g. ``{product_a: "amazon", product_b: "binance"}``).
        landing_pages: Optional mapping of product names to landing page URLs.
        title: Optional override for the article title.

    Returns:
        Dict with ``status``, ``content_id``, ``title``, ``filepath``, and a text ``preview``.
    """
    landing_pages = landing_pages or {}
    program_a = (
        programs.get(product_a)
        or programs.get("product_a", "amazon")
    )
    program_b = (
        programs.get(product_b)
        or programs.get("product_b", "amazon")
    )
    landing_a = (
        landing_pages.get(product_a)
        or landing_pages.get("product_a", "https://www.amazon.com")
    )
    landing_b = (
        landing_pages.get(product_b)
        or landing_pages.get("product_b", "https://www.amazon.com")
    )

    link_a = _build_affiliate_url(program_a, landing_a)
    link_b = _build_affiliate_url(program_b, landing_b)

    post_title = title or f"{product_a} vs {product_b}: Which One Should You Choose?"

    slug = _slugify(post_title)
    content_dir = os.path.join(config.WORKSPACE_ROOT, "content", "affiliate")
    os.makedirs(content_dir, exist_ok=True)
    filepath = os.path.join(content_dir, f"{slug}.md")

    sections: List[str] = [
        f"# {post_title}\n",
        "## Introduction\n",
        (
            f"**{product_a}** and **{product_b}** are two of the most discussed options right now. "
            f"Both solve the same core problem, yet they approach it with different priorities. "
            f"This comparison breaks down the differences so you can pick the one that fits your workflow.\n"
        ),
        "## Head-to-Head Comparison\n",
        f"| Criteria | {product_a} | {product_b} |\n",
        "|----------|-------------|-------------|\n",
        f"| Primary Strength | Proven reliability & ecosystem | Competitive feature set |\n",
        f"| Ideal User | Teams that need stability fast | Users who want granular control |\n",
        f"| Pricing | Check current price below | Check current price below |\n",
        f"\n## {product_a} Overview\n",
        f"[Learn more about {product_a} →]({link_a})\n",
        f"\n## {product_b} Overview\n",
        f"[Learn more about {product_b} →]({link_b})\n",
        "\n## Which Should You Pick?\n",
        f"- **{product_a}** is the better fit if you need something that works out of the box with minimal friction.\n",
        f"- **{product_b}** makes more sense if you need advanced options and do not mind a steeper setup curve.\n",
        "\n---\n",
        "*Disclosure: This post contains affiliate links. We earn a commission when you purchase through these links, at no extra cost to you.*",
    ]

    body = "\n".join(sections)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(body)

    doc: Dict[str, Any] = {
        "title": post_title,
        "product_a": product_a,
        "product_b": product_b,
        "body": body,
        "affiliate_links": {"product_a": link_a, "product_b": link_b},
        "content_type": "comparison",
        "published": False,
        "created_at": datetime.utcnow().isoformat(),
        "filepath": filepath,
    }
    doc_id = vault.insert("affiliate_content", doc)
    return {
        "status": "ok",
        "message": f"Generated comparison post '{product_a} vs {product_b}'",
        "content_id": doc_id,
        "title": post_title,
        "filepath": filepath,
        "preview": body[:500],
    }


# ---------------------------------------------------------------------------
# Analytics & commission tracking
# ---------------------------------------------------------------------------

@business_tool(
    name="track_commission_estimate",
    description="Calculate estimated earnings for a link and record it in the vault.",
    category="affiliate",
)
def track_commission_estimate(
    link_id: str,
    clicks: int,
    conversion_rate: float,
    commission: float,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Estimate commissions and update link-performance history.

    Args:
        link_id: Vault ID of the affiliate link.
        clicks: Number of clicks to account for.
        conversion_rate: Expected conversion rate (0.0 – 1.0).
        commission: Average commission per conversion in USD.
        notes: Optional context notes.

    Returns:
        Dict with ``status``, ``history_id``, and ``estimated_earnings``.
    """
    if clicks < 0 or conversion_rate < 0 or commission < 0:
        return {
            "status": "error",
            "message": "Negative values are not allowed for clicks, conversion_rate, or commission.",
            "estimated_earnings": 0.0,
        }

    estimated_earnings = clicks * conversion_rate * commission

    # Update the running tally on the affiliate link record
    link_doc = vault.get("affiliate_links", link_id)
    if link_doc:
        vault.update(
            "affiliate_links",
            link_id,
            {
                "clicks": link_doc.get("clicks", 0) + clicks,
                "estimated_revenue": link_doc.get("estimated_revenue", 0.0) + estimated_earnings,
                "last_tracked_at": datetime.utcnow().isoformat(),
            },
        )

    history_doc: Dict[str, Any] = {
        "link_id": link_id,
        "clicks": clicks,
        "conversion_rate": conversion_rate,
        "commission_per_sale": commission,
        "estimated_earnings": round(estimated_earnings, 2),
        "recorded_at": datetime.utcnow().isoformat(),
        "notes": notes,
    }
    history_id = vault.insert("commission_history", history_doc)

    return {
        "status": "ok",
        "message": f"Tracked commission estimate for link '{link_id}'",
        "history_id": history_id,
        "estimated_earnings": round(estimated_earnings, 2),
    }


@business_tool(
    name="get_top_performing_links",
    description="Query the vault for the best-performing affiliate links by estimated revenue.",
    category="affiliate",
)
def get_top_performing_links(limit: int = 10) -> Dict[str, Any]:
    """
    Return the highest-earning affiliate links from the vault.

    Args:
        limit: Maximum number of links to return.

    Returns:
        Dict with ``status``, ``message``, and a ``links`` list.
    """
    links = vault.find("affiliate_links")
    if not links:
        return {
            "status": "ok",
            "message": "No affiliate links found in vault.",
            "links": [],
        }

    sorted_links = sorted(
        links,
        key=lambda x: x.get("estimated_revenue", 0),
        reverse=True,
    )[:limit]

    return {
        "status": "ok",
        "message": f"Retrieved top {len(sorted_links)} performing links",
        "links": [
            {
                "link_id": link.get("link_id"),
                "program_name": link.get("program_name"),
                "campaign": link.get("campaign"),
                "tracking_url": link.get("tracking_url"),
                "clicks": link.get("clicks", 0),
                "estimated_revenue": link.get("estimated_revenue", 0.0),
            }
            for link in sorted_links
        ],
    }
