"""
CryptoWeb3Agent — Autonomous business agent for NFTs, tokens, DeFi, and affiliate
programs in the Web3/crypto vertical.

Operates in simulation mode by default (no real blockchain keys).
All on-chain interactions are mocked with realistic data and structured for
live API integration later.
"""

import json
import random
from typing import Any, Dict, List, Optional

from core.business_tools.registry import business_tool, BusinessToolRegistry
from core.business_tools.vault import vault
from .base import BaseBusinessAgent, BusinessDecision


class CryptoWeb3Agent(BaseBusinessAgent):
    """
    Autonomous agent for crypto & Web3 monetization:
    - NFT collection design & metadata generation
    - Tokenomics creation for new tokens
    - DeFi yield farming strategy drafting
    - Affiliate campaign creation for crypto products

    Conservative risk posture: crypto volatility means high risk scores
    and lower auto-approval confidence thresholds.
    """

    # Collections persisted to the unified vault
    VAULT_COLLECTIONS = {
        "nft_collections",
        "tokenomics",
        "defi_strategies",
        "affiliate_links",
        "web3_campaigns",
    }

    def __init__(self, model_router, autonomy_tier: str = "AUTOPILOT", decision_callback=None):
        super().__init__(
            name="CryptoWeb3Agent",
            description="NFTs, tokens, DeFi yield, and crypto affiliate campaigns",
            model_router=model_router,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )
        # Ensure tools are loaded (idempotent import triggers registration)
        try:
            import core.business_tools.crypto_tools  # noqa: F401
        except Exception as e:
            print(f"[{self.name}] Warning: could not load crypto_tools: {e}")

    # ── Perception ────────────────────────────────────────────────────────────

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather signals from the vault and simulated market data.

        Checks:
        - Existing NFT collections, tokenomics docs, DeFi strategies
        - Simulated gas prices
        - Simulated market sentiment for major coins
        - Recent affiliate link performance
        """
        perception: Dict[str, Any] = {"agent": self.name, "timestamp": self._now_iso()}

        # 1. Vault inventory
        for collection in self.VAULT_COLLECTIONS:
            count = vault.count(collection)
            perception[f"{collection}_count"] = count
            if count > 0:
                # Fetch the most recent entry for context
                recent = vault.find(collection, limit=1)
                perception[f"latest_{collection}"] = recent[0] if recent else None

        # 2. Simulated gas prices
        gas_result = await self.tools.execute("get_gas_price_estimate")
        perception["gas_prices"] = gas_result.get("gas_prices") if gas_result.get("success") else None

        # 3. Simulated market sentiment for major assets
        sentiment_coins = ["BTC", "ETH", "SOL"]
        perception["market_sentiment"] = {}
        for coin in sentiment_coins:
            s = await self.tools.execute("analyze_market_sentiment", coin=coin)
            if s.get("success"):
                perception["market_sentiment"][coin] = s["sentiment"]

        # 4. Overall market temperature heuristic
        sentiment_scores = [
            perception["market_sentiment"][c]["sentiment_score"]
            for c in sentiment_coins
            if c in perception["market_sentiment"]
        ]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        perception["avg_sentiment"] = round(avg_sentiment, 3)
        perception["market_temperature"] = (
            "hot" if avg_sentiment > 0.4 else "cold" if avg_sentiment < -0.4 else "neutral"
        )

        return perception

    # ── Decision Making ───────────────────────────────────────────────────────

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Decide whether to act based on perceived signals.

        Possible actions:
        - design_nft_collection
        - create_tokenomics
        - draft_defi_strategy
        - launch_affiliate_campaign
        - generate_crypto_content
        - no_op (do nothing if conditions are unfavorable)

        Risk scoring is conservative: crypto volatility pushes risk_score
        upward so the agent rarely auto-approves high-capital actions.
        """
        system_prompt = """You are the CryptoWeb3Agent decision engine.
Given market perception data, decide the next best action.

Respond in strict JSON:
{
  "action": "design_nft_collection|create_tokenomics|draft_defi_strategy|launch_affiliate_campaign|generate_crypto_content|no_op",
  "rationale": "...",
  "confidence": 0.0-1.0,
  "risk_score": 0.0-1.0,
  "payload": {...}
}

Rules:
- If market_temperature is "cold", prefer content generation or low-risk affiliate campaigns.
- If gas prices are very high (fast > 50 gwei), avoid on-chain actions.
- Be conservative: default risk_score >= 0.5 for any token/NFT action.
- Only return no_op if there is genuinely nothing productive to do.
"""

        user_prompt = f"""Current perception:
{json.dumps(perception, indent=2, default=str)}

What should the CryptoWeb3Agent do next?
"""

        llm_response = await self.llm_decide(system_prompt, user_prompt)

        action = llm_response.get("action", "no_op")
        if action == "no_op" or action == "raw":
            return None

        confidence = float(llm_response.get("confidence", 0.5))
        risk_score = float(llm_response.get("risk_score", 0.75))

        # Enforce conservative crypto floor risk
        if action in ("design_nft_collection", "create_tokenomics"):
            risk_score = max(risk_score, 0.55)
        elif action == "draft_defi_strategy":
            risk_score = max(risk_score, 0.60)

        payload = llm_response.get("payload", {})

        # Derive rough revenue estimate
        revenue_map = {
            "design_nft_collection": 500.0,
            "create_tokenomics": 300.0,
            "draft_defi_strategy": 200.0,
            "launch_affiliate_campaign": 150.0,
            "generate_crypto_content": 100.0,
        }
        estimated_revenue = revenue_map.get(action, 0.0)

        decision = BusinessDecision(
            agent_name=self.name,
            decision_type=action,
            rationale=llm_response.get("rationale", "LLM-generated decision"),
            action_payload=payload,
            estimated_revenue_impact=estimated_revenue,
            risk_score=min(risk_score, 0.95),
            confidence=min(confidence, 1.0),
        )

        return decision

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute(self, decision: BusinessDecision):
        """
        Execute an approved decision using business tools.

        Routes:
        - design_nft_collection  → generate_nft_collection
        - create_tokenomics      → design_tokenomics
        - draft_defi_strategy    → research_defi_yield + save to vault
        - launch_affiliate_campaign → create_affiliate_tracking_link
        - generate_crypto_content → generate_crypto_content
        """
        action = decision.decision_type
        payload = decision.action_payload
        result: Dict[str, Any] = {}

        try:
            if action == "design_nft_collection":
                result = await self.tools.execute(
                    "generate_nft_collection",
                    name=payload.get("name", "Orbit Collection"),
                    theme=payload.get("theme", "Cyberpunk Universe"),
                    count=payload.get("count", 100),
                )

            elif action == "create_tokenomics":
                result = await self.tools.execute(
                    "design_tokenomics",
                    token_name=payload.get("token_name", "OrbitToken"),
                    use_case=payload.get("use_case", "utility"),
                    initial_supply=payload.get("initial_supply", 1_000_000_000),
                )

            elif action == "draft_defi_strategy":
                protocols = payload.get("protocols", ["aave", "lido"])
                yield_data: List[Dict[str, Any]] = []
                for protocol in protocols:
                    y = await self.tools.execute("research_defi_yield", protocol=protocol)
                    if y.get("success"):
                        yield_data.append(y["yield_data"])

                strategy_doc = {
                    "strategy_name": payload.get("strategy_name", "Conservative Yield Farm"),
                    "protocols": protocols,
                    "yield_data": yield_data,
                    "allocation_rules": payload.get(
                        "allocation_rules",
                        {
                            "max_single_protocol_pct": 0.40,
                            "rebalance_threshold_pct": 0.10,
                            "emergency_exit_apy_drop": 0.005,
                        },
                    ),
                    "risk_disclaimer": (
                        "DeFi strategies carry smart contract risk, impermanent loss, "
                        "and regulatory uncertainty. This is a simulation."
                    ),
                    "created_by": self.name,
                }
                doc_id = vault.insert("defi_strategies", strategy_doc)
                result = {"success": True, "vault_id": doc_id, "strategy": strategy_doc}

            elif action == "launch_affiliate_campaign":
                result = await self.tools.execute(
                    "create_affiliate_tracking_link",
                    campaign=payload.get("campaign", "web3_default"),
                    platform=payload.get("platform", "binance"),
                )

            elif action == "generate_crypto_content":
                result = await self.tools.execute(
                    "generate_crypto_content",
                    topic=payload.get("topic", "Crypto safety fundamentals"),
                    content_format=payload.get("format", "blog"),
                )

            else:
                result = {"error": f"Unknown action: {action}"}

            # Update decision record
            if result.get("success"):
                decision.status = "executed"
                decision.result_summary = json.dumps(result, indent=2, default=str)[:500]
                # Simulate actual revenue with high variance (crypto is volatile)
                simulated_actual = random.uniform(
                    0.0, decision.estimated_revenue_impact * 1.5
                )
                decision.actual_revenue = round(simulated_actual, 2)
            else:
                decision.status = "failed"
                decision.result_summary = result.get("error", "Execution failed")

        except Exception as e:
            decision.status = "failed"
            decision.result_summary = str(e)
            result = {"error": str(e)}

        self.log_decision(decision)
        return result

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
