"""
AssetFactoryAgent — autonomous digital asset creation and monetization agent.

Perceives market demand via the unified vault, decides which digital assets
(ebooks, prompt packs, code templates, Notion templates, etc.) to create,
generates them via LLM-powered tools, packages them for sale, and tracks
revenue per asset type.
"""

import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.business_tools.vault import vault
from agents.business.base import BaseBusinessAgent, BusinessDecision


class AssetFactoryAgent(BaseBusinessAgent):
    """
    Autonomous agent that creates digital assets based on market demand and trends.

    Vault collections used:
        - assets: Completed and in-progress assets.
        - asset_requests: Incoming requests for specific assets.
        - asset_sales: Listing intents and confirmed sales.
        - creative_briefs: Briefs for assets requiring external APIs (image/video/music).
    """

    COLLECTION_ASSETS = "assets"
    COLLECTION_REQUESTS = "asset_requests"
    COLLECTION_SALES = "asset_sales"
    COLLECTION_BRIEFS = "creative_briefs"

    def __init__(
        self,
        llm_client=None,
        model_router=None,
        autonomy_tier: str = "AUTOPILOT",
        decision_callback=None,
    ):
        # Initialize custom fields BEFORE super().__init__() because it calls _load_vault()
        self.asset_type_revenue: Dict[str, float] = {}
        self.pending_briefs: List[str] = []
        client = llm_client or model_router
        super().__init__(
            name="AssetFactory",
            description="Autonomous digital asset creation, packaging, and listing agent.",
            llm_client=client,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )

    # ── Vault persistence overrides ───────────────────────────────────────

    def _load_vault(self):
        """Load agent state including asset-type revenue tracking."""
        super()._load_vault()
        if os.path.exists(self.vault_path):
            try:
                with open(self.vault_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.asset_type_revenue = data.get("asset_type_revenue", {})
                self.pending_briefs = data.get("pending_briefs", [])
            except Exception:
                pass

    def _save_vault(self):
        """Persist agent state with asset-type revenue breakdown."""
        os.makedirs(os.path.dirname(self.vault_path), exist_ok=True)
        data = {
            "agent_name": self.name,
            "updated_at": datetime.utcnow().isoformat(),
            "ledger": asdict(self.ledger),
            "decisions": [asdict(d) for d in self.decisions[-500:]],
            "asset_type_revenue": self.asset_type_revenue,
            "pending_briefs": self.pending_briefs,
        }
        with open(self.vault_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # ── Perception ────────────────────────────────────────────────────────

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather market signals from the vault and external trends.

        Checks:
        - Pending asset requests
        - Existing asset catalog and sales performance
        - Trending niches via LLM
        - Pending creative briefs (image/video/music awaiting external APIs)

        Returns:
            Perception dictionary with market signals.
        """
        # Pending requests
        requests = vault.find(self.COLLECTION_REQUESTS, limit=50)
        pending_requests = [r for r in requests if r.get("status") == "pending"]

        # Asset catalog
        assets = vault.find(self.COLLECTION_ASSETS, limit=200)
        sales = vault.find(self.COLLECTION_SALES, limit=200)

        # Compute revenue by asset type
        revenue_by_type: Dict[str, float] = {}
        for sale in sales:
            asset_id = sale.get("asset_id")
            if not asset_id:
                continue
            asset = vault.get(self.COLLECTION_ASSETS, asset_id)
            if asset:
                a_type = asset.get("asset_type", "unknown")
                revenue_by_type[a_type] = revenue_by_type.get(a_type, 0.0) + float(
                    sale.get("price", 0.0)
                )

        top_selling = sorted(
            revenue_by_type.items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Trending niches
        trends_result = await self.tools.execute("get_trending_asset_niches")
        trending_niches: List[Dict[str, Any]] = []
        if isinstance(trends_result, dict) and "niches" in trends_result:
            trending_niches = trends_result["niches"]

        # Pending briefs
        briefs = vault.find(self.COLLECTION_BRIEFS, limit=20)
        pending_briefs = [b for b in briefs if b.get("status") == "pending"]

        return {
            "pending_requests": pending_requests,
            "total_assets": len(assets),
            "total_sales": len(sales),
            "revenue_by_type": revenue_by_type,
            "top_selling_types": top_selling,
            "trending_niches": trending_niches,
            "pending_briefs": pending_briefs,
            "agent_asset_type_revenue": self.asset_type_revenue,
        }

    # ── Decision ──────────────────────────────────────────────────────────

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Decide what digital asset to create next.

        Prioritizes:
        1. Direct pending requests
        2. Top-selling asset types
        3. Trending niches

        Args:
            perception: Output from perceive().

        Returns:
            BusinessDecision or None if no action is warranted.
        """
        pending_requests = perception.get("pending_requests", [])
        top_selling = perception.get("top_selling_types", [])
        trending_niches = perception.get("trending_niches", [])
        pending_briefs = perception.get("pending_briefs", [])

        system_prompt = (
            "You are the strategic decision engine for an autonomous Asset Factory. "
            "Given market signals, decide the next digital asset to create. "
            "Respond ONLY with valid JSON matching this schema:\n"
            "{\n"
            '  "decision": "create_asset|fulfill_request|create_brief|noop",\n'
            '  "asset_type": "ebook|prompt_pack|code_template|notion_template|image|video|music",\n'
            '  "topic_or_purpose": "string",\n'
            '  "target_platform": "gumroad|etsy|creative_market|self",\n'
            '  "price": 0.0,\n'
            '  "rationale": "string",\n'
            '  "confidence": 0.0,\n'
            '  "risk_score": 0.0\n'
            "}"
        )

        user_prompt = (
            f"Pending asset requests: {len(pending_requests)}\n"
            f"Top-selling asset types: {top_selling}\n"
            f"Trending niches: {[n.get('name') for n in trending_niches[:10]]}\n"
            f"Pending creative briefs awaiting external APIs: {len(pending_briefs)}\n\n"
            "What should the Asset Factory create next?"
        )

        raw_decision = await self.llm_decide(system_prompt, user_prompt)
        if not isinstance(raw_decision, dict):
            return None

        decision_type = raw_decision.get("decision", "noop")
        if decision_type == "noop":
            return None

        asset_type = raw_decision.get("asset_type", "ebook")
        topic = raw_decision.get("topic_or_purpose", "Untitled Asset")
        platform = raw_decision.get("target_platform", "self")
        price = float(raw_decision.get("price", 9.99))
        confidence = float(raw_decision.get("confidence", 0.5))
        risk_score = float(raw_decision.get("risk_score", 0.5))
        rationale = raw_decision.get("rationale", "No rationale provided.")

        # Link to a request if applicable
        linked_request_id: Optional[str] = None
        if pending_requests and decision_type == "fulfill_request":
            linked_request_id = pending_requests[0].get("_id")

        payload: Dict[str, Any] = {
            "asset_type": asset_type,
            "topic": topic,
            "platform": platform,
            "price": price,
            "linked_request_id": linked_request_id,
        }

        # Asset-type-specific parameters for tool execution
        if asset_type == "ebook":
            payload["chapters"] = 5
        elif asset_type == "prompt_pack":
            payload["count"] = 10
        elif asset_type == "code_template":
            payload["features"] = ["auth", "database", "api"]
        elif asset_type == "notion_template":
            payload["purpose"] = topic

        decision = BusinessDecision(
            agent_name=self.name,
            decision_type=decision_type,
            rationale=rationale,
            action_payload=payload,
            estimated_revenue_impact=price * 0.3,
            risk_score=risk_score,
            confidence=confidence,
        )
        return decision

    # ── Execution ─────────────────────────────────────────────────────────

    async def execute(self, decision: BusinessDecision):
        """
        Execute the approved decision: generate, package, save, and optionally list.

        Args:
            decision: Approved BusinessDecision with action_payload.
        """
        payload = decision.action_payload
        asset_type = payload.get("asset_type", "ebook")
        topic = payload.get("topic", "Untitled")
        platform = payload.get("platform", "self")
        price = payload.get("price", 9.99)

        asset_doc: Dict[str, Any] = {
            "asset_type": asset_type,
            "topic": topic,
            "status": "generating",
            "platform": platform,
            "price": price,
            "decision_id": decision.decision_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        asset_id = vault.insert(self.COLLECTION_ASSETS, asset_doc)
        asset_doc["_id"] = asset_id

        generated_files: List[Dict[str, Any]] = []
        tool_result: Dict[str, Any] = {}

        try:
            if asset_type == "ebook":
                outline_res = await self.tools.execute(
                    "generate_ebook_outline",
                    topic=topic,
                    chapters=payload.get("chapters", 5),
                )
                if isinstance(outline_res, dict) and "error" in outline_res:
                    raise RuntimeError(f"Outline failed: {outline_res['error']}")

                content_res = await self.tools.execute(
                    "generate_ebook_content",
                    outline=outline_res.get("outline", {}),
                )
                if isinstance(content_res, dict) and "error" in content_res:
                    raise RuntimeError(f"Content failed: {content_res['error']}")

                generated_files = [
                    {
                        "filename": "outline.json",
                        "content": json.dumps(
                            outline_res.get("outline", {}), indent=2
                        ),
                    },
                    {
                        "filename": "ebook.md",
                        "content": content_res.get("content", ""),
                    },
                ]
                asset_doc["outline"] = outline_res.get("outline", {})
                tool_result = content_res

            elif asset_type == "prompt_pack":
                result = await self.tools.execute(
                    "generate_prompt_pack",
                    niche=topic,
                    count=payload.get("count", 10),
                )
                if isinstance(result, dict) and "error" in result:
                    raise RuntimeError(f"Prompt pack failed: {result['error']}")

                generated_files = [
                    {
                        "filename": "prompts.json",
                        "content": json.dumps(result.get("prompts", []), indent=2),
                    },
                    {
                        "filename": "README.md",
                        "content": result.get("readme", ""),
                    },
                ]
                tool_result = result

            elif asset_type == "code_template":
                result = await self.tools.execute(
                    "generate_code_template",
                    project_type=topic,
                    features=payload.get("features", []),
                )
                if isinstance(result, dict) and "error" in result:
                    raise RuntimeError(f"Code template failed: {result['error']}")

                generated_files = [
                    {
                        "filename": "README.md",
                        "content": result.get("readme", ""),
                    },
                    {
                        "filename": "main.py",
                        "content": result.get("code", ""),
                    },
                    {
                        "filename": "requirements.txt",
                        "content": result.get("requirements", ""),
                    },
                ]
                tool_result = result

            elif asset_type == "notion_template":
                result = await self.tools.execute(
                    "generate_notion_template",
                    purpose=topic,
                )
                if isinstance(result, dict) and "error" in result:
                    raise RuntimeError(f"Notion template failed: {result['error']}")

                generated_files = [
                    {
                        "filename": "template.md",
                        "content": result.get("markdown", ""),
                    },
                    {
                        "filename": "guide.md",
                        "content": result.get("guide", ""),
                    },
                ]
                tool_result = result

            else:
                # Image, video, music — queue a creative brief for external generation
                brief_id = vault.insert(
                    self.COLLECTION_BRIEFS,
                    {
                        "asset_type": asset_type,
                        "topic": topic,
                        "status": "pending",
                        "decision_id": decision.decision_id,
                        "platform": platform,
                        "price": price,
                    },
                )
                self.pending_briefs.append(brief_id)
                asset_doc["creative_brief_id"] = brief_id
                asset_doc["status"] = "pending_external_generation"

            # Package generated files
            if generated_files:
                package_res = await self.tools.execute(
                    "package_asset",
                    asset_id=asset_id,
                    files=generated_files,
                )
                asset_doc["package"] = package_res
                if isinstance(package_res, dict) and "error" in package_res:
                    raise RuntimeError(f"Packaging failed: {package_res['error']}")

            # Update linked request
            linked_request_id = payload.get("linked_request_id")
            if linked_request_id:
                vault.update(
                    self.COLLECTION_REQUESTS,
                    linked_request_id,
                    {
                        "status": "fulfilled",
                        "fulfilled_asset_id": asset_id,
                        "fulfilled_at": datetime.utcnow().isoformat(),
                    },
                )

            # List for sale on marketplace
            if platform and platform != "self" and generated_files:
                listing_res = await self.tools.execute(
                    "list_asset_for_sale",
                    asset_id=asset_id,
                    platform=platform,
                    price=price,
                )
                asset_doc["listing"] = listing_res

            # Finalize asset record
            asset_doc["status"] = "completed"
            vault.update(self.COLLECTION_ASSETS, asset_id, asset_doc)

            decision.status = "executed"
            decision.result_summary = (
                f"Created {asset_type} '{topic}' (asset_id={asset_id})"
            )
            decision.actual_revenue = 0.0

        except Exception as exc:
            asset_doc["status"] = "failed"
            asset_doc["error"] = str(exc)
            vault.update(self.COLLECTION_ASSETS, asset_id, asset_doc)
            decision.status = "failed"
            decision.result_summary = f"Failed to create {asset_type}: {exc}"

        self.log_decision(decision)
        self._save_vault()

    # ── Revenue tracking ──────────────────────────────────────────────────

    def update_revenue(self, asset_id: str, amount: float):
        """
        Update revenue when a sale is confirmed for an asset.

        Args:
            asset_id: The sold asset's ID.
            amount: Sale revenue amount.
        """
        asset = vault.get(self.COLLECTION_ASSETS, asset_id)
        if not asset:
            return
        asset_type = asset.get("asset_type", "unknown")
        self.asset_type_revenue[asset_type] = (
            self.asset_type_revenue.get(asset_type, 0.0) + amount
        )
        self.ledger.lifetime_revenue += amount
        self._save_vault()

    def get_status(self) -> Dict[str, Any]:
        """Extended status including asset-type revenue breakdown."""
        status = super().get_status()
        status["asset_type_revenue"] = self.asset_type_revenue
        status["pending_briefs_count"] = len(self.pending_briefs)
        return status
