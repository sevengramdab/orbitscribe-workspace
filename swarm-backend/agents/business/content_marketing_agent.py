"""
ContentMarketingAgent — autonomous content marketing for the Monetization Swarm.

Creates blog posts, social threads, newsletters, email funnels, and SEO-optimized
content while tracking traffic and conversion estimates in the unified vault.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Register content tools via side-effect of module import
from core.business_tools import content_tools  # noqa: F401
from core.business_tools.vault import vault
from .base import BaseBusinessAgent, BusinessDecision


class ContentMarketingAgent(BaseBusinessAgent):
    """
    Autonomous content marketing agent.

    Responsibilities:
    - Research trending topics and SEO keyword opportunities
    - Produce blog posts, Twitter threads, newsletters, and email sequences
    - Optimize existing content for search engines
    - Schedule content and track estimated traffic / conversions
    """

    def __init__(self, model_router, autonomy_tier: str = "AUTOPILOT", decision_callback=None):
        super().__init__(
            name="ContentMarketingAgent",
            description="Autonomous blog, social, SEO, newsletter, and email funnel production.",
            model_router=model_router,
            autonomy_tier=autonomy_tier,
            decision_callback=decision_callback,
        )
        self._seed_vault()

    def _seed_vault(self) -> None:
        """Initialize empty collections with baseline SEO keywords and analytics."""
        if vault.count("seo_keywords") == 0:
            seed_keywords = [
                {"keyword": "AI automation tools", "volume": 5400, "difficulty": 45, "cpc": 2.5},
                {"keyword": "passive income ideas", "volume": 12100, "difficulty": 62, "cpc": 4.1},
                {"keyword": "content marketing strategy", "volume": 8100, "difficulty": 55, "cpc": 3.2},
                {"keyword": "small business growth", "volume": 6600, "difficulty": 38, "cpc": 2.8},
                {"keyword": "email marketing tips", "volume": 4400, "difficulty": 42, "cpc": 3.5},
            ]
            for kw in seed_keywords:
                vault.insert("seo_keywords", kw)

        if vault.count("content_analytics") == 0:
            vault.insert(
                "content_analytics",
                {"content_id": "placeholder", "views": 0, "note": "Baseline analytics collection initialized"},
            )

    # ── Perception ────────────────────────────────────────────────────────

    async def perceive(self) -> Dict[str, Any]:
        """
        Gather signals from the vault and external research.

        Checks:
        - Content calendar backlog and published count
        - Inventory of blog posts, social posts, and email sequences
        - SEO keyword opportunities (low difficulty, high volume)
        - Content performance snapshot (revenue, engagement)
        - Trending topics via web research

        Returns:
            Dict of observations used by decide().
        """
        # 1. Content calendar status
        calendar_items = vault.find("content_calendar", limit=50)
        scheduled_count = len([c for c in calendar_items if c.get("status") == "scheduled"])
        published_count = len([c for c in calendar_items if c.get("status") == "published"])

        # 2. Recent inventory counts
        blog_count = vault.count("blog_posts")
        social_count = vault.count("social_posts")
        email_count = vault.count("email_sequences")

        # 3. SEO keyword opportunities
        keywords = vault.find("seo_keywords", limit=20)
        opportunities = [
            kw
            for kw in keywords
            if kw.get("difficulty", 100) < 60 and kw.get("volume", 0) > 1000
        ]

        # 4. Content performance snapshot
        analytics = vault.find("content_analytics", limit=20)
        total_estimated_revenue = sum(a.get("estimated_revenue", 0) for a in analytics)
        avg_engagement = (
            sum(a.get("engagement_score", 0) for a in analytics) / len(analytics)
            if analytics
            else 0.0
        )

        # 5. Research trending topics (via registered tool)
        niche = "AI business automation"
        research_result = await self.tools.execute("research_trending_topics", niche=niche)
        trending = (
            research_result.get("topics", [])
            if "error" not in research_result
            else []
        )

        perception = {
            "calendar_backlog": scheduled_count,
            "published_count": published_count,
            "inventory": {
                "blog_posts": blog_count,
                "social_posts": social_count,
                "email_sequences": email_count,
            },
            "seo_opportunities": opportunities,
            "seo_opportunity_count": len(opportunities),
            "total_estimated_revenue": round(total_estimated_revenue, 2),
            "avg_engagement_score": round(avg_engagement, 1),
            "trending_topics": trending[:5],
            "timestamp": datetime.utcnow().isoformat(),
        }

        return perception

    # ── Decision ──────────────────────────────────────────────────────────

    async def decide(self, perception: Dict[str, Any]) -> Optional[BusinessDecision]:
        """
        Use the LLM to decide the next highest-ROI content action.

        Possible actions:
        - write_blog_post
        - create_twitter_thread
        - write_newsletter
        - create_email_funnel
        - optimize_seo

        Returns:
            BusinessDecision with confidence, risk_score, and estimated revenue impact.
        """
        system_prompt = (
            "You are the strategic brain of a content marketing agency. "
            "Given market signals, decide the single best action to take next. "
            "Respond ONLY with valid JSON matching this schema:\n"
            "{\n"
            '  "action": "write_blog_post|create_twitter_thread|write_newsletter|create_email_funnel|optimize_seo",\n'
            '  "rationale": "...",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "risk_score": 0.0-1.0,\n'
            '  "estimated_revenue_impact": 0.0,\n'
            '  "payload": {"topic":"...", "keywords":["..."], ...}\n'
            "}"
        )

        user_prompt = (
            f"Current time: {perception['timestamp']}\n"
            f"Content inventory: {perception['inventory']}\n"
            f"Scheduled backlog: {perception['calendar_backlog']}\n"
            f"SEO opportunities ({perception['seo_opportunity_count']}): "
            f"{[k.get('keyword') for k in perception['seo_opportunities'][:3]]}\n"
            f"Trending topics: {[t.get('title') for t in perception['trending_topics'][:3]]}\n"
            f"Total estimated revenue from content: ${perception['total_estimated_revenue']}\n"
            f"Avg engagement score: {perception['avg_engagement_score']}\n\n"
            "What should we create or optimize next?"
        )

        try:
            raw = await self.model_router.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
        except Exception as exc:
            # Fallback decision when LLM is unavailable
            raw = json.dumps(
                {
                    "action": "write_blog_post",
                    "rationale": f"LLM error fallback: {exc}",
                    "confidence": 0.5,
                    "risk_score": 0.2,
                    "estimated_revenue_impact": 50.0,
                    "payload": {
                        "topic": "AI automation trends",
                        "keywords": ["AI automation"],
                        "tone": "professional",
                        "length": "medium",
                    },
                }
            )

        # Parse structured decision
        try:
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            decision_data = json.loads(json_match.group()) if json_match else json.loads(raw)
        except Exception:
            decision_data = {
                "action": "write_blog_post",
                "rationale": "Fallback due to LLM parse failure.",
                "confidence": 0.6,
                "risk_score": 0.2,
                "estimated_revenue_impact": 75.0,
                "payload": {
                    "topic": "How AI Automation Transforms Small Business",
                    "keywords": ["AI automation", "small business"],
                    "tone": "professional",
                    "length": "medium",
                },
            }

        action = decision_data.get("action", "write_blog_post")
        payload = decision_data.get("payload", {})

        # Normalize action names to canonical forms
        action_map = {
            "write_blog_post": "write_blog_post",
            "create_blog_post": "write_blog_post",
            "blog": "write_blog_post",
            "create_twitter_thread": "create_twitter_thread",
            "twitter_thread": "create_twitter_thread",
            "social": "create_twitter_thread",
            "write_newsletter": "write_newsletter",
            "newsletter": "write_newsletter",
            "create_email_funnel": "create_email_funnel",
            "email_sequence": "create_email_funnel",
            "email_funnel": "create_email_funnel",
            "optimize_seo": "optimize_seo",
            "seo": "optimize_seo",
        }
        canonical_action = action_map.get(action, action)

        decision = BusinessDecision(
            agent_name=self.name,
            decision_type=canonical_action,
            rationale=decision_data.get("rationale", ""),
            action_payload=payload,
            estimated_revenue_impact=float(decision_data.get("estimated_revenue_impact", 0)),
            risk_score=float(decision_data.get("risk_score", 0.3)),
            confidence=float(decision_data.get("confidence", 0.5)),
        )

        # Auto-approve low-risk content decisions so the agent can run autonomously
        if decision.risk_score < 0.5 and decision.confidence > 0.6:
            decision.status = "approved"

        self.log_decision(decision)
        return decision

    # ── Execution ─────────────────────────────────────────────────────────

    async def execute(self, decision: BusinessDecision) -> None:
        """
        Execute the approved content decision using registered business tools.

        Saves outputs to the vault, schedules posts, and updates traffic /
        conversion estimates.

        Args:
            decision: The approved BusinessDecision to act upon.
        """
        action = decision.decision_type
        payload = decision.action_payload
        result_summary_parts: List[str] = []
        actual_revenue = 0.0

        try:
            if action == "write_blog_post":
                result = await self.tools.execute(
                    "generate_blog_post",
                    topic=payload.get("topic", "Untitled"),
                    keywords=payload.get("keywords", []),
                    tone=payload.get("tone", "professional"),
                    length=payload.get("length", "medium"),
                )
                content_id = result.get("content_id")
                result_summary_parts.append(
                    f"Blog post '{result.get('title')}' generated (ID: {content_id})."
                )

                if content_id:
                    publish_at = (datetime.utcnow() + timedelta(days=2)).isoformat()
                    sched = await self.tools.execute(
                        "schedule_content",
                        content_id=content_id,
                        platform="blog",
                        publish_at=publish_at,
                    )
                    result_summary_parts.append(
                        f"Scheduled for {publish_at} (entry {sched.get('entry_id')})."
                    )

                    perf = await self.tools.execute(
                        "get_content_performance", content_id=content_id
                    )
                    metrics = perf.get("metrics", {})
                    actual_revenue = metrics.get("estimated_revenue", 0.0)
                    result_summary_parts.append(
                        f"Est. revenue: ${actual_revenue} | Views: {metrics.get('views')}"
                    )

            elif action == "create_twitter_thread":
                result = await self.tools.execute(
                    "generate_twitter_thread",
                    topic=payload.get("topic", "Untitled"),
                    tweets=payload.get("tweets", 5),
                )
                content_id = result.get("content_id")
                result_summary_parts.append(
                    f"Twitter thread generated with {result.get('tweet_count')} tweets (ID: {content_id})."
                )

                if content_id:
                    publish_at = (datetime.utcnow() + timedelta(hours=4)).isoformat()
                    sched = await self.tools.execute(
                        "schedule_content",
                        content_id=content_id,
                        platform="twitter",
                        publish_at=publish_at,
                    )
                    result_summary_parts.append(f"Scheduled for {publish_at}.")
                    perf = await self.tools.execute(
                        "get_content_performance", content_id=content_id
                    )
                    actual_revenue = perf.get("metrics", {}).get("estimated_revenue", 0.0)

            elif action == "write_newsletter":
                result = await self.tools.execute(
                    "generate_newsletter",
                    subject=payload.get("subject", "Newsletter"),
                    topics=payload.get("topics", []),
                    cta=payload.get("cta", "Read More"),
                )
                content_id = result.get("content_id")
                result_summary_parts.append(
                    f"Newsletter '{result.get('subject')}' created (ID: {content_id})."
                )

                if content_id:
                    publish_at = (datetime.utcnow() + timedelta(days=1)).isoformat()
                    sched = await self.tools.execute(
                        "schedule_content",
                        content_id=content_id,
                        platform="newsletter",
                        publish_at=publish_at,
                    )
                    result_summary_parts.append(f"Scheduled for {publish_at}.")
                    perf = await self.tools.execute(
                        "get_content_performance", content_id=content_id
                    )
                    actual_revenue = perf.get("metrics", {}).get("estimated_revenue", 0.0)

            elif action == "create_email_funnel":
                result = await self.tools.execute(
                    "generate_email_sequence",
                    goal=payload.get("goal", "Engage subscribers"),
                    emails=payload.get("emails", 3),
                )
                content_id = result.get("content_id")
                result_summary_parts.append(
                    f"Email sequence '{result.get('sequence_name')}' with {result.get('email_count')} emails created (ID: {content_id})."
                )

                if content_id:
                    publish_at = (datetime.utcnow() + timedelta(days=1)).isoformat()
                    sched = await self.tools.execute(
                        "schedule_content",
                        content_id=content_id,
                        platform="email",
                        publish_at=publish_at,
                    )
                    result_summary_parts.append(f"First email scheduled for {publish_at}.")
                    perf = await self.tools.execute(
                        "get_content_performance", content_id=content_id
                    )
                    actual_revenue = perf.get("metrics", {}).get("estimated_revenue", 0.0)

            elif action == "optimize_seo":
                result = await self.tools.execute(
                    "optimize_for_seo",
                    content_id=payload.get("content_id", ""),
                    target_keywords=payload.get("target_keywords", []),
                )
                if "error" in result:
                    result_summary_parts.append(
                        f"SEO optimization failed: {result['error']}"
                    )
                    decision.status = "failed"
                else:
                    result_summary_parts.append(
                        f"SEO optimized content {result.get('original_content_id')} "
                        f"(score: {result.get('seo_score_estimate')}, changes: {len(result.get('changes_made', []))})."
                    )
                    actual_revenue = float(result.get("seo_score_estimate", 0)) * 0.5

            else:
                result_summary_parts.append(f"Unknown action type: {action}")
                decision.status = "failed"

            if decision.status != "failed":
                decision.status = "executed"
                decision.actual_revenue = actual_revenue
                decision.result_summary = " | ".join(result_summary_parts)
                self.ledger.lifetime_revenue += actual_revenue
                self.ledger.decisions_executed += 1

        except Exception as exc:
            decision.status = "failed"
            decision.result_summary = f"Execution error: {exc}"
            raise

        finally:
            self._save_vault()
