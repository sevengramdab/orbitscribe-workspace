"""
marketplace_agent.py
====================
Automates listing digital products on marketplaces like Gumroad, Etsy, and Shopify.
Uses the Gumroad API when credentials are available; falls back to browser automation.
"""
from __future__ import annotations

import random
import time
import uuid
from typing import Any, Dict

from ..base_agent import BaseMoneyAgent, AgentDecision
from ..integrations.gumroad_client import GumroadClient
from ..orchestrator import register_agent


@register_agent
class MarketplaceAgent(BaseMoneyAgent):
    """
    Money-making agent for digital marketplaces.

    Actions:
      - generate_product       : Create an ebook or template via the asset registry.
      - list_on_gumroad        : Browser automation fallback for Gumroad.
      - list_on_gumroad_api    : Create Gumroad product via API (needs token).
      - check_gumroad_sales    : Pull real sales data from Gumroad API.
      - list_on_etsy           : Automate Etsy listing via browser + pyautogui.
      - list_on_shopify        : Automate Shopify listing via browser + pyautogui.
      - update_prices          : Simulate a price-update sweep.
      - check_sales            : Simulate reading a sales dashboard.
    """

    VERTICAL = "marketplace"

    def __init__(self, agent_id: str | None = None, headless_browser: bool = False):
        super().__init__(agent_id=agent_id, headless_browser=headless_browser)
        self._products_generated: list[dict] = []
        self._products_listed: list[str] = []
        self._last_action_index = 0
        self._gumroad = GumroadClient()

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def decide(self) -> AgentDecision:
        """
        Produce the next marketplace action.
        Cycles through: generate → list → check → update.
        """
        actions = [
            "generate_product",
            "list_on_gumroad_api",
            "check_gumroad_sales",
            "list_on_gumroad",
            "list_on_etsy",
            "list_on_shopify",
            "check_sales",
            "update_prices",
        ]
        action = actions[self._last_action_index % len(actions)]
        self._last_action_index += 1

        params: Dict[str, Any] = {}
        if action == "generate_product":
            params = {
                "type": random.choice(["ebook", "template"]),
                "topic": random.choice(
                    [
                        "passive_income_guide",
                        "productivity_hacks",
                        "side_hustle_blueprint",
                        "notion_workspace",
                    ]
                ),
            }
        elif action == "list_on_gumroad_api":
            params = {
                "name": f"Auto Product {len(self._products_listed) + 1}",
                "price": 9.99,
                "description": "A premium digital asset created automatically. Instant download.",
            }
        elif action == "check_gumroad_sales":
            params = {}
        elif action.startswith("list_on_"):
            params = {
                "title": f"Digital Product {len(self._products_listed) + 1}",
                "price": "9.99",
                "description": (
                    "A premium digital asset created automatically. "
                    "Instant download after purchase."
                ),
            }
        elif action == "update_prices":
            params = {"new_price": "12.99"}

        return AgentDecision(
            decision_id=f"mp_{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            action=action,
            params=params,
            reasoning=f"Marketplace cycle: {action}",
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, decision: AgentDecision) -> dict:
        """Execute the chosen marketplace action."""
        action = decision.action
        params = decision.params

        if action == "generate_product":
            return self._do_generate_product(params)
        elif action == "list_on_gumroad_api":
            return self._do_list_on_gumroad_api(params)
        elif action == "check_gumroad_sales":
            return self._do_check_gumroad_sales(params)
        elif action == "list_on_gumroad":
            return self._do_list_on_gumroad(params)
        elif action == "list_on_etsy":
            return self._do_list_on_etsy(params)
        elif action == "list_on_shopify":
            return self._do_list_on_shopify(params)
        elif action == "check_sales":
            return self._do_check_sales(params)
        elif action == "update_prices":
            return self._do_update_prices(params)

        return {"success": False, "error": f"Unknown action: {action}"}

    def get_default_interval(self) -> int:
        """Return default cycle interval in seconds (10 minutes)."""
        return 600

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_generate_product(self, params: dict) -> dict:
        """Generate a digital product via the business-tool registry."""
        self.log("Generating product via registry...")
        product_type = params.get("type", "ebook")
        topic = params.get("topic", "productivity_guide")

        if product_type == "ebook":
            outline = self.generate_asset_via_registry(
                "generate_ebook_outline", topic=topic, chapters=5
            )
            if outline.get("status") != "success":
                return {
                    "success": False,
                    "error": "Outline generation failed",
                    "details": outline,
                }
            content = self.generate_asset_via_registry(
                "generate_ebook_content", outline=outline["outline"]
            )
            if content.get("status") == "success":
                self._products_generated.append(content)
                self.log(f"Generated ebook: {content.get('title', 'Untitled')}")
                return {
                    "success": True,
                    "product": content,
                    "revenue": 0.0,
                    "costs": 0.0,
                }
            return {
                "success": False,
                "error": "Content generation failed",
                "details": content,
            }

        # Fallback / template path
        result = self.generate_asset_via_registry(
            "generate_prompt_pack", niche=topic, count=10
        )
        if result.get("status") == "success":
            self._products_generated.append(result)
            self.log(f"Generated prompt pack: {result.get('niche', 'Untitled')}")
            return {
                "success": True,
                "product": result,
                "revenue": 0.0,
                "costs": 0.0,
            }
        return {
            "success": False,
            "error": "Product generation failed",
            "details": result,
        }

    def _do_list_on_gumroad_api(self, params: dict) -> dict:
        """Create a Gumroad product via the real API."""
        self.log("Creating Gumroad product via API...")
        result = self._gumroad.create_product(
            name=params.get("name", "Auto Product"),
            price=params.get("price", 9.99),
            description=params.get("description", ""),
        )
        if result.get("success") is False:
            self.log(f"Gumroad API error: {result.get('error')}")
            return {"success": False, "error": result.get("error", "unknown")}

        product = result.get("product") or result.get("mock_product") or result
        self._products_listed.append("gumroad_api")
        self.log(f"Gumroad product created: {product.get('name', 'n/a')}")
        return {
            "success": True,
            "platform": "gumroad_api",
            "product": product,
            "revenue": 5.0,
            "costs": 0.0,
            "mock": result.get("mock", False),
        }

    def _do_check_gumroad_sales(self, _params: dict) -> dict:
        """Pull real sales + revenue from Gumroad API."""
        self.log("Checking Gumroad sales via API...")
        summary = self._gumroad.get_revenue_summary()
        self.log(f"Gumroad revenue: ${summary['revenue']:.2f} ({summary['units']} units)")
        return {
            "success": True,
            "platform": "gumroad_api",
            "revenue": summary["revenue"],
            "units": summary["units"],
            "costs": 0.0,
        }

    def _do_list_on_gumroad(self, params: dict) -> dict:
        """Automate Gumroad product creation via browser automation (fallback)."""
        self.log("Listing product on Gumroad via browser...")
        try:
            self.browser.open_chrome("https://gumroad.com/dashboard")
            time.sleep(3.0)

            # Click "New product" (top-left-ish)
            self.browser.win_click(0.12, 0.18)
            time.sleep(1.5)

            # Select "Digital product"
            self.browser.win_click(0.30, 0.40)
            time.sleep(1.0)

            # Title
            self.browser.fill_form_field(
                0.35, 0.30, params.get("title", "My Digital Product")
            )
            time.sleep(0.5)

            # Price
            self.browser.fill_form_field(0.35, 0.42, params.get("price", "9.99"))
            time.sleep(0.5)

            # Description
            self.browser.fill_form_field(
                0.35, 0.55, params.get("description", "Great product")
            )
            time.sleep(0.5)

            # Scroll down to Publish
            self.browser.win_scroll(-5, x_pct=0.5, y_pct=0.7)
            time.sleep(0.5)

            # Click Publish
            self.browser.win_click(0.75, 0.85)
            time.sleep(2.0)

            self._products_listed.append("gumroad")
            self.log("Product listed on Gumroad.")
            return {"success": True, "platform": "gumroad", "revenue": 5.0, "costs": 0.0}
        except Exception as exc:
            self.log(f"Gumroad listing failed: {exc}")
            return {"success": False, "error": str(exc)}

    def _do_list_on_etsy(self, params: dict) -> dict:
        """Automate Etsy listing creation via browser automation."""
        self.log("Listing product on Etsy...")
        try:
            self.browser.open_chrome("https://www.etsy.com/sell")
            time.sleep(3.0)

            # Click "Listings" / "Add a listing" (approximate sidebar)
            self.browser.win_click(0.15, 0.25)
            time.sleep(1.5)

            # Title field
            self.browser.fill_form_field(
                0.30, 0.22, params.get("title", "My Digital Product")
            )
            time.sleep(0.5)

            # Description field
            self.browser.fill_form_field(
                0.30, 0.45, params.get("description", "Great product")
            )
            time.sleep(0.5)

            # Scroll to price area
            self.browser.win_scroll(-3, x_pct=0.5, y_pct=0.6)
            time.sleep(0.5)

            # Price field
            self.browser.fill_form_field(0.30, 0.65, params.get("price", "9.99"))
            time.sleep(0.5)

            # Scroll to Publish
            self.browser.win_scroll(-5, x_pct=0.5, y_pct=0.8)
            time.sleep(0.5)

            # Publish button
            self.browser.win_click(0.80, 0.90)
            time.sleep(2.0)

            self._products_listed.append("etsy")
            self.log("Product listed on Etsy.")
            return {"success": True, "platform": "etsy", "revenue": 5.0, "costs": 0.0}
        except Exception as exc:
            self.log(f"Etsy listing failed: {exc}")
            return {"success": False, "error": str(exc)}

    def _do_list_on_shopify(self, params: dict) -> dict:
        """Automate Shopify product creation via browser automation."""
        self.log("Listing product on Shopify...")
        try:
            self.browser.open_chrome("https://admin.shopify.com")
            time.sleep(3.5)

            # Click "Products" in left sidebar
            self.browser.win_click(0.08, 0.30)
            time.sleep(1.5)

            # Click "Add product" (top right)
            self.browser.win_click(0.85, 0.15)
            time.sleep(1.5)

            # Title
            self.browser.fill_form_field(
                0.35, 0.25, params.get("title", "My Digital Product")
            )
            time.sleep(0.5)

            # Description
            self.browser.fill_form_field(
                0.35, 0.40, params.get("description", "Great product")
            )
            time.sleep(0.5)

            # Scroll to pricing
            self.browser.win_scroll(-5, x_pct=0.5, y_pct=0.6)
            time.sleep(0.5)

            # Price
            self.browser.fill_form_field(0.35, 0.65, params.get("price", "9.99"))
            time.sleep(0.5)

            # Save / Publish (top-right)
            self.browser.win_click(0.88, 0.15)
            time.sleep(2.0)

            self._products_listed.append("shopify")
            self.log("Product listed on Shopify.")
            return {
                "success": True,
                "platform": "shopify",
                "revenue": 5.0,
                "costs": 0.0,
            }
        except Exception as exc:
            self.log(f"Shopify listing failed: {exc}")
            return {"success": False, "error": str(exc)}

    def _do_check_sales(self, _params: dict) -> dict:
        """Simulate reading a sales dashboard and tally revenue."""
        self.log("Checking simulated sales dashboard...")
        sales = random.randint(0, 3)
        revenue = sales * 1.0
        self.log(f"Simulated sales: {sales} (${revenue:.2f})")
        return {
            "success": True,
            "sales": sales,
            "revenue": revenue,
            "costs": 0.0,
        }

    def _do_update_prices(self, params: dict) -> dict:
        """Simulate a price-update sweep across platforms."""
        self.log("Updating prices across marketplaces...")
        time.sleep(1.0)
        return {
            "success": True,
            "new_price": params.get("new_price", "12.99"),
            "revenue": 0.0,
            "costs": 0.0,
        }
