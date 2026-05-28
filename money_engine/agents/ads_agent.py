"""
ads_agent.py
============
Automates ad campaign creation and monitoring across Facebook & Google.
- Generates ad copy from templates
- Navigates ads.facebook.com / ads.google.com via BrowserController
- Simulates performance metrics and tracks P&L
"""
from __future__ import annotations

import random
import time
import uuid
from typing import Any, Dict, List

from money_engine.base_agent import BaseMoneyAgent, AgentDecision
from money_engine.orchestrator import register_agent


# Simple in-memory ad copy templates
AD_COPY_TEMPLATES: List[Dict[str, str]] = [
    {
        "headline": "Unlock Your Potential Today",
        "body": "Join thousands who have transformed their workflow. Limited spots available—get started now!",
        "cta": "Get Started",
    },
    {
        "headline": "Save 50% This Week Only",
        "body": "Our premium plan is half off for new members. Don't miss out on this exclusive deal.",
        "cta": "Claim Offer",
    },
    {
        "headline": "The Tool Top Creators Swear By",
        "body": "Streamline your content, boost engagement, and grow faster. Try it free for 14 days.",
        "cta": "Try Free",
    },
    {
        "headline": "Stop Overpaying for Software",
        "body": "One affordable platform replaces five expensive tools. See why teams are switching today.",
        "cta": "See Pricing",
    },
    {
        "headline": "Results in 24 Hours—Guaranteed",
        "body": "Our proven system delivers measurable outcomes fast. Start your risk-free trial now.",
        "cta": "Start Trial",
    },
]


@register_agent
class AdsAgent(BaseMoneyAgent):
    """
    Money agent for the "ads" vertical.
    Creates ad copy, sets up Facebook/Google campaigns, checks metrics,
    optimizes bids, and screenshots dashboards.
    """

    VERTICAL = "ads"

    # Simulated campaign state (not persisted to keep example simple)
    _campaigns: Dict[str, Dict[str, Any]] = {}
    _last_action_index: int = 0

    def __init__(self, agent_id=None, headless_browser: bool = False):
        super().__init__(agent_id=agent_id, headless_browser=headless_browser)
        self._campaigns = {}
        self._last_action_index = 0

    # ------------------------------------------------------------------
    # Decision logic
    # ------------------------------------------------------------------

    def decide(self) -> AgentDecision:
        """
        Cycle through a deterministic list of actions so every vertical
        gets exercised over time.
        """
        actions = [
            "create_ad_copy",
            "setup_facebook_ad",
            "setup_google_ad",
            "check_performance",
            "optimize_campaign",
            "screenshot_dashboard",
        ]
        action = actions[self._last_action_index % len(actions)]
        self._last_action_index += 1

        params: Dict[str, Any] = {}
        reasoning = ""

        if action == "create_ad_copy":
            tpl = random.choice(AD_COPY_TEMPLATES)
            params = {
                "headline": tpl["headline"],
                "body": tpl["body"],
                "cta": tpl["cta"],
            }
            reasoning = f"Selected template '{tpl['headline']}' for new ad copy."

        elif action == "setup_facebook_ad":
            campaign_id = f"fb_{uuid.uuid4().hex[:6]}"
            params = {
                "platform": "facebook",
                "campaign_id": campaign_id,
                "budget_usd": round(random.uniform(10.0, 50.0), 2),
            }
            reasoning = f"Launching Facebook campaign {campaign_id} with ${params['budget_usd']} budget."

        elif action == "setup_google_ad":
            campaign_id = f"ggl_{uuid.uuid4().hex[:6]}"
            params = {
                "platform": "google",
                "campaign_id": campaign_id,
                "budget_usd": round(random.uniform(15.0, 60.0), 2),
            }
            reasoning = f"Launching Google Ads campaign {campaign_id} with ${params['budget_usd']} budget."

        elif action == "check_performance":
            params = {"platform": random.choice(["facebook", "google", "all"])}
            reasoning = f"Checking performance for {params['platform']} campaigns."

        elif action == "optimize_campaign":
            if self._campaigns:
                target = random.choice(list(self._campaigns.keys()))
            else:
                target = "fb_default"
            params = {"campaign_id": target, "bid_adjustment_pct": random.randint(-20, 30)}
            reasoning = (
                f"Optimizing campaign {target} by {params['bid_adjustment_pct']}% bid adjustment."
            )

        elif action == "screenshot_dashboard":
            params = {"platform": random.choice(["facebook", "google"])}
            reasoning = f"Capturing {params['platform']} ads dashboard screenshot."

        return AgentDecision(
            decision_id=f"ads_{int(time.time())}_{uuid.uuid4().hex[:4]}",
            timestamp=time.time(),
            action=action,
            params=params,
            reasoning=reasoning,
        )

    # ------------------------------------------------------------------
    # Execution logic
    # ------------------------------------------------------------------

    def execute(self, decision: AgentDecision) -> dict:
        """Dispatch to the correct handler based on decision.action."""
        handler = getattr(self, f"_exec_{decision.action}", None)
        if handler:
            return handler(decision)
        return {"success": False, "error": f"Unknown action: {decision.action}"}

    def get_default_interval(self) -> int:
        """Return default cycle interval in seconds (~11.7 minutes)."""
        return 700

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _exec_create_ad_copy(self, decision: AgentDecision) -> dict:
        """Generate ad copy from the built-in template registry."""
        params = decision.params
        headline = params.get("headline", "Amazing Offer")
        body = params.get("body", "Check it out today!")
        cta = params.get("cta", "Learn More")

        self.log(f"Generated ad copy — Headline: '{headline}' | CTA: '{cta}'")
        return {
            "success": True,
            "headline": headline,
            "body": body,
            "cta": cta,
            "revenue": 0.0,
            "costs": 0.0,
        }

    def _exec_setup_facebook_ad(self, decision: AgentDecision) -> dict:
        """Navigate ads.facebook.com and walk through a creation flow."""
        params = decision.params
        campaign_id = params.get("campaign_id", f"fb_{uuid.uuid4().hex[:6]}")
        budget = params.get("budget_usd", 20.0)

        self.log(f"Setting up Facebook campaign {campaign_id} (budget ${budget})")

        try:
            self.browser.open_chrome(url="https://business.facebook.com/", new_window=False)
            time.sleep(3.0)

            # Navigate to Ads Manager (fallback if already on business page)
            self.browser.navigate("https://business.facebook.com/ads-manager")
            time.sleep(3.0)

            # --- Simulated creation flow using percentage coords ---
            # Click "Create" button (approx top-left area of Ads Manager)
            self.browser.win_click(0.08, 0.18)
            time.sleep(1.5)

            # Campaign name field (approx modal center-left)
            self.browser.fill_form_field(0.35, 0.28, campaign_id)
            time.sleep(0.5)

            # Buying type / objective — click first objective card
            self.browser.win_click(0.25, 0.42)
            time.sleep(0.5)

            # Scroll down a bit to reveal budget fields
            self.browser.win_scroll(-3, x_pct=0.5, y_pct=0.6)
            time.sleep(0.5)

            # Budget field (approx mid-right)
            self.browser.fill_form_field(0.72, 0.55, str(budget))
            time.sleep(0.5)

            # Click "Continue" (approx bottom-right of modal)
            self.browser.win_click(0.85, 0.92)
            time.sleep(2.0)

            # Headline field (ad level)
            self.browser.fill_form_field(0.30, 0.35, "Unlock Your Potential Today")
            time.sleep(0.5)

            # Primary text / body
            self.browser.fill_form_field(0.30, 0.45, "Join thousands transforming their workflow. Limited spots!")
            time.sleep(0.5)

            # CTA button dropdown — click it then select first option
            self.browser.win_click(0.35, 0.62)
            time.sleep(0.4)
            self.browser.win_click(0.35, 0.68)
            time.sleep(0.4)

            # Final publish button (approx top-right)
            self.browser.win_click(0.90, 0.15)
            time.sleep(2.0)

            # Track simulated cost
            self._campaigns[campaign_id] = {
                "platform": "facebook",
                "budget": budget,
                "spent": 0.0,
                "clicks": 0,
                "impressions": 0,
                "ctr": 0.0,
                "cpc": 0.0,
                "bid": 1.0,
            }

            self.log(f"Facebook campaign {campaign_id} created successfully.")
            return {
                "success": True,
                "campaign_id": campaign_id,
                "platform": "facebook",
                "budget_usd": budget,
                "revenue": 0.0,
                "costs": round(budget * 0.05, 2),  # small initial setup cost
            }
        except Exception as e:
            self.log(f"Facebook setup failed: {e}")
            return {"success": False, "error": str(e), "revenue": 0.0, "costs": 0.0}

    def _exec_setup_google_ad(self, decision: AgentDecision) -> dict:
        """Navigate ads.google.com and walk through a creation flow."""
        params = decision.params
        campaign_id = params.get("campaign_id", f"ggl_{uuid.uuid4().hex[:6]}")
        budget = params.get("budget_usd", 25.0)

        self.log(f"Setting up Google Ads campaign {campaign_id} (budget ${budget})")

        try:
            self.browser.open_chrome(url="https://ads.google.com/", new_window=False)
            time.sleep(3.0)

            # Click "New campaign" if available (approx top-left-ish)
            self.browser.win_click(0.10, 0.20)
            time.sleep(1.5)

            # Select campaign goal — click first card
            self.browser.win_click(0.20, 0.35)
            time.sleep(0.5)

            # Continue button
            self.browser.win_click(0.85, 0.90)
            time.sleep(1.5)

            # Campaign name
            self.browser.fill_form_field(0.35, 0.25, campaign_id)
            time.sleep(0.5)

            # Budget input (approx mid-right)
            self.browser.fill_form_field(0.70, 0.40, str(budget))
            time.sleep(0.5)

            # Continue
            self.browser.win_click(0.85, 0.90)
            time.sleep(1.5)

            # Ad group name
            self.browser.fill_form_field(0.35, 0.30, f"AdGroup_{campaign_id}")
            time.sleep(0.5)

            # Continue
            self.browser.win_click(0.85, 0.90)
            time.sleep(1.5)

            # Headline 1
            self.browser.fill_form_field(0.30, 0.28, "Save 50% This Week Only")
            time.sleep(0.4)

            # Description
            self.browser.fill_form_field(0.30, 0.42, "Our premium plan is half off for new members. Claim now!")
            time.sleep(0.4)

            # Final "Create campaign" button (approx bottom-right)
            self.browser.win_click(0.88, 0.92)
            time.sleep(2.5)

            self._campaigns[campaign_id] = {
                "platform": "google",
                "budget": budget,
                "spent": 0.0,
                "clicks": 0,
                "impressions": 0,
                "ctr": 0.0,
                "cpc": 0.0,
                "bid": 1.0,
            }

            self.log(f"Google Ads campaign {campaign_id} created successfully.")
            return {
                "success": True,
                "campaign_id": campaign_id,
                "platform": "google",
                "budget_usd": budget,
                "revenue": 0.0,
                "costs": round(budget * 0.05, 2),
            }
        except Exception as e:
            self.log(f"Google Ads setup failed: {e}")
            return {"success": False, "error": str(e), "revenue": 0.0, "costs": 0.0}

    def _exec_check_performance(self, decision: AgentDecision) -> dict:
        """Simulate CTR/CPC metrics and update campaign P&L."""
        platform = decision.params.get("platform", "all")
        total_revenue = 0.0
        total_costs = 0.0
        reports: List[dict] = []

        for cid, camp in self._campaigns.items():
            if platform != "all" and camp.get("platform") != platform:
                continue

            # Simulate realistic metrics
            impressions = random.randint(500, 5000)
            ctr = round(random.uniform(0.5, 4.5), 2)
            clicks = int(impressions * (ctr / 100.0))
            cpc = round(random.uniform(0.30, 2.50), 2)
            spent = round(clicks * cpc, 2)
            conversions = int(clicks * random.uniform(0.02, 0.12))
            conversion_value = round(conversions * random.uniform(15.0, 80.0), 2)

            camp["impressions"] = impressions
            camp["clicks"] = clicks
            camp["ctr"] = ctr
            camp["cpc"] = cpc
            camp["spent"] = spent

            total_costs += spent
            total_revenue += conversion_value

            reports.append({
                "campaign_id": cid,
                "platform": camp["platform"],
                "impressions": impressions,
                "clicks": clicks,
                "ctr": f"{ctr}%",
                "cpc": f"${cpc}",
                "spent": f"${spent}",
                "conversions": conversions,
                "conversion_value": f"${conversion_value}",
            })

        self.log(
            f"Performance check ({platform}): {len(reports)} campaigns | "
            f"Revenue ${round(total_revenue, 2)} | Costs ${round(total_costs, 2)}"
        )
        return {
            "success": True,
            "platform": platform,
            "reports": reports,
            "revenue": round(total_revenue, 2),
            "costs": round(total_costs, 2),
        }

    def _exec_optimize_campaign(self, decision: AgentDecision) -> dict:
        """Adjust simulated bids for a target campaign."""
        cid = decision.params.get("campaign_id", "")
        adjustment = decision.params.get("bid_adjustment_pct", 0)

        camp = self._campaigns.get(cid)
        if not camp:
            # If campaign doesn't exist, create a dummy one so the agent stays useful
            camp = {
                "platform": "facebook",
                "budget": 20.0,
                "spent": 0.0,
                "clicks": 0,
                "impressions": 0,
                "ctr": 0.0,
                "cpc": 0.0,
                "bid": 1.0,
            }
            self._campaigns[cid] = camp

        old_bid = camp["bid"]
        new_bid = round(old_bid * (1 + adjustment / 100.0), 2)
        camp["bid"] = max(0.10, new_bid)

        self.log(
            f"Optimized campaign {cid}: bid ${old_bid} -> ${camp['bid']} ({adjustment}% change)"
        )
        return {
            "success": True,
            "campaign_id": cid,
            "old_bid": old_bid,
            "new_bid": camp["bid"],
            "revenue": 0.0,
            "costs": 0.0,
        }

    def _exec_screenshot_dashboard(self, decision: AgentDecision) -> dict:
        """Screenshot the ads dashboard for the chosen platform."""
        platform = decision.params.get("platform", "facebook")
        url = (
            "https://business.facebook.com/ads-manager"
            if platform == "facebook"
            else "https://ads.google.com/"
        )

        self.log(f"Screenshotting {platform} dashboard at {url}")
        try:
            self.browser.open_chrome(url=url, new_window=False)
            time.sleep(3.0)
            state = self.browser.screenshot(filename=f"{platform}_dashboard_{int(time.time())}.png")
            return {
                "success": True,
                "platform": platform,
                "screenshot_path": state.screenshot_path,
                "revenue": 0.0,
                "costs": 0.0,
            }
        except Exception as e:
            self.log(f"Screenshot failed: {e}")
            return {"success": False, "error": str(e), "revenue": 0.0, "costs": 0.0}
