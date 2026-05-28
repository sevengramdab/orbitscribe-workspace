"""
licensing_agent.py
==================
Automates code/template/asset licensing.
- Generates code templates and prompt packs via the business-tool registry
- Lists products on Gumroad and Etsy via browser automation
- Tracks simulated sales revenue ($3 per template, $1 per prompt pack)
- Updates license metadata and checks for new sales
"""
from __future__ import annotations

import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import BaseMoneyAgent, AgentDecision
from ..orchestrator import register_agent


@register_agent
class LicensingAgent(BaseMoneyAgent):
    """Agent that creates digital assets and licenses them on marketplaces."""

    VERTICAL = "licensing"

    # Pricing simulation constants
    TEMPLATE_PRICE = 3.0
    PROMPT_PACK_PRICE = 1.0

    def __init__(self, agent_id: Optional[str] = None, headless_browser: bool = False):
        super().__init__(agent_id=agent_id, headless_browser=headless_browser)
        self.assets_dir = Path(__file__).parent.parent / "products" / "assets" / "licensing"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self._sales_log_path = self.assets_dir / "_sales_log.json"

    # ------------------------------------------------------------------
    # Decision loop
    # ------------------------------------------------------------------

    def decide(self) -> AgentDecision:
        """
        Choose the next action based on current asset inventory and cycle state.
        Actions: generate_code_template, generate_prompt_pack, list_on_gumroad,
                 list_on_etsy, update_licenses, check_sales
        """
        assets = self._scan_assets()
        unlisted = [a for a in assets if not a.get("listed", False)]
        action: str
        params: Dict[str, Any] = {}
        reasoning: str

        # Priorities:
        # 1. If we have unlisted assets, list them (alternate platforms)
        # 2. If inventory is low, generate something new
        # 3. Otherwise check sales / update licenses

        if unlisted:
            # Pick a platform based on asset type and randomness
            asset = random.choice(unlisted)
            platform = "gumroad" if random.random() < 0.5 else "etsy"
            action = f"list_on_{platform}"
            params = {
                "asset_path": str(asset["path"]),
                "title": asset.get("title", "Untitled Asset"),
                "description": asset.get("description", ""),
                "price": asset.get("price", 5.0),
            }
            reasoning = f"Asset '{asset['title']}' is unlisted; creating {platform} listing."

        elif len(assets) < 3:
            # Low inventory — generate a new asset
            if random.random() < 0.6:
                action = "generate_code_template"
                params = {
                    "project_type": random.choice(["react", "flask", "cli", "chrome_extension"]),
                    "features": random.sample(
                        ["auth", "payments", "dashboard", "api", "testing", "ci_cd"],
                        k=random.randint(1, 3),
                    ),
                }
                reasoning = "Low inventory; generating a new code template."
            else:
                action = "generate_prompt_pack"
                params = {
                    "theme": random.choice(["seo", "coding", "design", "marketing", "copywriting"]),
                    "count": random.randint(5, 15),
                }
                reasoning = "Low inventory; generating a new prompt pack."

        else:
            # Healthy inventory — maintenance actions
            action = random.choice(["check_sales", "update_licenses", "check_sales"])
            if action == "check_sales":
                reasoning = "Periodic sales check to update revenue ledger."
            else:
                reasoning = "Periodic license metadata refresh for all assets."

        return AgentDecision(
            decision_id=f"lic_{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            action=action,
            params=params,
            reasoning=reasoning,
        )

    def execute(self, decision: AgentDecision) -> dict:
        """Execute the chosen licensing action."""
        action = decision.action
        params = decision.params

        if action == "generate_code_template":
            return self._exec_generate_code_template(params)

        if action == "generate_prompt_pack":
            return self._exec_generate_prompt_pack(params)

        if action == "list_on_gumroad":
            return self._exec_list_on_platform("gumroad", params)

        if action == "list_on_etsy":
            return self._exec_list_on_platform("etsy", params)

        if action == "update_licenses":
            return self._exec_update_licenses()

        if action == "check_sales":
            return self._exec_check_sales()

        return {"success": False, "error": f"Unknown action: {action}"}

    def get_default_interval(self) -> int:
        """Return default cycle interval in seconds (15 minutes)."""
        return 900

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    def _exec_generate_code_template(self, params: dict) -> dict:
        """Generate a code template via the business-tool registry."""
        project_type = params.get("project_type", "generic")
        features = params.get("features", [])
        self.log(f"Generating code template: {project_type} with features {features}")

        result = self.generate_asset_via_registry(
            "generate_code_template",
            project_type=project_type,
            features=features,
        )

        if result.get("success"):
            # Save asset metadata locally
            asset_id = f"template_{uuid.uuid4().hex[:6]}"
            asset_meta = {
                "id": asset_id,
                "type": "code_template",
                "project_type": project_type,
                "features": features,
                "title": f"{project_type.title()} Starter Template",
                "description": f"Production-ready {project_type} template including {', '.join(features)}.",
                "price": self.TEMPLATE_PRICE,
                "listed": False,
                "platforms": [],
                "created_at": time.time(),
                "registry_result": result,
            }
            self._save_asset(asset_id, asset_meta)
            return {"success": True, "asset_id": asset_id, "revenue": 0.0, "costs": 0.0}

        # Fallback: create a placeholder asset file so the agent can still list it
        asset_id = f"template_{uuid.uuid4().hex[:6]}"
        placeholder_path = self.assets_dir / f"{asset_id}.zip"
        placeholder_path.write_text("# Placeholder code template\n", encoding="utf-8")
        asset_meta = {
            "id": asset_id,
            "type": "code_template",
            "project_type": project_type,
            "features": features,
            "title": f"{project_type.title()} Starter Template",
            "description": f"Production-ready {project_type} template including {', '.join(features)}.",
            "price": self.TEMPLATE_PRICE,
            "listed": False,
            "platforms": [],
            "created_at": time.time(),
            "path": str(placeholder_path),
        }
        self._save_asset(asset_id, asset_meta)
        self.log(f"Registry fallback: created placeholder {asset_id}")
        return {"success": True, "asset_id": asset_id, "revenue": 0.0, "costs": 0.0, "fallback": True}

    def _exec_generate_prompt_pack(self, params: dict) -> dict:
        """Generate a prompt pack via the business-tool registry."""
        theme = params.get("theme", "general")
        count = params.get("count", 10)
        self.log(f"Generating prompt pack: {theme} ({count} prompts)")

        result = self.generate_asset_via_registry(
            "generate_prompt_pack",
            theme=theme,
            count=count,
        )

        if result.get("success"):
            asset_id = f"prompts_{uuid.uuid4().hex[:6]}"
            asset_meta = {
                "id": asset_id,
                "type": "prompt_pack",
                "theme": theme,
                "count": count,
                "title": f"{theme.title()} AI Prompt Pack ({count} prompts)",
                "description": f"Curated collection of {count} high-converting {theme} prompts for ChatGPT, Claude, and Midjourney.",
                "price": self.PROMPT_PACK_PRICE,
                "listed": False,
                "platforms": [],
                "created_at": time.time(),
                "registry_result": result,
            }
            self._save_asset(asset_id, asset_meta)
            return {"success": True, "asset_id": asset_id, "revenue": 0.0, "costs": 0.0}

        # Fallback placeholder
        asset_id = f"prompts_{uuid.uuid4().hex[:6]}"
        placeholder_path = self.assets_dir / f"{asset_id}.txt"
        placeholder_path.write_text(f"# {theme.title()} Prompt Pack ({count} prompts)\n", encoding="utf-8")
        asset_meta = {
            "id": asset_id,
            "type": "prompt_pack",
            "theme": theme,
            "count": count,
            "title": f"{theme.title()} AI Prompt Pack ({count} prompts)",
            "description": f"Curated collection of {count} high-converting {theme} prompts.",
            "price": self.PROMPT_PACK_PRICE,
            "listed": False,
            "platforms": [],
            "created_at": time.time(),
            "path": str(placeholder_path),
        }
        self._save_asset(asset_id, asset_meta)
        self.log(f"Registry fallback: created placeholder {asset_id}")
        return {"success": True, "asset_id": asset_id, "revenue": 0.0, "costs": 0.0, "fallback": True}

    def _exec_list_on_platform(self, platform: str, params: dict) -> dict:
        """Open the platform in Chrome and attempt to create a listing."""
        title = params.get("title", "Untitled")
        description = params.get("description", "")
        price = params.get("price", 5.0)
        asset_path = params.get("asset_path", "")
        self.log(f"Listing '{title}' on {platform} for ${price}")

        url_map = {
            "gumroad": "https://gumroad.com/",
            "etsy": "https://www.etsy.com/sell",
        }
        url = url_map.get(platform, f"https://{platform}.com")

        # Open browser and navigate
        self.browser.open_chrome(url=url, new_window=False)
        time.sleep(3.0)

        # Attempt basic form interaction using safe browser actions.
        # These are heuristic coordinates; the agent logs what it does.
        try:
            if platform == "gumroad":
                # Navigate to product creation page
                self.browser.navigate("https://gumroad.com/products")
                time.sleep(2.5)
                # Click "New product" (approximate top-right area)
                self.browser.win_click(0.85, 0.12)
                time.sleep(1.5)
                # Fill title (approximate first field)
                self.browser.fill_form_field(0.30, 0.25, title)
                time.sleep(0.5)
                # Fill description (approximate text area)
                self.browser.fill_form_field(0.30, 0.40, description)
                time.sleep(0.5)
                # Price field (approximate)
                self.browser.fill_form_field(0.30, 0.55, str(price))
                time.sleep(0.5)
                # Note: actual save/publish would require more specific Gumroad UI knowledge
                self.log(f"Gumroad listing form filled for '{title}' (manual publish may be required)")

            elif platform == "etsy":
                self.browser.navigate("https://www.etsy.com/your/shop/listings/create")
                time.sleep(3.0)
                # Title field (approximate)
                self.browser.fill_form_field(0.25, 0.18, title)
                time.sleep(0.5)
                # Description field (approximate)
                self.browser.fill_form_field(0.25, 0.30, description)
                time.sleep(0.5)
                # Price field (approximate)
                self.browser.fill_form_field(0.25, 0.50, str(price))
                time.sleep(0.5)
                self.log(f"Etsy listing form filled for '{title}' (manual publish may be required)")
        except Exception as e:
            self.log(f"Browser automation encountered an issue: {e}")
            # Non-fatal: mark as attempted so we don't loop forever

        # Update local asset metadata to reflect listing attempt
        asset_id = self._find_asset_id_by_path(asset_path)
        if asset_id:
            meta = self._load_asset(asset_id)
            meta["listed"] = True
            meta.setdefault("platforms", []).append(platform)
            self._save_asset(asset_id, meta)

        return {
            "success": True,
            "platform": platform,
            "title": title,
            "price": price,
            "revenue": 0.0,
            "costs": 0.0,
        }

    def _exec_update_licenses(self) -> dict:
        """Scan all local assets and refresh license metadata."""
        assets = self._scan_assets()
        updated = 0
        for asset in assets:
            asset_id = asset.get("id")
            if not asset_id:
                continue
            meta = self._load_asset(asset_id)
            meta["license_version"] = "1.0"
            meta["license_type"] = "standard_digital"
            meta["last_updated"] = time.time()
            self._save_asset(asset_id, meta)
            updated += 1

        self.log(f"Updated license metadata for {updated} assets")
        return {"success": True, "updated": updated, "revenue": 0.0, "costs": 0.0}

    def _exec_check_sales(self) -> dict:
        """Simulate checking marketplace sales and record revenue."""
        assets = self._scan_assets()
        listed_assets = [a for a in assets if a.get("listed", False)]
        if not listed_assets:
            self.log("No listed assets yet; simulated sales = 0")
            return {"success": True, "sales": 0, "revenue": 0.0, "costs": 0.0}

        # Simulate a small chance of sale per listed asset
        total_revenue = 0.0
        sales_log: List[dict] = []
        for asset in listed_assets:
            if random.random() < 0.15:  # 15% chance of a sale per cycle
                price = asset.get("price", 0.0)
                total_revenue += price
                sales_log.append({
                    "asset_id": asset["id"],
                    "asset_type": asset.get("type", "unknown"),
                    "price": price,
                    "timestamp": time.time(),
                })
                self.log(f"Simulated sale: {asset['title']} for ${price}")

        if sales_log:
            existing = self._load_sales_log()
            existing.extend(sales_log)
            self._save_sales_log(existing)

        self.log(f"Simulated sales check complete: ${total_revenue:.2f} revenue")
        return {"success": True, "sales": len(sales_log), "revenue": total_revenue, "costs": 0.0}

    # ------------------------------------------------------------------
    # Local asset helpers
    # ------------------------------------------------------------------

    def _asset_meta_path(self, asset_id: str) -> Path:
        return self.assets_dir / f"{asset_id}.json"

    def _save_asset(self, asset_id: str, meta: dict):
        self._asset_meta_path(asset_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _load_asset(self, asset_id: str) -> dict:
        path = self._asset_meta_path(asset_id)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _scan_assets(self) -> List[dict]:
        assets = []
        for path in self.assets_dir.glob("*.json"):
            if path.name.startswith("_"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                data.setdefault("path", str(path.with_suffix("")))
                assets.append(data)
            except Exception:
                continue
        return assets

    def _find_asset_id_by_path(self, asset_path: str) -> Optional[str]:
        for asset in self._scan_assets():
            if str(asset.get("path", "")) == asset_path or asset.get("id", "") in asset_path:
                return asset.get("id")
        return None

    def _load_sales_log(self) -> List[dict]:
        if self._sales_log_path.exists():
            try:
                return json.loads(self._sales_log_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_sales_log(self, log: List[dict]):
        self._sales_log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
