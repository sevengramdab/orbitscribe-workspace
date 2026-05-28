"""
dropshipping_agent.py
=====================
Automates dropshipping tasks:
- Product research via browser (Printify / AliExpress)
- Listing creation with generated descriptions
- Price monitoring and updates
- Inventory simulation
- Dashboard screenshots
"""
from __future__ import annotations

import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from money_engine.base_agent import AgentDecision, BaseMoneyAgent
from money_engine.orchestrator import register_agent


@register_agent
class DropshippingAgent(BaseMoneyAgent):
    """Agent that automates dropshipping operations."""

    VERTICAL = "dropshipping"

    # Paths
    PRODUCTS_DIR = Path(__file__).parent.parent.parent / "products" / "dropshipping"
    DASHBOARD_DIR = Path(__file__).parent.parent.parent / "screenshots"

    # Simulated economics
    RESEARCH_COST = 0.50
    LISTING_COST = 1.00
    PRICE_UPDATE_COST = 0.10
    INVENTORY_CHECK_COST = 0.05
    AVG_PROFIT_PER_SALE = 8.50

    def __init__(self, agent_id: str | None = None, headless_browser: bool = False):
        super().__init__(agent_id=agent_id, headless_browser=headless_browser)
        self.PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
        self.DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def decide(self) -> AgentDecision:
        """Choose the next action based on current state."""
        actions = [
            "research_products",
            "create_listing",
            "update_prices",
            "check_inventory",
            "screenshot_dashboard",
        ]

        # Weight toward research if we have few listings
        listings = self._list_existing_listings()
        if len(listings) < 3:
            weights = [0.50, 0.20, 0.10, 0.10, 0.10]
        elif len(listings) < 8:
            weights = [0.20, 0.30, 0.25, 0.15, 0.10]
        else:
            weights = [0.10, 0.10, 0.40, 0.25, 0.15]

        action = random.choices(actions, weights=weights, k=1)[0]

        params: Dict[str, Any] = {}
        if action == "research_products":
            site = random.choice(["https://printify.com", "https://aliexpress.com"])
            params = {"site": site, "category": random.choice(["apparel", "home", "electronics", "accessories"])}
        elif action == "create_listing":
            params = {"category": random.choice(["apparel", "home", "electronics", "accessories"])}
        elif action == "update_prices":
            params = {"adjustment_pct": round(random.uniform(-5.0, 10.0), 2)}
        elif action == "check_inventory":
            params = {"listings": [l["sku"] for l in listings[:5]]}
        elif action == "screenshot_dashboard":
            params = {"filename": f"dropshipping_dashboard_{int(time.time())}.png"}

        return AgentDecision(
            decision_id=f"ds_{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            action=action,
            params=params,
            reasoning=f"Weighted decision selected '{action}' with {len(listings)} existing listings.",
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, decision: AgentDecision) -> dict:
        """Execute the chosen action."""
        action = decision.action
        params = decision.params

        self.log(f"Executing dropshipping action: {action}")

        if action == "research_products":
            return self._execute_research(params)
        elif action == "create_listing":
            return self._execute_create_listing(params)
        elif action == "update_prices":
            return self._execute_update_prices(params)
        elif action == "check_inventory":
            return self._execute_check_inventory(params)
        elif action == "screenshot_dashboard":
            return self._execute_screenshot_dashboard(params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def get_default_interval(self) -> int:
        """Return default cycle interval in seconds (15 minutes)."""
        return 900

    # ------------------------------------------------------------------
    # Internal action implementations
    # ------------------------------------------------------------------

    def _execute_research(self, params: dict) -> dict:
        """Open a supplier site and simulate browsing."""
        site = params.get("site", "https://printify.com")
        category = params.get("category", "apparel")

        try:
            self.browser.open_chrome(url=site, new_window=False)
            time.sleep(2.0)
            self.browser.focus_chrome()
            time.sleep(0.5)

            # Simulate scrolling to browse products
            for _ in range(random.randint(2, 5)):
                self.browser.win_scroll(-random.randint(300, 700), x_pct=0.5, y_pct=0.6)
                time.sleep(0.8)

            # Screenshot the results
            shot = self.browser.screenshot(filename=f"ds_research_{int(time.time())}.png")

            # Simulate finding a product idea
            product_idea = self._generate_product_idea(category)

            return {
                "success": True,
                "action": "research_products",
                "site": site,
                "category": category,
                "product_idea": product_idea,
                "screenshot": shot.screenshot_path,
                "costs": self.RESEARCH_COST,
                "revenue": 0.0,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "costs": self.RESEARCH_COST, "revenue": 0.0}

    def _execute_create_listing(self, params: dict) -> dict:
        """Generate a product description and save it to products/dropshipping/."""
        category = params.get("category", "apparel")
        product = self._generate_product_idea(category)
        sku = f"DS-{uuid.uuid4().hex[:6].upper()}"

        listing = {
            "sku": sku,
            "title": product["title"],
            "category": category,
            "description": product["description"],
            "base_cost": round(product["base_cost"], 2),
            "sale_price": round(product["base_cost"] * random.uniform(1.4, 2.2), 2),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "agent_id": self.agent_id,
        }

        filepath = self.PRODUCTS_DIR / f"{sku}.json"
        try:
            filepath.write_text(json.dumps(listing, indent=2), encoding="utf-8")
            self.log(f"Created listing {sku}: {listing['title']} @ ${listing['sale_price']}")

            return {
                "success": True,
                "action": "create_listing",
                "sku": sku,
                "filepath": str(filepath),
                "listing": listing,
                "costs": self.LISTING_COST,
                "revenue": 0.0,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "costs": self.LISTING_COST, "revenue": 0.0}

    def _execute_update_prices(self, params: dict) -> dict:
        """Read existing listings and adjust prices."""
        listings = self._list_existing_listings()
        if not listings:
            return {"success": True, "action": "update_prices", "updated": 0, "costs": self.PRICE_UPDATE_COST, "revenue": 0.0}

        adjustment_pct = params.get("adjustment_pct", random.uniform(-2.0, 5.0))
        updated = 0
        changes = []

        for listing in listings:
            old_price = listing.get("sale_price", 0.0)
            new_price = round(old_price * (1 + adjustment_pct / 100), 2)
            listing["sale_price"] = max(new_price, listing.get("base_cost", 0.0) * 1.1)
            listing["last_price_update"] = time.strftime("%Y-%m-%dT%H:%M:%S")

            filepath = self.PRODUCTS_DIR / f"{listing['sku']}.json"
            try:
                filepath.write_text(json.dumps(listing, indent=2), encoding="utf-8")
                changes.append({"sku": listing["sku"], "old": old_price, "new": listing["sale_price"]})
                updated += 1
            except Exception as e:
                self.log(f"Failed to update {listing['sku']}: {e}")

        self.log(f"Updated prices for {updated} listings (adjustment {adjustment_pct}%)")
        return {
            "success": True,
            "action": "update_prices",
            "updated": updated,
            "adjustment_pct": adjustment_pct,
            "changes": changes,
            "costs": self.PRICE_UPDATE_COST,
            "revenue": 0.0,
        }

    def _execute_check_inventory(self, params: dict) -> dict:
        """Simulate checking inventory levels for listings."""
        skus = params.get("listings", [])
        if not skus:
            listings = self._list_existing_listings()
            skus = [l["sku"] for l in listings[:5]]

        inventory = {}
        for sku in skus:
            stock = random.randint(0, 100)
            status = "in_stock" if stock > 10 else "low_stock" if stock > 0 else "out_of_stock"
            inventory[sku] = {"stock": stock, "status": status}

        self.log(f"Checked inventory for {len(skus)} items.")
        return {
            "success": True,
            "action": "check_inventory",
            "inventory": inventory,
            "costs": self.INVENTORY_CHECK_COST,
            "revenue": 0.0,
        }

    def _execute_screenshot_dashboard(self, params: dict) -> dict:
        """Take a dashboard screenshot and optionally simulate a sale."""
        filename = params.get("filename", f"ds_dashboard_{int(time.time())}.png")
        try:
            self.browser.focus_chrome()
            shot = self.browser.screenshot(filename=filename)

            # Occasionally simulate a sale when viewing dashboard
            revenue = 0.0
            if random.random() < 0.15:
                revenue = self.AVG_PROFIT_PER_SALE * random.uniform(0.5, 1.5)
                revenue = round(revenue, 2)
                self.log(f"Simulated sale on dashboard view: +${revenue}")

            return {
                "success": True,
                "action": "screenshot_dashboard",
                "screenshot": shot.screenshot_path,
                "costs": 0.0,
                "revenue": revenue,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "costs": 0.0, "revenue": 0.0}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _list_existing_listings(self) -> List[dict]:
        """Read all JSON listings from products/dropshipping/."""
        listings = []
        if not self.PRODUCTS_DIR.exists():
            return listings
        for filepath in self.PRODUCTS_DIR.glob("DS-*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                listings.append(data)
            except Exception:
                continue
        return listings

    def _generate_product_idea(self, category: str) -> dict:
        """Generate a fake but realistic product idea."""
        templates = {
            "apparel": [
                ("Vintage Graphic Tee", "Soft cotton unisex tee with retro-inspired print.", 6.50),
                ("Eco Hoodie", "Sustainable fleece hoodie, minimal branding.", 14.00),
                ("Athletic Joggers", "Moisture-wicking tapered joggers with zip pockets.", 12.00),
            ],
            "home": [
                ("Aromatherapy Candle", "Soy wax candle with lavender and eucalyptus notes.", 5.00),
                ("Minimalist Wall Clock", "Silent sweep mechanism, matte black finish.", 9.00),
                ("Organic Throw Blanket", "Knitted cotton blanket, 50x60 inches.", 11.00),
            ],
            "electronics": [
                ("LED Desk Lamp", "Dimmable USB-C lamp with touch controls.", 8.50),
                ("Phone Stand", "Aluminum foldable stand, adjustable angle.", 4.00),
                ("Cable Organizer Set", "Silicone ties and magnetic clips, 12-pack.", 3.50),
            ],
            "accessories": [
                ("RFID Blocking Wallet", "Slim bifold with card-slide mechanism.", 7.00),
                ("Polarized Sunglasses", "UV400 protection, wayfarer style.", 6.00),
                ("Canvas Tote Bag", "Heavy-duty 12oz canvas with interior pocket.", 5.50),
            ],
        }
        items = templates.get(category, templates["apparel"])
        title, desc, base_cost = random.choice(items)
        return {"title": title, "description": desc, "base_cost": base_cost}
