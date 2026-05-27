"""
AffiliateAgent — autonomous affiliate marketing agent for the Monetization Swarm.

Discovers affiliate programs, generates tracking links, creates review and
comparison content, inserts links into existing content, and tracks estimated
commissions via the unified business vault.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.business_tools.vault import vault
from .base import BaseBusinessAgent, BusinessDecision


class AffiliateAgent(BaseBusinessAgent):
    """
    Autonomous affiliate-marketing agent.

    Responsibilities
    ----------------
    1. **Research** — discover affiliate programs in relevant niches.
    2. **Join** — persist program metadata to the vault.
    3. **Links** — generate campaign-specific tracking URLs.
    4. **Content** — create product reviews, comparison posts, and insert
       affiliate links into existing content.
    5. **Analytics** — estimate commissions and surface top-performing links.

    Vault collections used
    ----------------------
    - ``affiliate_programs``
    - ``affiliate_links``
    - ``affiliate_content``
    - ``commission_history``
    - ``traffic_sources``
    """

    def __init__(
        self,
        model_router,
        autonomy_tier: str = "AUTOPILOT",
        decision_callback=None,
    ):
        super().__init__(
            name="affiliate",
            description=(
                "Affiliate marketing automation: program discovery, link generation, "
                "content creation, and commission tracking."
            ),
            model_router=model_router,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )
        # Eager-import so that the @business_tool decorators run and the tools
        # are available in the registry before the first cycle.
        try:
            import core.business_tools.affiliate_tools  # noqa: F401
        except Exception as exc:
            print(f"[{self.name}] Warning: could not load affiliate_tools: {exc}")

    # ------------------------------------------------------------------
    # Perceive
    # ------------------------------------------------------------------

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather affiliate-related signals from the unified vault.

        Checks:
        - ``affiliate_programs`` — joined programs and their metadata.
        - ``affiliate_links`` — tracking links, clicks, estimated revenue.
        - ``affiliate_content`` — review/comparison articles.
        - ``content`` (generic) — pieces that could host affiliate links.
        - ``traffic_sources`` — inbound traffic channels.
        - ``commission_history`` — past earnings estimates.

        Returns:
            A structured perception dictionary.
        """
        perception: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.name,
        }

        # ── Affiliate programs ─────────────────────────────────────────
        programs = vault.find("affiliate_programs")
        perception["affiliate_programs"] = {
            "count": len(programs),
            "programs": [
                {
                    "id": p.get("_id"),
                    "name": p.get("program_name"),
                    "niche": p.get("niche"),
                    "status": p.get("status"),
                    "commission_rate": p.get("commission_rate"),
                }
                for p in programs[:20]
            ],
        }

        # ── Affiliate links ────────────────────────────────────────────
        links = vault.find("affiliate_links")
        total_clicks = sum(l.get("clicks", 0) for l in links)
        total_estimated_revenue = sum(l.get("estimated_revenue", 0.0) for l in links)
        perception["affiliate_links"] = {
            "count": len(links),
            "total_clicks": total_clicks,
            "total_estimated_revenue": round(total_estimated_revenue, 2),
            "top_links": sorted(
                links,
                key=lambda x: x.get("estimated_revenue", 0),
                reverse=True,
            )[:5],
        }

        # ── Affiliate content ──────────────────────────────────────────
        content = vault.find("affiliate_content")
        unpublished = [c for c in content if not c.get("published", False)]
        perception["affiliate_content"] = {
            "total_count": len(content),
            "unpublished_count": len(unpublished),
            "recent": [
                {
                    "id": c.get("_id"),
                    "title": c.get("title"),
                    "type": c.get("content_type"),
                    "published": c.get("published", False),
                }
                for c in content[:5]
            ],
        }

        # ── Generic content opportunities ──────────────────────────────
        generic_content = vault.find("content")
        content_without_links = [
            c
            for c in generic_content
            if not c.get("affiliate_links") and (c.get("body") or c.get("content"))
        ]
        perception["content_opportunities"] = {
            "generic_content_count": len(generic_content),
            "without_links_count": len(content_without_links),
            "candidates": [
                {
                    "id": c.get("_id"),
                    "title": c.get("title", "Untitled"),
                }
                for c in content_without_links[:5]
            ],
        }

        # ── Traffic sources ────────────────────────────────────────────
        traffic = vault.find("traffic_sources")
        perception["traffic_sources"] = {
            "count": len(traffic),
            "sources": [
                {
                    "id": t.get("_id"),
                    "source": t.get("source"),
                    "medium": t.get("medium"),
                    "estimated_monthly_visitors": t.get("estimated_monthly_visitors"),
                }
                for t in traffic[:10]
            ],
        }

        # ── Commission history ─────────────────────────────────────────
        history = vault.find("commission_history")
        perception["commission_history"] = {
            "count": len(history),
            "total_estimated": round(
                sum(h.get("estimated_earnings", 0.0) for h in history), 2
            ),
            "recent": history[-10:],
        }

        # Keep the ledger in sync with vault-derived estimates
        self.ledger.lifetime_revenue = total_estimated_revenue

        return perception

    # ------------------------------------------------------------------
    # Decide
    # ------------------------------------------------------------------

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Determine the next affiliate-marketing action.

        Decision types
        --------------
        - ``join_program`` — research & join a new affiliate program.
        - ``create_link`` — generate a tracking link for a campaign.
        - ``insert_links`` — embed affiliate links into existing content.
        - ``create_review`` — write a product-review article.
        - ``create_comparison`` — write a comparison article.
        - ``track_commissions`` — update earnings estimates.
        - ``optimize`` — analyse top performers for further action.

        Heuristics are evaluated first; if confidence is low the agent falls
        back to an LLM-based decision.

        Returns:
            A :class:`BusinessDecision` or ``None``.
        """
        programs = perception.get("affiliate_programs", {})
        links = perception.get("affiliate_links", {})
        content = perception.get("affiliate_content", {})
        opportunities = perception.get("content_opportunities", {})

        decision_type: Optional[str] = None
        payload: Dict[str, Any] = {}
        rationale = ""
        confidence = 0.5
        risk_score = 0.1
        estimated_impact = 0.0

        # Heuristic 1 — No programs at all → research & join
        if programs.get("count", 0) == 0:
            decision_type = "join_program"
            payload = {"niche": "software", "auto_join_first": True}
            rationale = (
                "No affiliate programs in vault. "
                "Start by researching programs in the software niche."
            )
            confidence = 0.9
            estimated_impact = 50.0

        # Heuristic 2 — Programs exist but links are scarce → create links
        elif programs.get("count", 0) > 0 and links.get("count", 0) < programs.get("count", 0) * 2:
            program = programs["programs"][0] if programs["programs"] else None
            if program:
                decision_type = "create_link"
                payload = {
                    "program_id": program["id"],
                    "landing_page": program.get("url", "https://example.com"),
                    "campaign": "default",
                }
                rationale = (
                    f"Program '{program['name']}' has few tracking links. "
                    f"Create a new campaign link to start driving traffic."
                )
                confidence = 0.85
                estimated_impact = 25.0

        # Heuristic 3 — Content without links → insert links
        elif opportunities.get("without_links_count", 0) > 0:
            candidate = (
                opportunities["candidates"][0]
                if opportunities["candidates"]
                else None
            )
            if candidate:
                decision_type = "insert_links"
                payload = {"content_id": candidate["id"]}
                rationale = (
                    f"Content '{candidate.get('title', 'Untitled')}' "
                    f"has no affiliate links. Insert relevant links to monetise traffic."
                )
                confidence = 0.8
                estimated_impact = 30.0

        # Heuristic 4 — No affiliate content but programs exist → create review
        elif content.get("total_count", 0) == 0 and programs.get("count", 0) > 0:
            program = programs["programs"][0] if programs["programs"] else None
            if program:
                decision_type = "create_review"
                payload = {
                    "product_name": program.get("name", "Product"),
                    "features": ["Easy to use", "Great support", "Affordable pricing"],
                }
                rationale = (
                    "No affiliate content exists. "
                    "Create a product review to drive conversions."
                )
                confidence = 0.75
                estimated_impact = 100.0

        # Heuristic 5 — Active links with clicks → track commissions
        elif links.get("total_clicks", 0) > 0:
            top_link = links.get("top_links", [{}])[0]
            if top_link:
                decision_type = "track_commissions"
                payload = {
                    "link_id": top_link.get("link_id"),
                    "clicks": 100,
                    "conversion_rate": 0.02,
                    "commission": 10.0,
                }
                rationale = (
                    f"Link '{top_link.get('campaign')}' has recorded activity. "
                    f"Update commission estimates to inform future optimisation."
                )
                confidence = 0.7
                estimated_impact = links.get("total_estimated_revenue", 0.0) * 0.1

        # Heuristic 6 — Fallback → optimise top performers
        else:
            decision_type = "optimize"
            payload = {"limit": 10}
            rationale = (
                "Review top-performing links and look for optimisation opportunities."
            )
            confidence = 0.6
            estimated_impact = 10.0

        # If confidence is low, delegate to the LLM for a second opinion
        if not decision_type or confidence < 0.6:
            llm_decision = await self._llm_decide(perception)
            if llm_decision:
                return llm_decision

        if not decision_type:
            return None

        return BusinessDecision(
            agent_name=self.name,
            decision_type=decision_type,
            rationale=rationale,
            action_payload=payload,
            estimated_revenue_impact=estimated_impact,
            risk_score=risk_score,
            confidence=confidence,
        )

    async def _llm_decide(
        self, perception: Dict[str, Any]
    ) -> Optional[BusinessDecision]:
        """
        Ask the LLM to choose the best affiliate action given current state.

        Expected JSON output keys:
        ``decision_type``, ``rationale``, ``payload`` (object),
        ``confidence`` (float 0-1), ``risk_score`` (float 0-1),
        ``estimated_revenue_impact`` (number).
        """
        system_prompt = (
            "You are an expert affiliate-marketing strategist. Given the current state of "
            "affiliate programs, links, content, and traffic, decide the single best next action. "
            "Respond in JSON with keys: decision_type, rationale, payload (object), "
            "confidence (0.0-1.0), risk_score (0.0-1.0), estimated_revenue_impact (number)."
        )
        user_prompt = (
            "Current perception:\n"
            f"{json.dumps(perception, indent=2, default=str)[:4000]}"
        )

        try:
            response = await self.llm_decide(system_prompt, user_prompt)
            if response and "decision_type" in response:
                return BusinessDecision(
                    agent_name=self.name,
                    decision_type=response["decision_type"],
                    rationale=response.get("rationale", ""),
                    action_payload=response.get("payload", {}),
                    estimated_revenue_impact=float(
                        response.get("estimated_revenue_impact", 0)
                    ),
                    risk_score=float(response.get("risk_score", 0.3)),
                    confidence=float(response.get("confidence", 0.5)),
                )
        except Exception as exc:
            print(f"[{self.name}] LLM decision failed: {exc}")

        return None

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute(self, decision: BusinessDecision):
        """
        Carry out an approved affiliate-marketing decision.

        Maps ``decision_type`` to the corresponding business tool, updates the
        decision record with results, and persists state to the vault.

        Args:
            decision: An approved :class:`BusinessDecision`.
        """
        payload = decision.action_payload
        decision_type = decision.decision_type
        result: Dict[str, Any] = {"status": "pending"}

        try:
            if decision_type == "join_program":
                niche = payload.get("niche", "software")
                research = await self.tools.execute(
                    "research_affiliate_programs", niche=niche
                )
                programs = research.get("programs", [])
                if programs and payload.get("auto_join_first"):
                    first = programs[0]
                    result = await self.tools.execute(
                        "join_affiliate_program",
                        program_name=first.get("title", "Unknown Program"),
                        url=first.get("url", ""),
                        niche=niche,
                    )
                else:
                    result = research

            elif decision_type == "create_link":
                result = await self.tools.execute(
                    "generate_tracking_link",
                    program_id=payload.get("program_id", ""),
                    landing_page=payload.get("landing_page", ""),
                    campaign=payload.get("campaign", "default"),
                )

            elif decision_type == "insert_links":
                content_id = payload.get("content_id", "")
                # Gather relevant links from the vault
                links = vault.find("affiliate_links", limit=10)
                product_urls: List[Dict[str, str]] = []
                for link in links:
                    url = link.get("tracking_url", "")
                    if url:
                        product_urls.append(
                            {
                                "anchor_text": link.get(
                                    "program_name", "this product"
                                ),
                                "url": url,
                            }
                        )

                # If no links exist yet, spin one up on the fly
                if not product_urls:
                    programs = vault.find("affiliate_programs", limit=1)
                    if programs:
                        prog = programs[0]
                        link_res = await self.tools.execute(
                            "generate_tracking_link",
                            program_id=prog.get("_id", ""),
                            landing_page=prog.get("url", "https://example.com"),
                            campaign="content_insert",
                        )
                        if link_res.get("status") == "ok":
                            product_urls.append(
                                {
                                    "anchor_text": prog.get(
                                        "program_name", "this product"
                                    ),
                                    "url": link_res.get("tracking_url", ""),
                                }
                            )

                result = await self.tools.execute(
                    "insert_affiliate_links",
                    content_id=content_id,
                    product_urls=product_urls,
                )

            elif decision_type == "create_review":
                product_name = payload.get("product_name", "Product")
                features = payload.get("features", [])

                # Re-use an existing link or create one
                links = vault.find("affiliate_links", limit=1)
                if links:
                    affiliate_link = links[0].get("tracking_url", "")
                else:
                    programs = vault.find("affiliate_programs", limit=1)
                    prog = programs[0] if programs else None
                    affiliate_link = ""
                    if prog:
                        link_res = await self.tools.execute(
                            "generate_tracking_link",
                            program_id=prog.get("_id", ""),
                            landing_page=prog.get("url", "https://example.com"),
                            campaign="review",
                        )
                        affiliate_link = link_res.get("tracking_url", "")

                result = await self.tools.execute(
                    "generate_product_review",
                    product_name=product_name,
                    features=features,
                    affiliate_link=affiliate_link,
                )

            elif decision_type == "create_comparison":
                result = await self.tools.execute(
                    "generate_comparison_post",
                    product_a=payload.get("product_a", "Product A"),
                    product_b=payload.get("product_b", "Product B"),
                    affiliate_links=payload.get("affiliate_links", {}),
                )

            elif decision_type == "track_commissions":
                result = await self.tools.execute(
                    "track_commission_estimate",
                    link_id=payload.get("link_id", ""),
                    clicks=payload.get("clicks", 0),
                    conversion_rate=payload.get("conversion_rate", 0.0),
                    commission=payload.get("commission", 0.0),
                )
                if result.get("status") == "ok":
                    self.ledger.lifetime_revenue += result.get(
                        "estimated_earnings", 0.0
                    )

            elif decision_type == "optimize":
                result = await self.tools.execute(
                    "get_top_performing_links",
                    limit=payload.get("limit", 10),
                )
                top = result.get("links", [])
                if top:
                    decision.rationale += (
                        f" | Top performer: {top[0].get('campaign')} "
                        f"with ${top[0].get('estimated_revenue', 0):.2f}"
                    )

            else:
                result = {
                    "status": "error",
                    "message": f"Unknown decision type: {decision_type}",
                }

        except Exception as exc:
            result = {"status": "error", "message": str(exc)}
            decision.status = "failed"
        else:
            decision.status = "executed"

        decision.result_summary = json.dumps(result, indent=2, default=str)[:1000]
        decision.actual_revenue = (
            result.get("estimated_earnings", 0.0)
            if isinstance(result, dict)
            else 0.0
        )
        self.log_decision(decision)
        self._save_vault()
        return result
