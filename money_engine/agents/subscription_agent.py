"""
subscription_agent.py
=====================
Newsletter and subscription product management agent.
Automates content generation, publishing to Substack/Medium,
and tracks simulated subscriber revenue.
"""
from __future__ import annotations

import time
import random
from typing import Any, Dict, List

from money_engine.base_agent import BaseMoneyAgent, AgentDecision
from money_engine.orchestrator import register_agent


@register_agent
class SubscriptionAgent(BaseMoneyAgent):
    """Agent that manages newsletter and subscription products."""

    VERTICAL = "subscriptions"

    # Simulated pricing
    REVENUE_PER_SUBSCRIBER_GAINED = 0.50
    REVENUE_PER_NEWSLETTER = 2.00

    def __init__(self, agent_id=None, headless_browser: bool = False):
        super().__init__(agent_id=agent_id, headless_browser=headless_browser)
        self._subscriber_count = self._load_subscriber_count()
        self._newsletters_sent = self._load_newsletters_sent()
        self._action_index = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_subscriber_count(self) -> int:
        return getattr(self.state, "subscriber_count", 0) if hasattr(self.state, "subscriber_count") else 0

    def _save_subscriber_count(self):
        self.state.subscriber_count = self._subscriber_count

    def _load_newsletters_sent(self) -> int:
        return getattr(self.state, "newsletters_sent", 0) if hasattr(self.state, "newsletters_sent") else 0

    def _save_newsletters_sent(self):
        self.state.newsletters_sent = self._newsletters_sent

    def _next_action(self) -> str:
        actions = [
            "generate_newsletter",
            "generate_twitter_thread",
            "publish_to_substack",
            "publish_to_medium",
            "check_subscribers",
            "screenshot_growth",
        ]
        action = actions[self._action_index % len(actions)]
        self._action_index += 1
        return action

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def decide(self) -> AgentDecision:
        action = self._next_action()

        if action == "generate_newsletter":
            params = {
                "subject": "Weekly insights on AI automation",
                "topics": ["AI tools", "revenue growth", "automation tips"],
                "cta": "Subscribe for more weekly insights!",
            }
            reasoning = "Time to generate a new newsletter issue to keep subscribers engaged."

        elif action == "generate_twitter_thread":
            params = {
                "topic": "How to automate your online business",
                "tweets_count": 5,
                "cta": "Follow for daily automation tips.",
            }
            reasoning = "Generate a Twitter thread to drive traffic to the newsletter."

        elif action == "publish_to_substack":
            params = {
                "title": "The Automation Blueprint #" + str(self._newsletters_sent + 1),
                "body": "(newsletter body will be injected after generation)",
            }
            reasoning = "Publish the latest newsletter to Substack."

        elif action == "publish_to_medium":
            params = {
                "title": "The Automation Blueprint #" + str(self._newsletters_sent + 1),
                "body": "(newsletter body will be injected after generation)",
            }
            reasoning = "Republish the newsletter on Medium for wider reach."

        elif action == "check_subscribers":
            params = {}
            reasoning = "Simulate subscriber growth check."

        elif action == "screenshot_growth":
            params = {}
            reasoning = "Capture a screenshot of the subscriber growth dashboard."

        else:
            params = {}
            reasoning = "Default fallback decision."

        return AgentDecision(
            decision_id=f"sub_{int(time.time())}_{random.randint(1000,9999)}",
            timestamp=time.time(),
            action=action,
            params=params,
            reasoning=reasoning,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, decision: AgentDecision) -> dict:
        action = decision.action
        params = decision.params

        if action == "generate_newsletter":
            return self._exec_generate_newsletter(params)

        if action == "generate_twitter_thread":
            return self._exec_generate_twitter_thread(params)

        if action == "publish_to_substack":
            return self._exec_publish_to_substack(params)

        if action == "publish_to_medium":
            return self._exec_publish_to_medium(params)

        if action == "check_subscribers":
            return self._exec_check_subscribers(params)

        if action == "screenshot_growth":
            return self._exec_screenshot_growth(params)

        return {"success": False, "error": f"Unknown action: {action}"}

    # -- action implementations ------------------------------------------

    def _exec_generate_newsletter(self, params: dict) -> dict:
        self.log("Generating newsletter via registry...")
        result = self.generate_asset_via_registry(
            "generate_newsletter",
            subject=params.get("subject", "Weekly Update"),
            topics=params.get("topics", ["general"]),
            cta=params.get("cta", "Stay tuned!"),
        )
        revenue = self.REVENUE_PER_NEWSLETTER
        self._newsletters_sent += 1
        self._save_newsletters_sent()
        self.log(f"Newsletter generated. Revenue: ${revenue:.2f}")
        return {
            "success": result.get("success", False),
            "revenue": revenue,
            "costs": 0.0,
            "result": result,
            "newsletters_sent": self._newsletters_sent,
        }

    def _exec_generate_twitter_thread(self, params: dict) -> dict:
        self.log("Generating Twitter thread via registry...")
        result = self.generate_asset_via_registry(
            "generate_twitter_thread",
            topic=params.get("topic", "AI automation"),
            tweets_count=params.get("tweets_count", 5),
            cta=params.get("cta", "Follow for more!"),
        )
        self.log("Twitter thread generated.")
        return {
            "success": result.get("success", False),
            "revenue": 0.0,
            "costs": 0.0,
            "result": result,
        }

    def _exec_publish_to_substack(self, params: dict) -> dict:
        self.log("Publishing to Substack via browser...")
        try:
            self.browser.open_chrome("https://substack.com", new_window=False)
            time.sleep(3.0)

            # Click "Write" — approximate top-left area of Substack nav
            self.browser.win_click(0.85, 0.08)
            time.sleep(2.0)

            # Fill title
            self.browser.fill_form_field(0.30, 0.20, params.get("title", "New Post"))
            time.sleep(0.5)

            # Fill body — click body area and type
            self.browser.click_text_field(0.30, 0.35, clear=True)
            body = params.get("body", "")
            if body:
                self.browser.win_type(body)
            time.sleep(0.5)

            # Click publish — approximate bottom-right of editor
            self.browser.win_click(0.90, 0.92)
            time.sleep(2.0)

            self.log("Substack publish sequence completed.")
            return {"success": True, "revenue": 0.0, "costs": 0.0, "platform": "substack"}
        except Exception as e:
            self.log(f"Substack publish failed: {e}")
            return {"success": False, "error": str(e), "revenue": 0.0, "costs": 0.0}

    def _exec_publish_to_medium(self, params: dict) -> dict:
        self.log("Publishing to Medium via browser...")
        try:
            self.browser.open_chrome("https://medium.com/new-story", new_window=False)
            time.sleep(3.0)

            # Medium title field
            self.browser.fill_form_field(0.25, 0.18, params.get("title", "New Story"))
            time.sleep(0.5)

            # Medium body field
            self.browser.click_text_field(0.25, 0.30, clear=True)
            body = params.get("body", "")
            if body:
                self.browser.win_type(body)
            time.sleep(0.5)

            # Click publish — top-right corner
            self.browser.win_click(0.92, 0.08)
            time.sleep(1.5)

            # Confirm publish in modal
            self.browser.win_click(0.60, 0.60)
            time.sleep(1.0)

            self.log("Medium publish sequence completed.")
            return {"success": True, "revenue": 0.0, "costs": 0.0, "platform": "medium"}
        except Exception as e:
            self.log(f"Medium publish failed: {e}")
            return {"success": False, "error": str(e), "revenue": 0.0, "costs": 0.0}

    def _exec_check_subscribers(self, params: dict) -> dict:
        self.log("Checking simulated subscriber growth...")
        gained = random.randint(1, 10)
        self._subscriber_count += gained
        self._save_subscriber_count()
        revenue = gained * self.REVENUE_PER_SUBSCRIBER_GAINED
        self.log(f"Subscribers gained: {gained} (total: {self._subscriber_count}). Revenue: ${revenue:.2f}")
        return {
            "success": True,
            "revenue": revenue,
            "costs": 0.0,
            "subscribers_gained": gained,
            "total_subscribers": self._subscriber_count,
        }

    def _exec_screenshot_growth(self, params: dict) -> dict:
        self.log("Taking growth dashboard screenshot...")
        try:
            state = self.browser.screenshot(filename=f"sub_growth_{int(time.time())}.png")
            path = state.screenshot_path
            self.log(f"Screenshot saved: {path}")
            return {"success": True, "revenue": 0.0, "costs": 0.0, "screenshot_path": path}
        except Exception as e:
            self.log(f"Screenshot failed: {e}")
            return {"success": False, "error": str(e), "revenue": 0.0, "costs": 0.0}

    # ------------------------------------------------------------------
    # Interval
    # ------------------------------------------------------------------

    def get_default_interval(self) -> int:
        return 500
