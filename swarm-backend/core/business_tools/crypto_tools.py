"""
Crypto & Web3 Business Tools

Production-ready blockchain and DeFi integrations.
All API-dependent tools require LIVE_MODE=True and valid API keys.
"""

import asyncio
import json
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core import config
from core.business_tools.registry import business_tool
from core.business_tools.vault import vault
from core.tool_executor import _web_search


def _now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _random_hash() -> str:
    """Generate a random Ethereum-style address placeholder."""
    return "0x" + uuid.uuid4().hex[:40]


def _run_llm_sync(
    messages: list,
    model: str | None = None,
    temperature: float = 0.3,
) -> str:
    """Run an async LLM chat from a synchronous context."""
    from core.model_router import router

    try:
        return asyncio.run(router.chat(messages, model=model, temperature=temperature))
    except Exception as exc:
        raise RuntimeError(f"LLM call failed: {exc}")


# ── NFT Tools ────────────────────────────────────────────────────────────────


@business_tool(
    name="generate_nft_collection",
    description="Generate metadata JSON and trait maps for an NFT collection.",
    category="crypto_web3",
)
def generate_nft_collection(
    name: str,
    theme: str,
    count: int = 100,
) -> Dict[str, Any]:
    """
    Generate a complete NFT collection blueprint including ERC-721 metadata schema,
    trait distributions, and rarity tables ready for IPFS upload.

    Args:
        name: Collection name (e.g., "Cosmic Cubs").
        theme: Artistic theme / lore (e.g., "Space exploration meets cyberpunk").
        count: Number of items in the collection (default 100).

    Returns:
        Dict with collection metadata, trait definitions, and IPFS-ready preview.
    """
    try:
        if count < 1 or count > 10_000:
            return {"error": "Collection count must be between 1 and 10,000"}

        traits = {
            "background": ["Nebula", "Cyber City", "Void", "Galaxy"],
            "body": ["Fur", "Mech", "Hologram", "Crystal"],
            "eyes": ["Laser", "Sleepy", "Cyborg", "Star"],
            "accessory": ["None", "Jetpack", "Helmet", "Scarf"],
            "mood": ["Chill", "Aggressive", "Curious", "Mystic"],
        }

        # Deterministic trait assignment using hash for reproducibility
        def _assign_traits(token_id: int) -> Dict[str, str]:
            assigned: Dict[str, str] = {}
            for trait_key, trait_values in traits.items():
                idx = hash((name, theme, token_id, trait_key)) % len(trait_values)
                assigned[trait_key] = trait_values[idx]
            return assigned

        preview_items: List[Dict[str, Any]] = []
        for token_id in range(1, min(count + 1, 6)):  # Preview first 5
            item_traits = _assign_traits(token_id)
            rarity_score = sum(hash(v) % 100 for v in item_traits.values()) / 100
            preview_items.append(
                {
                    "token_id": token_id,
                    "name": f"{name} #{token_id}",
                    "description": f"{theme} — {name} #{token_id}",
                    "image": "ipfs://<PENDING_UPLOAD>",
                    "attributes": [
                        {"trait_type": k.title(), "value": v}
                        for k, v in item_traits.items()
                    ],
                    "rarity_score": round(rarity_score, 2),
                }
            )

        symbol = "".join([w[0] for w in name.split() if w]).upper()[:4] or "NFT"

        collection_doc = {
            "collection_name": name,
            "theme": theme,
            "total_supply": count,
            "symbol": symbol,
            "contract_address": None,  # To be filled after deployment
            "traits": traits,
            "preview": preview_items,
            "metadata_standard": "ERC-721",
            "created_at": _now_iso(),
            "mint_price_eth": None,  # To be configured by creator
            "royalty_bps": 500,  # 5% default
            "ipfs_ready": True,
        }

        doc_id = vault.insert("nft_collections", collection_doc)

        return {
            "success": True,
            "vault_id": doc_id,
            "collection": collection_doc,
            "note": (
                "Collection metadata generated. Upload images to IPFS and update "
                "image URIs before deployment."
            ),
        }
    except Exception as e:
        return {"error": str(e), "tool": "generate_nft_collection"}


# ── Tokenomics Tools ─────────────────────────────────────────────────────────


@business_tool(
    name="design_tokenomics",
    description="Design a tokenomics document for a new crypto token.",
    category="crypto_web3",
)
def design_tokenomics(
    token_name: str,
    use_case: str,
    initial_supply: int,
) -> Dict[str, Any]:
    """
    Create a comprehensive tokenomics design including distribution,
    vesting schedules, and utility mapping.

    Args:
        token_name: Human-readable token name.
        use_case: Primary utility (e.g., "governance", "payment", "utility").
        initial_supply: Total initial token supply (e.g., 1_000_000_000).

    Returns:
        Dict with tokenomics document and vault reference.
    """
    try:
        if initial_supply < 1:
            return {"error": "initial_supply must be >= 1"}

        symbol = "".join([w[0] for w in token_name.split() if w]).upper()[:5] or "TKN"

        allocation = {
            "community_rewards": 0.30,
            "team_advisors": 0.15,
            "ecosystem_growth": 0.25,
            "liquidity_pools": 0.15,
            "treasury": 0.10,
            "private_sale": 0.05,
        }

        vesting = {
            "team_advisors": {"cliff_months": 12, "vesting_months": 36},
            "private_sale": {"cliff_months": 6, "vesting_months": 18},
            "community_rewards": {"cliff_months": 0, "vesting_months": 48},
            "ecosystem_growth": {"cliff_months": 0, "vesting_months": 36},
        }

        distribution = {
            k: {
                "percentage": v,
                "tokens": int(initial_supply * v),
                "vesting": vesting.get(k, {"cliff_months": 0, "vesting_months": 0}),
            }
            for k, v in allocation.items()
        }

        use_case_lower = use_case.lower()
        if use_case_lower in ("payment", "utility"):
            burn = "transaction_fee_burn"
        elif use_case_lower in ("governance", "dao", "protocol"):
            burn = "buyback_burn"
        else:
            burn = "none"

        doc = {
            "token_name": token_name,
            "symbol": symbol,
            "use_case": use_case_lower,
            "initial_supply": initial_supply,
            "contract_type": "ERC-20",
            "contract_address": None,  # To be deployed
            "distribution": distribution,
            "burn_mechanism": burn,
            "governance": use_case_lower in ("governance", "dao", "protocol"),
            "staking_apr": None,  # To be set by protocol mechanics
            "created_at": _now_iso(),
            "risk_notes": [
                "Tokenomics design is theoretical; legal and audit review required before mainnet.",
                "Staking APR depends on actual protocol revenue and token emission schedule.",
            ],
        }

        doc_id = vault.insert("tokenomics", doc)

        return {
            "success": True,
            "vault_id": doc_id,
            "tokenomics": doc,
            "note": "Tokenomics design generated. Legal and smart-contract audit required before deployment.",
        }
    except Exception as e:
        return {"error": str(e), "tool": "design_tokenomics"}


# ── DeFi Yield Tools ─────────────────────────────────────────────────────────


@business_tool(
    name="research_defi_yield",
    description="Research current DeFi yield rates for a given protocol.",
    category="crypto_web3",
)
def research_defi_yield(
    protocol: str = "aave",
) -> Dict[str, Any]:
    """
    Fetch live yield rates and TVL for a DeFi protocol from DeFiLlama.

    Args:
        protocol: Protocol name (aave, compound, lido, curve, convex, uniswap).

    Returns:
        Dict with current APY, TVL, risk level, and chain info.

    Raises:
        ValueError: If LIVE_MODE is not enabled.
        RuntimeError: If the DeFiLlama API request fails or protocol is not found.
    """
    if not config.LIVE_MODE:
        raise ValueError("LIVE_MODE must be True to research real DeFi yields.")

    protocol = protocol.lower().strip()

    try:
        # Fetch yield pools from DeFiLlama
        req = urllib.request.Request(
            "https://yields.llama.fi/pools",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        pools = data.get("data", [])
        matched = [p for p in pools if protocol in p.get("project", "").lower()]

        if not matched:
            # Fallback: check protocols endpoint for TVL info
            req2 = urllib.request.Request(
                "https://api.llama.fi/protocols",
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                protocols_data = json.loads(resp2.read().decode("utf-8"))

            proto_info = next(
                (
                    p
                    for p in protocols_data
                    if protocol in p.get("slug", "").lower()
                    or protocol in p.get("name", "").lower()
                ),
                None,
            )
            if proto_info:
                tvl = proto_info.get("tvl", 0)
                result = {
                    "protocol": protocol,
                    "current_apy": None,
                    "current_apy_percent": "N/A",
                    "tvl_usd": tvl,
                    "risk_level": "unknown",
                    "impermanent_loss_risk": protocol
                    in ("uniswap", "curve", "sushiswap", "balancer", "pancakeswap"),
                    "timestamp": _now_iso(),
                    "data_source": "defillama.com/protocols",
                    "note": "Protocol found on DeFiLlama but no yield pool data available.",
                }
                return {"success": True, "yield_data": result}
            else:
                raise ValueError(f"Protocol '{protocol}' not found on DeFiLlama.")

        # Aggregate top pool by TVL
        top_pool = max(matched, key=lambda x: x.get("tvlUsd", 0))
        apy = top_pool.get("apy", 0)
        tvl = top_pool.get("tvlUsd", 0)

        if apy > 0.20:
            risk = "high"
        elif apy > 0.10:
            risk = "medium-high"
        elif apy > 0.05:
            risk = "medium"
        else:
            risk = "low"

        result = {
            "protocol": protocol,
            "current_apy": round(apy, 4),
            "current_apy_percent": f"{apy * 100:.2f}%",
            "tvl_usd": tvl,
            "risk_level": risk,
            "impermanent_loss_risk": protocol
            in ("uniswap", "curve", "sushiswap", "balancer", "pancakeswap"),
            "timestamp": _now_iso(),
            "data_source": "defillama.com/pools",
            "top_pool_symbol": top_pool.get("symbol", "N/A"),
            "chain": top_pool.get("chain", "N/A"),
        }
        return {"success": True, "yield_data": result}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"DeFiLlama API request failed: {e.code} {e.reason}")
    except Exception as e:
        raise RuntimeError(f"DeFiLlama yield research failed: {e}")


# ── Affiliate Tools ──────────────────────────────────────────────────────────


@business_tool(
    name="create_affiliate_tracking_link",
    description="Create an affiliate tracking link structure for crypto products.",
    category="crypto_web3",
)
def create_affiliate_tracking_link(
    campaign: str,
    platform: str = "binance",
) -> Dict[str, Any]:
    """
    Generate a real affiliate tracking link using configured referral codes.

    Args:
        campaign: Campaign identifier (e.g., "summer2025_yield").
        platform: Exchange or platform name (binance, coinbase, ledger, bybit, okx).

    Returns:
        Dict with tracking URL, referral code, and vault ID.

    Raises:
        ValueError: If no referral code is configured for the requested platform.
    """
    try:
        platform = platform.lower().strip()

        ref_map = {
            "binance": getattr(config, "BINANCE_REF", ""),
            "coinbase": getattr(config, "COINBASE_REF", ""),
            "ledger": getattr(config, "LEDGER_REF", ""),
            "bybit": getattr(config, "BYBIT_REF", ""),
            "okx": getattr(config, "OKX_REF", ""),
        }

        ref_code = ref_map.get(platform, "")
        if not ref_code:
            raise ValueError(
                f"No referral code configured for platform '{platform}'. "
                f"Set {platform.upper()}_REF in environment."
            )

        url_templates = {
            "binance": f"https://www.binance.com/en/register?ref={ref_code}",
            "coinbase": f"https://coinbase.com/join/{ref_code}",
            "ledger": f"https://shop.ledger.com/?r={ref_code}",
            "bybit": f"https://www.bybit.com/invite?ref={ref_code}",
            "okx": f"https://www.okx.com/join/{ref_code}",
        }

        tracking_url = url_templates.get(
            platform, f"https://{platform}.com/?ref={ref_code}"
        )

        doc = {
            "campaign": campaign,
            "platform": platform,
            "referral_code": ref_code,
            "tracking_url": tracking_url,
            "clicks": 0,
            "conversions": 0,
            "created_at": _now_iso(),
        }

        doc_id = vault.insert("affiliate_links", doc)

        return {
            "success": True,
            "vault_id": doc_id,
            "tracking": doc,
        }
    except Exception as e:
        return {"error": str(e), "tool": "create_affiliate_tracking_link"}


# ── Content Tools ────────────────────────────────────────────────────────────


@business_tool(
    name="generate_crypto_content",
    description="Generate educational or promotional crypto content.",
    category="crypto_web3",
)
def generate_crypto_content(
    topic: str,
    content_format: str = "blog",
) -> Dict[str, Any]:
    """
    Generate a draft piece of crypto content (blog, thread, newsletter, video_script).

    Args:
        topic: Content topic (e.g., "How to stake ETH safely").
        content_format: One of blog, thread, newsletter, video_script, landing_page.

    Returns:
        Dict with title, outline, body draft, and SEO tags.
    """
    try:
        fmt = content_format.lower().strip()
        allowed = {"blog", "thread", "newsletter", "video_script", "landing_page"}
        if fmt not in allowed:
            return {
                "error": f"Unsupported format '{content_format}'. Choose from {allowed}."
            }

        title = f"{topic.strip().title()}: A Complete Guide"
        outline = [
            "1. Introduction & Market Context",
            "2. Key Concepts Explained",
            "3. Step-by-Step Strategy",
            "4. Risk Considerations",
            "5. Conclusion & Call to Action",
        ]

        seo_tags = [
            topic.lower().replace(" ", "-"),
            "crypto",
            "web3",
            "defi",
            "blockchain",
        ]

        body_draft = f"""
# {title}

> **Disclaimer:** This content is for educational purposes only. Crypto assets are volatile and you may lose capital.

## 1. Introduction & Market Context
The crypto landscape continues to evolve rapidly. Understanding {topic} is essential for both newcomers and experienced participants.

## 2. Key Concepts Explained
- **Decentralization:** No single point of control.
- **Smart Contracts:** Self-executing code on the blockchain.
- **Yield:** Returns generated from DeFi protocols (rates vary by market conditions).

## 3. Step-by-Step Strategy
1. Research the protocol or asset thoroughly.
2. Start with a small allocation (< 5% of portfolio).
3. Use hardware wallets for self-custody.
4. Monitor gas fees and market conditions.

## 4. Risk Considerations
- Volatility: Prices can swing >20% in a day.
- Smart contract risk: Bugs can lead to loss of funds.
- Regulatory uncertainty: Rules change by jurisdiction.

## 5. Conclusion & Call to Action
Stay conservative, diversify, and never invest more than you can afford to lose.
""".strip()

        doc = {
            "title": title,
            "topic": topic,
            "format": fmt,
            "outline": outline,
            "body_draft": body_draft,
            "seo_tags": seo_tags,
            "word_count_approx": len(body_draft.split()),
            "created_at": _now_iso(),
        }

        doc_id = vault.insert("web3_campaigns", doc)

        return {
            "success": True,
            "vault_id": doc_id,
            "content": doc,
        }
    except Exception as e:
        return {"error": str(e), "tool": "generate_crypto_content"}


# ── Market Sentiment Tools ───────────────────────────────────────────────────


@business_tool(
    name="analyze_market_sentiment",
    description="Analyze market sentiment for a specific cryptocurrency.",
    category="crypto_web3",
)
def analyze_market_sentiment(
    coin: str,
) -> Dict[str, Any]:
    """
    Analyze real market sentiment for a given coin using web search and LLM.

    Args:
        coin: Ticker or name (BTC, ETH, SOL, etc.).

    Returns:
        Dict with sentiment score, trend, summary, and source URLs.

    Raises:
        RuntimeError: If web search or LLM analysis fails.
    """
    try:
        coin = coin.upper().strip()

        search_result = _web_search(
            f"{coin} crypto market sentiment news analysis", max_results=8
        )
        results = (
            search_result.get("data", {}).get("results", [])
            if search_result.get("status") == "ok"
            else []
        )

        if not results:
            raise RuntimeError(
                f"No web search results found for {coin} sentiment analysis."
            )

        context = "\n".join(
            [
                f"- {r.get('title', '')}: {r.get('url', '')}"
                for r in results
                if r.get("title")
            ]
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a crypto market analyst. Analyze the provided web search "
                    "results and output a JSON object with exactly these keys: "
                    "sentiment_score (float -1.0 to 1.0), trend (string: bullish, "
                    "bearish, or neutral), summary (string), key_drivers (list of strings). "
                    "Return ONLY valid JSON, no markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Analyze market sentiment for {coin} based on these recent web results:\n"
                    f"{context}\n\nProvide your analysis as JSON."
                ),
            },
        ]

        response = _run_llm_sync(messages, temperature=0.3)

        # Parse JSON from response
        json_str = response
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        analysis = json.loads(json_str.strip())

        result = {
            "coin": coin,
            "sentiment_score": float(analysis.get("sentiment_score", 0)),
            "trend": analysis.get("trend", "neutral"),
            "summary": analysis.get("summary", ""),
            "key_drivers": analysis.get("key_drivers", []),
            "sources": [r.get("url") for r in results if r.get("url")],
            "timestamp": _now_iso(),
            "data_source": "web_search + llm",
        }
        return {"success": True, "sentiment": result}
    except Exception as e:
        return {"error": str(e), "tool": "analyze_market_sentiment"}


# ── Gas Price Tools ──────────────────────────────────────────────────────────


@business_tool(
    name="get_gas_price_estimate",
    description="Get current Ethereum gas price estimates.",
    category="crypto_web3",
)
def get_gas_price_estimate() -> Dict[str, Any]:
    """
    Fetch live Ethereum gas price estimates from Etherscan across priority tiers.

    Returns:
        Dict with slow, standard, fast, and urgent gas prices in gwei plus
        estimated confirmation times.

    Raises:
        ValueError: If LIVE_MODE is disabled or ETHERSCAN_API_KEY is missing.
        RuntimeError: If the Etherscan API request fails.
    """
    if not config.LIVE_MODE:
        raise ValueError("LIVE_MODE must be True to fetch real gas prices.")

    api_key = getattr(config, "ETHERSCAN_API_KEY", "")
    if not api_key:
        raise ValueError("ETHERSCAN_API_KEY is not configured.")

    try:
        # Fetch current ETH price for USD estimates
        eth_price_url = (
            f"https://api.etherscan.io/api?module=stats&action=ethprice"
            f"&apikey={api_key}"
        )
        req_price = urllib.request.Request(
            eth_price_url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        eth_price_usd: Optional[float] = None
        with urllib.request.urlopen(req_price, timeout=15) as resp_price:
            price_data = json.loads(resp_price.read().decode("utf-8"))
            if price_data.get("status") == "1":
                eth_price_usd = float(price_data["result"]["ethusd"])

        # Fetch gas oracle
        url = (
            f"https://api.etherscan.io/api?module=gastracker&action=gasoracle"
            f"&apikey={api_key}"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("status") != "1":
            raise RuntimeError(
                f"Etherscan API error: {data.get('result', data.get('message', 'Unknown error'))}"
            )

        result_data = data.get("result", {})

        def _tier(gwei_str: str) -> Dict[str, Any]:
            gwei = float(gwei_str) if gwei_str else 0.0
            # Rough confirmation time heuristic
            est_time = int(15 / max(gwei / 10, 0.1)) if gwei > 0 else 300
            # USD cost for a simple 21,000 gas transfer
            cost_usd: Optional[float] = None
            if eth_price_usd:
                cost_eth = gwei * 21_000 / 1e9
                cost_usd = round(cost_eth * eth_price_usd, 4)
            return {
                "gwei": round(gwei, 2),
                "estimated_time_seconds": est_time,
                "cost_usd": cost_usd,
            }

        gas = {
            "network": "ethereum_mainnet",
            "currency": "gwei",
            "slow": _tier(result_data.get("SafeGasPrice", "0")),
            "standard": _tier(result_data.get("ProposeGasPrice", "0")),
            "fast": _tier(result_data.get("FastGasPrice", "0")),
            "urgent": _tier(
                str(float(result_data.get("FastGasPrice", "0")) * 1.2)
            ),
            "timestamp": _now_iso(),
            "data_source": "etherscan.io/gastracker",
            "eth_price_usd": eth_price_usd,
        }
        return {"success": True, "gas_prices": gas}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Etherscan gas API request failed: {e.code} {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Gas price fetch failed: {e}")
