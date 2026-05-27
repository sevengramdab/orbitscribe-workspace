"""
LeadGenAgent — Autonomous lead generation, enrichment, and outreach.

Inherits from BaseBusinessAgent and implements the full PDCA loop:
  perceive  →  decide  →  execute  →  learn

Vault collections used:
  - leads
  - outreach_campaigns
  - enrichment_cache
  - pipeline_stages
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.business_tools.vault import vault
from .base import BaseBusinessAgent, BusinessDecision

# Ensure tools are registered in the global BusinessToolRegistry
import core.business_tools.lead_gen_tools  # noqa: F401


class LeadGenAgent(BaseBusinessAgent):
    """
    Autonomous agent responsible for:

    1. **Discovery** – Web search for leads in target niches/platforms.
    2. **Enrichment** – Augment lead records with LLM + web data.
    3. **Scoring**    – Algorithmic 0-100 score based on signals.
    4. **Outreach**   – Draft personalized emails via LLM.
    5. **Pipeline**   – Move leads through stages (new → contacted →
       qualified → proposal → closed).
    """

    def __init__(
        self,
        model_router,
        autonomy_tier: str = "AUTOPILOT",
        decision_callback=None,
    ):
        super().__init__(
            name="LeadGenAgent",
            description="Autonomous lead generation, enrichment, scoring, and outreach.",
            model_router=model_router,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )
        self.target_niches: List[str] = []
        self._refresh_target_niches()

    # ── Internal utilities ────────────────────────────────────────────────

    def _refresh_target_niches(self) -> None:
        """Pull active campaign niches so perceive() knows what to hunt for."""
        campaigns = vault.find(
            "outreach_campaigns",
            filter_fn=lambda c: c.get("active", True),
            limit=20,
        )
        self.target_niches = [
            c.get("target_niche")
            for c in campaigns
            if c.get("target_niche")
        ]

    @staticmethod
    def _estimate_revenue_impact(decision_type: str, count: int) -> float:
        """Rough heuristic for revenue impact (used in BusinessDecision)."""
        if decision_type == "move_pipeline":
            return count * 150.0  # qualified leads are worth ~$150
        if decision_type == "draft_outreach":
            return count * 50.0
        if decision_type == "scrape_new_leads":
            return count * 25.0
        return 0.0

    # ── Perception ────────────────────────────────────────────────────────

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather pipeline state, identify gaps, and optionally discover new
        opportunities via lightweight web search.
        """
        self._refresh_target_niches()

        leads = vault.find("leads", limit=500)
        campaigns = vault.find("outreach_campaigns", limit=50)

        # Stage counts
        stage_counts: Dict[str, int] = {
            stage: sum(1 for l in leads if l.get("stage", "new") == stage)
            for stage in ["new", "contacted", "qualified", "proposal", "closed"]
        }

        # Leads missing data / low score
        needs_enrichment = [
            l for l in leads
            if not l.get("enriched") and l.get("score", 0) < 60
        ][:15]

        # High-quality leads awaiting first contact
        needs_outreach = [
            l for l in leads
            if l.get("score", 0) >= 60 and l.get("stage") == "new"
        ][:15]

        # Stale contacted leads with no follow-up flag
        stale_contacted = [
            l for l in leads
            if l.get("stage") == "contacted" and not l.get("follow_up_scheduled")
        ][:10]

        active_campaigns = [c for c in campaigns if c.get("active", True)]
        low_inventory = len(leads) < 50

        perception: Dict[str, Any] = {
            "total_leads": len(leads),
            "stage_counts": stage_counts,
            "needs_enrichment_count": len(needs_enrichment),
            "needs_enrichment_preview": [
                {"_id": l["_id"], "name": l.get("name"), "score": l.get("score")}
                for l in needs_enrichment
            ],
            "needs_outreach_count": len(needs_outreach),
            "needs_outreach_preview": [
                {"_id": l["_id"], "name": l.get("name"), "score": l.get("score")}
                for l in needs_outreach
            ],
            "stale_contacted_count": len(stale_contacted),
            "stale_contacted_preview": [
                {"_id": l["_id"], "name": l.get("name")}
                for l in stale_contacted
            ],
            "active_campaigns": [
                {"name": c.get("name"), "niche": c.get("target_niche")}
                for c in active_campaigns
            ],
            "low_inventory": low_inventory,
            "target_niches": self.target_niches,
        }

        # Lightweight proactive search when inventory is low
        if low_inventory and self.target_niches:
            search_result = await self.tools.execute(
                "search_leads",
                query=self.target_niches[0],
                platform="linkedin",
            )
            perception["discovered_from_search"] = search_result.get("leads_found", 0)
        else:
            perception["discovered_from_search"] = 0

        return perception

    # ── Decision ──────────────────────────────────────────────────────────

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Use an LLM to choose the highest-impact next action.

        Supported decision types:
          - scrape_new_leads
          - enrich_leads
          - draft_outreach
          - move_pipeline
          - noop
        """
        system_prompt = (
            "You are a strategic lead-generation AI.\n\n"
            "Given pipeline state, choose ONE next action from:\n"
            "- scrape_new_leads   (use when low_inventory or very few new leads)\n"
            "- enrich_leads       (use when many unenriched / low-score leads)\n"
            "- draft_outreach     (use when high-score leads are waiting in 'new')\n"
            "- move_pipeline      (use when contacted leads are stale)\n"
            "- noop               (pipeline looks healthy)\n\n"
            "Respond in JSON:\n"
            '{\n'
            '  "decision_type": "scrape_new_leads|enrich_leads|draft_outreach|move_pipeline|noop",\n'
            '  "rationale": "...",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "risk_score": 0.0-1.0,\n'
            '  "action_payload": {}\n'
            "}"
        )

        user_prompt = f"Pipeline state:\n{json.dumps(perception, indent=2, default=str)}"

        try:
            llm_text = await self.model_router.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            json_match = re.search(r"\{.*\}", llm_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = {
                    "decision_type": "noop",
                    "rationale": "Could not parse LLM output",
                }
        except Exception as exc:
            parsed = {
                "decision_type": "noop",
                "rationale": f"LLM decision failed: {exc}",
            }

        decision_type = parsed.get("decision_type", "noop")
        if decision_type == "noop":
            return None

        # Build action payload tailored to the decision type
        payload: Dict[str, Any] = {}
        if decision_type == "scrape_new_leads":
            niche = (
                perception["target_niches"][0]
                if perception.get("target_niches")
                else "AI automation"
            )
            payload = {"query": niche, "platform": "linkedin"}
        elif decision_type == "enrich_leads":
            payload = {
                "lead_ids": [
                    l["_id"]
                    for l in perception.get("needs_enrichment_preview", [])[:5]
                ]
            }
        elif decision_type == "draft_outreach":
            payload = {
                "lead_ids": [
                    l["_id"]
                    for l in perception.get("needs_outreach_preview", [])[:5]
                ],
                "product": None,  # resolved at execution time from campaigns
            }
        elif decision_type == "move_pipeline":
            payload = {
                "from_stage": "contacted",
                "to_stage": "qualified",
            }

        confidence = float(parsed.get("confidence", 0.5))
        risk_score = float(parsed.get("risk_score", 0.1))

        return BusinessDecision(
            agent_name=self.name,
            decision_type=decision_type,
            rationale=parsed.get("rationale", ""),
            action_payload=payload,
            confidence=confidence,
            risk_score=risk_score,
            estimated_revenue_impact=self._estimate_revenue_impact(
                decision_type, len(payload.get("lead_ids", []))
            ),
        )

    # ── Execution ─────────────────────────────────────────────────────────

    async def execute(self, decision: BusinessDecision):
        """
        Perform the decided action using registered lead-gen tools.
        Update the decision object with results and persist state.
        """
        payload = decision.action_payload
        decision_type = decision.decision_type
        results: List[Dict[str, Any]] = []

        try:
            if decision_type == "scrape_new_leads":
                result = await self.tools.execute(
                    "search_leads",
                    query=payload.get("query", "AI automation"),
                    platform=payload.get("platform", "linkedin"),
                )
                if "error" in result:
                    decision.status = "failed"
                    decision.result_summary = f"Search failed: {result['error']}"
                else:
                    for lead in result.get("leads", []):
                        score_res = await self.tools.execute("score_lead", lead=lead)
                        lead["score"] = score_res.get("score", 0)
                        lead_id = vault.insert("leads", lead)
                        results.append({"lead_id": lead_id, "name": lead.get("name")})
                    decision.result_summary = f"Discovered and saved {len(results)} leads"
                    decision.status = "executed"

            elif decision_type == "enrich_leads":
                for lead_id in payload.get("lead_ids", []):
                    enrich_res = await self.tools.execute(
                        "enrich_lead",
                        lead_id=lead_id,
                    )
                    results.append(enrich_res)
                    # Re-score after enrichment
                    lead = vault.get("leads", lead_id)
                    if lead:
                        score_res = await self.tools.execute("score_lead", lead=lead)
                        vault.update("leads", lead_id, {"score": score_res.get("score", 0)})
                decision.result_summary = f"Enriched {len(results)} leads"
                decision.status = "executed"

            elif decision_type == "draft_outreach":
                product = payload.get("product")
                if not product:
                    campaigns = vault.find(
                        "outreach_campaigns",
                        filter_fn=lambda c: c.get("active", True),
                        limit=1,
                    )
                    product = (
                        campaigns[0].get("message_template", "our solution")
                        if campaigns
                        else "our solution"
                    )

                for lead_id in payload.get("lead_ids", []):
                    lead = vault.get("leads", lead_id)
                    if not lead:
                        continue

                    draft_res = await self.tools.execute(
                        "draft_outreach_email",
                        lead=lead,
                        product=product,
                        tone=payload.get("tone", "professional"),
                    )

                    # Cache the draft in enrichment_cache
                    email_doc = {
                        "lead_id": lead_id,
                        "lead_name": lead.get("name"),
                        "email": draft_res.get("email"),
                        "product": product,
                        "drafted_at": datetime.utcnow().isoformat(),
                    }
                    vault.insert("enrichment_cache", email_doc)
                    results.append({
                        "lead_id": lead_id,
                        "email_subject": draft_res.get("email", {}).get("subject"),
                    })
                decision.result_summary = f"Drafted outreach for {len(results)} leads"
                decision.status = "executed"

            elif decision_type == "move_pipeline":
                from_stage = payload.get("from_stage", "contacted")
                to_stage = payload.get("to_stage", "qualified")
                stage_leads = vault.find(
                    "leads",
                    filter_fn=lambda doc: doc.get("stage") == from_stage,
                    limit=20,
                )
                for lead in stage_leads:
                    move_res = await self.tools.execute(
                        "move_lead_stage",
                        lead_id=lead["_id"],
                        stage=to_stage,
                    )
                    results.append(move_res)
                decision.result_summary = (
                    f"Moved {len(results)} leads from {from_stage} to {to_stage}"
                )
                decision.status = "executed"

            else:
                decision.result_summary = "Unknown decision type; no action taken."
                decision.status = "failed"

        except Exception as exc:
            decision.status = "failed"
            decision.result_summary = f"Execution error: {exc}"

        self.log_decision(decision)
        self._save_vault()
