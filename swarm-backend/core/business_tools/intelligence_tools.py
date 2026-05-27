"""
Intelligence Tools for the MarketIntelligenceAgent.

Provides competitor monitoring, trend tracking, review analysis, market gap
detection, pricing recommendations, and inter-agent signalling via the
unified business vault.
"""

import re
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import config
from core.tool_executor import _web_search

from .registry import business_tool
from .vault import vault


# ── Constants ────────────────────────────────────────────────────────────────

_REVIEW_SENTIMENT_KEYWORDS = {
    "positive": [
        "love", "great", "excellent", "amazing", "perfect", "recommend",
        "awesome", "fantastic", "best", "happy", "satisfied", "good",
    ],
    "negative": [
        "hate", "terrible", "awful", "worst", "bad", "disappointed",
        "poor", "broken", "defective", "waste", "refund", "return",
    ],
}


# ── Helper utilities ─────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _extract_price_from_html(html: str) -> Optional[float]:
    """Best-effort price extraction from raw HTML."""
    # Look for common price patterns: $XX.XX, USD XX.XX, etc.
    patterns = [
        r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2}))',
        r'price["\']?\s*[:=]\s*["\']?\$?([0-9]+(?:\.[0-9]{2})?)',
        r'"price":\s*([0-9]+(?:\.[0-9]{2})?)',
        r'([0-9]+\.[0-9]{2})\s*(?:USD|usd|USD\$|\$)',
    ]
    for pat in patterns:
        matches = re.findall(pat, html)
        for m in matches:
            try:
                val = float(m.replace(",", ""))
                if 1.0 <= val <= 50000.0:
                    return val
            except ValueError:
                continue
    return None


def _fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch raw HTML from a URL with minimal headers."""
    try:
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


# ── Business Tools ───────────────────────────────────────────────────────────


@business_tool(
    name="monitor_competitor_price",
    description="Scrape the current price for a competitor product URL.",
    category="intelligence",
)
def monitor_competitor_price(product_url: str) -> Dict[str, Any]:
    """
    Monitor the price of a competitor product.

    Attempts a live scrape of *product_url*.  In LIVE_MODE an exception is
    raised if the site is unreachable or does not contain a parseable price.

    Args:
        product_url: Full URL of the competitor product page.

    Returns:
        Dict with keys: url, price, currency, scraped_at, source (live|error),
        and error (empty string on success).
    """
    if not product_url or not product_url.startswith("http"):
        return {
            "url": product_url,
            "price": None,
            "currency": "USD",
            "scraped_at": _now_iso(),
            "source": "error",
            "error": "Invalid or missing URL.",
        }

    html = _fetch_url(product_url)
    if html is not None:
        price = _extract_price_from_html(html)
        if price is not None:
            doc = {
                "url": product_url,
                "price": price,
                "currency": "USD",
                "scraped_at": _now_iso(),
                "source": "live",
                "error": "",
            }
            vault.insert("price_history", doc)
            return doc

    if config.LIVE_MODE:
        raise Exception(f"Live scrape failed for {product_url}; could not extract price.")

    doc = {
        "url": product_url,
        "price": None,
        "currency": "USD",
        "scraped_at": _now_iso(),
        "source": "error",
        "error": "Live scrape failed; could not extract price.",
    }
    vault.insert("price_history", doc)
    return doc


@business_tool(
    name="analyze_reviews",
    description="Summarise customer sentiment from reviews for a product URL.",
    category="intelligence",
)
def analyze_reviews(product_url: str) -> Dict[str, Any]:
    """
    Analyze customer reviews for a given product.

    In production this would scrape review widgets or API endpoints.
    In LIVE_MODE an exception is raised when scraping is impossible.

    Args:
        product_url: URL of the product whose reviews should be analysed.

    Returns:
        Dict containing sentiment_score (-1.0 to 1.0), summary,
        top_positive themes, top_negative themes, and analysed_at.
    """
    if not product_url or not product_url.startswith("http"):
        return {
            "url": product_url,
            "sentiment_score": 0.0,
            "summary": "Invalid URL provided.",
            "top_positive": [],
            "top_negative": [],
            "review_count": 0,
            "analysed_at": _now_iso(),
            "source": "error",
        }

    html = _fetch_url(product_url)
    if html:
        text = re.sub(r"<[^>]+>", " ", html).lower()
        pos_hits = sum(text.count(w) for w in _REVIEW_SENTIMENT_KEYWORDS["positive"])
        neg_hits = sum(text.count(w) for w in _REVIEW_SENTIMENT_KEYWORDS["negative"])
        total = pos_hits + neg_hits
        if total > 0:
            score = round((pos_hits - neg_hits) / max(total, 1), 3)
            summary = (
                f"Detected {pos_hits} positive and {neg_hits} negative sentiment markers "
                f"in page text (estimated score {score})."
            )
            doc = {
                "url": product_url,
                "sentiment_score": score,
                "summary": summary,
                "top_positive": _REVIEW_SENTIMENT_KEYWORDS["positive"][:3] if pos_hits else [],
                "top_negative": _REVIEW_SENTIMENT_KEYWORDS["negative"][:3] if neg_hits else [],
                "review_count": total,
                "analysed_at": _now_iso(),
                "source": "live_heuristic",
            }
            vault.insert("review_analysis", doc)
            return doc

    if config.LIVE_MODE:
        raise Exception(f"No reviews found or parsing failed for {product_url}.")

    doc = {
        "url": product_url,
        "sentiment_score": 0.0,
        "summary": "No reviews found or parsing failed.",
        "top_positive": [],
        "top_negative": [],
        "review_count": 0,
        "analysed_at": _now_iso(),
        "source": "error",
    }
    vault.insert("review_analysis", doc)
    return doc


@business_tool(
    name="track_trend",
    description="Perform a web-search trend analysis for a keyword over time.",
    category="intelligence",
)
def track_trend(keyword: str) -> Dict[str, Any]:
    """
    Track market trend data for a keyword.

    Uses DuckDuckGo web search to gather recent result titles / snippets and
    derives a simple momentum score.  In a full production deployment this
    would integrate Google Trends or a similar API.  In LIVE_MODE an
    exception is raised when the search yields no results.

    Args:
        keyword: The keyword or phrase to trend-track (e.g. "wireless earbuds").

    Returns:
        Dict with keyword, momentum_score (0-100), result_count, top_sources,
        and tracked_at.
    """
    if not keyword or not keyword.strip():
        return {
            "keyword": keyword,
            "momentum_score": 0,
            "result_count": 0,
            "top_sources": [],
            "summary": "Empty keyword provided.",
            "tracked_at": _now_iso(),
            "source": "error",
        }

    search_result = _web_search(f"{keyword} market trend 2024 2025", max_results=8)
    results = search_result.get("data", {}).get("results", []) if search_result.get("status") == "ok" else []

    if results:
        momentum = min(100, max(10, len(results) * 10))
        sources = [r.get("url", "") for r in results[:5] if r.get("url")]
        summary = f"Found {len(results)} recent web results for '{keyword}'. Momentum estimated at {momentum}."
        doc = {
            "keyword": keyword,
            "momentum_score": momentum,
            "result_count": len(results),
            "top_sources": sources,
            "summary": summary,
            "tracked_at": _now_iso(),
            "source": "web_search",
        }
    else:
        if config.LIVE_MODE:
            raise Exception(f"Web search yielded zero results for '{keyword}'.")
        doc = {
            "keyword": keyword,
            "momentum_score": 0,
            "result_count": 0,
            "top_sources": [],
            "summary": f"Web search yielded zero results for '{keyword}'.",
            "tracked_at": _now_iso(),
            "source": "error",
        }

    vault.insert("trend_reports", doc)
    return doc


@business_tool(
    name="detect_market_gap",
    description="Identify underserved sub-niches inside a broader niche via web search.",
    category="intelligence",
)
def detect_market_gap(niche: str) -> Dict[str, Any]:
    """
    Detect potential market gaps inside a given niche.

    Searches for underserved sub-niches, low-competition angles, and
    unmet customer needs.  In LIVE_MODE an exception is raised when the
    web search fails.

    Args:
        niche: The broad niche to investigate (e.g. "pet accessories").

    Returns:
        Dict with niche, gap_score (0-100), opportunities list, threats list,
        and detected_at.
    """
    if not niche or not niche.strip():
        return {
            "niche": niche,
            "gap_score": 0,
            "opportunities": [],
            "threats": [],
            "summary": "Empty niche provided.",
            "detected_at": _now_iso(),
            "source": "error",
        }

    queries = [
        f"underserved sub niches in {niche}",
        f"unmet needs {niche} 2024",
        f"low competition {niche} opportunities",
    ]

    all_results: List[Dict[str, str]] = []
    for q in queries:
        try:
            sr = _web_search(q, max_results=5)
            if sr.get("status") == "ok" and sr.get("data"):
                all_results.extend(sr["data"].get("results", []))
        except Exception:
            continue

    if all_results:
        titles = " ".join(r.get("title", "") for r in all_results)
        opportunity_keywords = ["niche", "underserved", "gap", "opportunity", "untapped", "emerging"]
        threat_keywords = ["saturated", "competition", "decline", "oversupply", "regulation"]

        opp_score = sum(1 for k in opportunity_keywords if k.lower() in titles.lower())
        threat_score = sum(1 for k in threat_keywords if k.lower() in titles.lower())

        opportunities = list({r["title"] for r in all_results if any(k in r.get("title", "").lower() for k in opportunity_keywords)})[:5]
        threats = list({r["title"] for r in all_results if any(k in r.get("title", "").lower() for k in threat_keywords)})[:3]

        if not opportunities:
            opportunities = [r["title"] for r in all_results[:3]]

        gap_score = min(100, max(0, 50 + opp_score * 8 - threat_score * 8))
        doc = {
            "niche": niche,
            "gap_score": gap_score,
            "opportunities": opportunities,
            "threats": threats,
            "summary": f"Analysed {len(all_results)} search results for '{niche}'. Gap score {gap_score}.",
            "detected_at": _now_iso(),
            "source": "web_search",
        }
    else:
        if config.LIVE_MODE:
            raise Exception(f"Web search failed for niche '{niche}'; no results found.")
        doc = {
            "niche": niche,
            "gap_score": 0,
            "opportunities": [],
            "threats": [],
            "summary": f"No search results for '{niche}'.",
            "detected_at": _now_iso(),
            "source": "error",
        }

    vault.insert("competitor_intel", doc)
    return doc


@business_tool(
    name="generate_pricing_recommendation",
    description="Generate a dynamic pricing suggestion for a product based on target margin and historical data.",
    category="intelligence",
)
def generate_pricing_recommendation(product_id: str, target_margin: float) -> Dict[str, Any]:
    """
    Generate a pricing recommendation for a product.

    Queries the vault *price_history* for competitor prices linked to the
    product and suggests an optimal price point that hits the desired margin.
    Returns an 'insufficient data' message when no price history is available.

    Args:
        product_id: Internal identifier for the product.
        target_margin: Desired profit margin as a decimal (e.g. 0.35 for 35%).

    Returns:
        Dict with product_id, recommended_price, target_margin, competitor_avg,
        rationale, and generated_at.
    """
    if not product_id:
        return {
            "product_id": product_id,
            "recommended_price": None,
            "target_margin": target_margin,
            "competitor_avg": None,
            "rationale": "Missing product_id.",
            "generated_at": _now_iso(),
            "source": "error",
        }

    try:
        prices = [
            doc["price"]
            for doc in vault.find("price_history", limit=200)
            if isinstance(doc.get("price"), (int, float))
        ]
        competitor_avg = round(sum(prices) / len(prices), 2) if prices else None
    except Exception:
        competitor_avg = None

    if competitor_avg is not None and target_margin > 0:
        typical_margin = max(0.05, min(0.95, target_margin))
        estimated_cogs = competitor_avg * (1 - typical_margin)
        recommended = round(estimated_cogs / (1 - target_margin), 2)
        recommended = round(min(competitor_avg * 1.3, max(competitor_avg * 0.7, recommended)), 2)
        rationale = (
            f"Competitor average is ${competitor_avg}. To hit a {target_margin:.0%} margin "
            f"(est. COGS ${round(estimated_cogs, 2)}), recommend ${recommended}."
        )
        source = "dynamic_model"
    else:
        recommended = None
        rationale = "Insufficient data to generate a pricing recommendation."
        source = "insufficient_data"

    doc = {
        "product_id": product_id,
        "recommended_price": recommended,
        "target_margin": target_margin,
        "competitor_avg": competitor_avg,
        "rationale": rationale,
        "generated_at": _now_iso(),
        "source": source,
    }
    vault.insert("competitor_intel", doc)
    return doc


@business_tool(
    name="create_market_signal",
    description="Persist a market signal in the vault for other agents to consume.",
    category="intelligence",
)
def create_market_signal(
    signal_type: str,
    urgency: str,
    message: str,
    target_agents: List[str],
) -> Dict[str, Any]:
    """
    Create a market signal that other swarm agents can read and act upon.

    Signals are stored in the unified vault under the *market_signals*
    collection.  Agents should poll ``get_active_signals`` to consume them.

    Args:
        signal_type: Category, e.g. 'price_alert', 'new_entrant', 'trend_shift'.
        urgency: 'low', 'medium', 'high', or 'critical'.
        message: Human-readable signal description.
        target_agents: List of agent names that should react to this signal.

    Returns:
        Dict with signal_id, status, and the stored document.
    """
    if not signal_type or not message:
        return {
            "signal_id": None,
            "status": "error",
            "error": "signal_type and message are required.",
        }

    doc = {
        "signal_type": signal_type,
        "urgency": urgency.lower(),
        "message": message,
        "target_agents": list(target_agents),
        "read_by": [],
        "created_at": _now_iso(),
    }
    signal_id = vault.insert("market_signals", doc)
    return {
        "signal_id": signal_id,
        "status": "created",
        "signal": doc,
    }


@business_tool(
    name="get_active_signals",
    description="Retrieve unread market signals from the vault, optionally filtered by agent.",
    category="intelligence",
)
def get_active_signals(agent_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch active (unread) market signals from the vault.

    Args:
        agent_name: If provided, only return signals where this agent is in
            *target_agents* and has not yet read the signal.

    Returns:
        Dict with count and list of matching signals.
    """
    try:
        all_signals = vault.find("market_signals", limit=500)
    except Exception as exc:
        return {"count": 0, "signals": [], "error": str(exc)}

    def _is_active(sig: Dict[str, Any]) -> bool:
        if agent_name:
            targets = sig.get("target_agents", [])
            read_by = sig.get("read_by", [])
            return agent_name in targets and agent_name not in read_by
        targets = sig.get("target_agents", [])
        read_by = sig.get("read_by", [])
        return not targets or any(t not in read_by for t in targets)

    active = [s for s in all_signals if _is_active(s)]
    return {"count": len(active), "signals": active, "error": ""}
