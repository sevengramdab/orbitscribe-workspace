"""
affiliate_agent.py
==================
Affiliate marketing automation agent.

Actions:
- generate_comparison   -> Create product-comparison posts via business-tool registry
- generate_review       -> Create product-review posts via business-tool registry
- post_to_medium        -> Simulate posting to Medium via browser automation
- post_to_blog          -> Simulate posting to a self-hosted blog via browser
- check_commissions     -> Read/simulate affiliate commission dashboard
- update_links          -> Scan content/affiliate/ and refresh tracking links

Revenue model (simulated):
- $2.00 per comparison post generated
- $0.10 per click simulation
"""
from __future__ import annotations

import os
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from money_engine.base_agent import BaseMoneyAgent, AgentDecision
from money_engine.orchestrator import register_agent


@register_agent
class AffiliateAgent(BaseMoneyAgent):
    """
    Automates affiliate marketing workflows:
    content generation, link insertion, publishing simulation, and commission tracking.
    """

    VERTICAL = "affiliate"

    # Simulated revenue constants
    REVENUE_PER_COMPARISON = 2.0
    REVENUE_PER_CLICK = 0.10

    # Simple product catalogue for autonomous generation
    _PRODUCT_PAIRS = [
        ("Adobe Photoshop", "GIMP", {"Adobe Photoshop": "amazon", "GIMP": "amazon"}),
        ("Bluehost", "SiteGround", {"Bluehost": "amazon", "SiteGround": "amazon"}),
        ("NordVPN", "ExpressVPN", {"NordVPN": "amazon", "ExpressVPN": "amazon"}),
        ("AirPods Pro", "Sony WH-1000XM5", {"AirPods Pro": "amazon", "Sony WH-1000XM5": "amazon"}),
        ("Logitech MX Master", "Razer Pro Click", {"Logitech MX Master": "amazon", "Razer Pro Click": "amazon"}),
    ]

    _REVIEW_PRODUCTS = [
        ("NordVPN", ["Military-grade encryption", "No-logs policy", "6,000+ servers", "Threat Protection"]),
        ("Bluehost", ["Free domain first year", "One-click WordPress install", "24/7 support", "Unmetered bandwidth"]),
        ("Adobe Photoshop", ["AI-powered Generative Fill", "Layer-based editing", "Extensive plugin ecosystem", "Cloud sync"]),
        ("AirPods Pro", ["Active Noise Cancellation", "Transparency mode", "Spatial Audio", "MagSafe charging"]),
        ("Logitech MX Master 3S", ["8,000 DPI sensor", "MagSpeed electromagnetic wheel", "Multi-device connectivity", "USB-C quick charge"]),
    ]

    def __init__(self, agent_id: str | None = None, headless_browser: bool = False):
        super().__init__(agent_id=agent_id, headless_browser=headless_browser)
        self._action_index = 0

    # ------------------------------------------------------------------
    # Decision logic
    # ------------------------------------------------------------------

    def decide(self) -> AgentDecision:
        """
        Pick the next affiliate action based on a rotating schedule.
        """
        actions = [
            "generate_comparison",
            "generate_review",
            "update_links",
            "post_to_medium",
            "post_to_blog",
            "check_commissions",
        ]
        action = actions[self._action_index % len(actions)]
        self._action_index += 1

        params: Dict[str, Any] = {}
        reasoning = ""

        if action == "generate_comparison":
            product_a, product_b, programs = random.choice(self._PRODUCT_PAIRS)
            params = {
                "product_a": product_a,
                "product_b": product_b,
                "programs": programs,
            }
            reasoning = f"Generate a comparison post for '{product_a}' vs '{product_b}' to drive affiliate traffic."

        elif action == "generate_review":
            product_name, features = random.choice(self._REVIEW_PRODUCTS)
            params = {
                "product_name": product_name,
                "features": features,
            }
            reasoning = f"Generate a product review for '{product_name}' with embedded affiliate links."

        elif action == "post_to_medium":
            # Find the most recent unpublished comparison or review
            content_id = self._pick_unpublished_content()
            params = {"content_id": content_id, "platform": "medium"}
            reasoning = f"Simulate publishing content '{content_id}' to Medium."

        elif action == "post_to_blog":
            content_id = self._pick_unpublished_content()
            params = {"content_id": content_id, "platform": "blog"}
            reasoning = f"Simulate publishing content '{content_id}' to self-hosted blog."

        elif action == "check_commissions":
            params = {}
            reasoning = "Simulate reading affiliate commission dashboard and update revenue."

        elif action == "update_links":
            params = {}
            reasoning = "Scan content/affiliate/ folder and refresh/update affiliate tracking links."

        return AgentDecision(
            decision_id=f"aff_{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            action=action,
            params=params,
            reasoning=reasoning,
        )

    # ------------------------------------------------------------------
    # Execution logic
    # ------------------------------------------------------------------

    def execute(self, decision: AgentDecision) -> dict:
        """
        Execute the chosen affiliate action.
        """
        action = decision.action
        params = decision.params

        if action == "generate_comparison":
            return self._exec_generate_comparison(params)

        if action == "generate_review":
            return self._exec_generate_review(params)

        if action == "post_to_medium":
            return self._exec_post_to_medium(params)

        if action == "post_to_blog":
            return self._exec_post_to_blog(params)

        if action == "check_commissions":
            return self._exec_check_commissions(params)

        if action == "update_links":
            return self._exec_update_links(params)

        return {"success": False, "error": f"Unknown action: {action}"}

    # ------------------------------------------------------------------
    # Individual action implementations
    # ------------------------------------------------------------------

    def _exec_generate_comparison(self, params: dict) -> dict:
        """Generate a comparison post via the business-tool registry."""
        result = self.generate_asset_via_registry(
            "generate_comparison_post",
            product_a=params["product_a"],
            product_b=params["product_b"],
            programs=params["programs"],
        )
        success = result.get("status") == "ok" or result.get("success", False)
        revenue = self.REVENUE_PER_COMPARISON if success else 0.0
        self.log(f"Comparison post result: success={success}, revenue={revenue}")
        return {
            "success": success,
            "action": "generate_comparison",
            "result": result,
            "revenue": revenue,
            "costs": 0.0,
        }

    def _exec_generate_review(self, params: dict) -> dict:
        """Generate a product review via the business-tool registry."""
        result = self.generate_asset_via_registry(
            "generate_product_review",
            product_name=params["product_name"],
            features=params["features"],
        )
        success = result.get("status") == "ok" or result.get("success", False)
        revenue = self.REVENUE_PER_COMPARISON if success else 0.0
        self.log(f"Product review result: success={success}, revenue={revenue}")
        return {
            "success": success,
            "action": "generate_review",
            "result": result,
            "revenue": revenue,
            "costs": 0.0,
        }

    def _exec_post_to_medium(self, params: dict) -> dict:
        """
        Simulate posting content to Medium via browser automation.
        Opens Chrome, navigates to Medium's new-story page, and types a stub.
        """
        try:
            self.browser.open_chrome(url="https://medium.com/new-story", new_window=False)
            time.sleep(2.0)
            self.browser.focus_chrome()
            time.sleep(0.5)
            # Click in the title area (approximate percentage coordinates)
            self.browser.win_click(0.5, 0.25)
            time.sleep(0.3)
            title = params.get("content_id", "Affiliate Comparison Post")
            self.browser.win_type(f"{title}\n", interval=0.01)
            time.sleep(0.3)
            # Click in the body area
            self.browser.win_click(0.5, 0.40)
            time.sleep(0.3)
            self.browser.win_type(
                "This post contains affiliate links. We earn a commission when you purchase through these links, at no extra cost to you.\n",
                interval=0.01,
            )
            time.sleep(0.5)
            # Simulate a publish button click (top-right area)
            self.browser.win_click(0.85, 0.08)
            time.sleep(1.0)
            self.log(f"Simulated posting '{title}' to Medium.")
            return {
                "success": True,
                "action": "post_to_medium",
                "platform": "medium",
                "content_id": params.get("content_id"),
                "revenue": 0.0,
                "costs": 0.0,
            }
        except Exception as exc:
            self.log(f"Medium posting simulation failed: {exc}")
            return {"success": False, "action": "post_to_medium", "error": str(exc)}

    def _exec_post_to_blog(self, params: dict) -> dict:
        """
        Simulate posting to a self-hosted blog.
        Opens Chrome and navigates to a local blog admin page (placeholder).
        """
        try:
            blog_url = "http://localhost:8080/admin/new-post"
            self.browser.open_chrome(url=blog_url, new_window=False)
            time.sleep(2.0)
            self.browser.focus_chrome()
            time.sleep(0.5)
            # Fill title field (approximate coordinates for a generic admin UI)
            self.browser.fill_form_field(0.5, 0.20, params.get("content_id", "New Affiliate Post"))
            time.sleep(0.3)
            # Fill body field
            self.browser.fill_form_field(
                0.5,
                0.45,
                "Check out our latest affiliate recommendations in the full article.",
            )
            time.sleep(0.3)
            # Click publish button (top-right-ish)
            self.browser.win_click(0.88, 0.15)
            time.sleep(1.0)
            self.log(f"Simulated posting '{params.get('content_id')}' to self-hosted blog.")
            return {
                "success": True,
                "action": "post_to_blog",
                "platform": "blog",
                "content_id": params.get("content_id"),
                "revenue": 0.0,
                "costs": 0.0,
            }
        except Exception as exc:
            self.log(f"Blog posting simulation failed: {exc}")
            return {"success": False, "action": "post_to_blog", "error": str(exc)}

    def _exec_check_commissions(self, _params: dict) -> dict:
        """
        Simulate reading an affiliate commission dashboard.
        Uses the business-tool registry to fetch top-performing links and simulates
        a small number of clicks for revenue tracking.
        """
        try:
            result = self.generate_asset_via_registry(
                "get_top_performing_links",
                limit=5,
            )
            links = result.get("links", []) if isinstance(result, dict) else []
            simulated_clicks = random.randint(5, 25)
            revenue = simulated_clicks * self.REVENUE_PER_CLICK
            self.log(
                f"Commission check: {len(links)} top links found, "
                f"simulated {simulated_clicks} clicks, revenue=${revenue:.2f}"
            )
            return {
                "success": True,
                "action": "check_commissions",
                "top_links_count": len(links),
                "simulated_clicks": simulated_clicks,
                "revenue": revenue,
                "costs": 0.0,
                "details": result,
            }
        except Exception as exc:
            self.log(f"Commission check failed: {exc}")
            # Graceful fallback: still simulate some clicks
            simulated_clicks = random.randint(5, 25)
            revenue = simulated_clicks * self.REVENUE_PER_CLICK
            return {
                "success": True,
                "action": "check_commissions",
                "simulated_clicks": simulated_clicks,
                "revenue": revenue,
                "costs": 0.0,
                "error": str(exc),
            }

    def _exec_update_links(self, _params: dict) -> dict:
        """
        Scan the content/affiliate/ folder for markdown files and ensure
        affiliate tracking links are up to date.
        """
        content_dir = Path(__file__).parent.parent.parent / "content" / "affiliate"
        if not content_dir.exists():
            content_dir.mkdir(parents=True, exist_ok=True)

        updated = 0
        scanned = 0
        try:
            for md_file in content_dir.glob("*.md"):
                scanned += 1
                text = md_file.read_text(encoding="utf-8")
                # If the file contains placeholder links, replace them with a tracking pattern
                if "example.com" in text or "#affiliate-link" in text:
                    new_text = text.replace(
                        "https://example.com/placeholder",
                        "https://www.amazon.com?tag=AFF_AGENT_01",
                    )
                    new_text = new_text.replace(
                        "#affiliate-link",
                        "https://www.amazon.com?tag=AFF_AGENT_01",
                    )
                    md_file.write_text(new_text, encoding="utf-8")
                    updated += 1
                    self.log(f"Updated links in {md_file.name}")

            self.log(f"Link update complete: {scanned} files scanned, {updated} updated.")
            return {
                "success": True,
                "action": "update_links",
                "scanned": scanned,
                "updated": updated,
                "revenue": 0.0,
                "costs": 0.0,
            }
        except Exception as exc:
            self.log(f"Link update failed: {exc}")
            return {"success": False, "action": "update_links", "error": str(exc)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pick_unpublished_content(self) -> str:
        """
        Look in content/affiliate/ for the most recently created markdown file
        and return its stem as a content identifier.
        """
        content_dir = Path(__file__).parent.parent.parent / "content" / "affiliate"
        if content_dir.exists():
            md_files = sorted(content_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if md_files:
                return md_files[0].stem
        return "affiliate_post_default"

    def get_default_interval(self) -> int:
        """Return default cycle interval in seconds (10 minutes)."""
        return 600
