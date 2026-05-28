"""
saas_agent.py
=============
Money Engine agent for building and deploying micro-SaaS applications.

Actions:
- generate_app : scaffold a new micro-SaaS via the business-tool registry
- deploy_app   : simulate deployment on Render / Railway via browser automation
- update_app   : patch an existing app in products/apps/
- check_analytics: simulate reading usage stats and accrue revenue
- screenshot_app : capture a screenshot of the deployed app
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from money_engine.base_agent import BaseMoneyAgent, AgentDecision
from money_engine.orchestrator import register_agent


APP_DIR = Path(__file__).parent.parent.parent / "products" / "apps"
APP_REGISTRY_PATH = APP_DIR / "saas_registry.json"

# Simulated economics
REVENUE_PER_DEPLOYMENT = 10.0
REVENUE_PER_USER = 0.50


@register_agent
class SaaSAgent(BaseMoneyAgent):
    """Agent that builds and deploys micro-SaaS apps for revenue."""

    VERTICAL = "saas"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def __init__(self, agent_id: Optional[str] = None, headless_browser: bool = False):
        super().__init__(agent_id=agent_id, headless_browser=headless_browser)
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self._apps = self._load_app_registry()

    # ------------------------------------------------------------------
    # App registry helpers
    # ------------------------------------------------------------------
    def _load_app_registry(self) -> List[Dict[str, Any]]:
        if APP_REGISTRY_PATH.exists():
            try:
                return json.loads(APP_REGISTRY_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_app_registry(self):
        APP_REGISTRY_PATH.write_text(json.dumps(self._apps, indent=2), encoding="utf-8")

    def _next_app_name(self, app_type: str) -> str:
        count = len([a for a in self._apps if a["app_type"] == app_type]) + 1
        return f"{app_type}_{count}"

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------
    def decide(self) -> AgentDecision:
        """Choose the next SaaS action based on current portfolio state."""
        decision_id = f"saas_{uuid.uuid4().hex[:8]}"
        ts = time.time()

        if not self._apps:
            action = "generate_app"
            params = {"app_type": "url_shortener", "tech_stack": "flask"}
            reasoning = "Portfolio empty. Generate first micro-SaaS."
        else:
            # Cycle through mature actions
            deployed = [a for a in self._apps if a.get("deployed")]
            pending = [a for a in self._apps if not a.get("deployed")]

            if pending:
                action = "deploy_app"
                params = {"app_name": pending[0]["name"]}
                reasoning = f"App '{pending[0]['name']}' is ready to deploy."
            elif deployed:
                # Rotate between analytics, update, screenshot
                last_actions = [entry["action"] for entry in self.state.ledger[-5:]]
                candidates = ["check_analytics", "update_app", "screenshot_app"]
                # Pick the least-recently used candidate
                scores = {c: last_actions.count(c) for c in candidates}
                action = min(candidates, key=lambda c: scores[c])
                target = deployed[0]
                params = {"app_name": target["name"], "app_type": target.get("app_type", "url_shortener")}
                reasoning = f"Maintaining deployed app '{target['name']}'."
            else:
                action = "generate_app"
                params = {"app_type": "url_shortener", "tech_stack": "flask"}
                reasoning = "No deployable apps. Generating another."

        return AgentDecision(
            decision_id=decision_id,
            timestamp=ts,
            action=action,
            params=params,
            reasoning=reasoning,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute(self, decision: AgentDecision) -> dict:
        """Run the chosen SaaS action."""
        action = decision.action
        params = decision.params

        self.log(f"SaaS execute: {action} | params={params}")

        if action == "generate_app":
            return self._exec_generate_app(params)
        if action == "deploy_app":
            return self._exec_deploy_app(params)
        if action == "update_app":
            return self._exec_update_app(params)
        if action == "check_analytics":
            return self._exec_check_analytics(params)
        if action == "screenshot_app":
            return self._exec_screenshot_app(params)

        return {"success": False, "error": f"Unknown action: {action}"}

    def get_default_interval(self) -> int:
        """20 minutes between cycles."""
        return 1200

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------
    def _exec_generate_app(self, params: dict) -> dict:
        app_type = params.get("app_type", "url_shortener")
        tech_stack = params.get("tech_stack", "flask")
        features = params.get("features", ["auth", "dashboard", "api"])

        # Call business-tool registry
        result = self.generate_asset_via_registry(
            "generate_app_code",
            app_type=app_type,
            features=features,
            tech_stack=tech_stack,
        )

        if not isinstance(result, dict):
            result = {"success": False, "error": f"Unexpected registry response: {result}"}

        if not result.get("success"):
            # Fallback: write a minimal runnable Flask app so the agent stays useful
            self.log("Registry failed; generating fallback Flask app locally.")
            result = self._generate_fallback_app(app_type, tech_stack, features)

        app_name = self._next_app_name(app_type)
        app_folder = APP_DIR / app_name
        app_folder.mkdir(parents=True, exist_ok=True)

        # Persist generated files
        files = result.get("files", {})
        if not files and result.get("code"):
            files = {"app.py": result["code"]}
        for fname, content in files.items():
            (app_folder / fname).write_text(content, encoding="utf-8")

        # Also save metadata
        app_meta = {
            "name": app_name,
            "app_type": app_type,
            "tech_stack": tech_stack,
            "features": features,
            "created_at": time.time(),
            "deployed": False,
            "deploy_url": None,
            "users": 0,
            "folder": str(app_folder),
        }
        self._apps.append(app_meta)
        self._save_app_registry()

        self.log(f"Generated app '{app_name}' in {app_folder}")
        return {
            "success": True,
            "app_name": app_name,
            "folder": str(app_folder),
            "files": list(files.keys()),
            "revenue": 0.0,
            "costs": 0.0,
        }

    def _generate_fallback_app(self, app_type: str, tech_stack: str, features: List[str]) -> dict:
        """Generate a minimal Flask app locally when the registry is unavailable."""
        code = '''from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# In-memory store
store = {}

HTML = """
<!doctype html>
<title>'''+ app_type.replace("_", " ").title() + '''</title>
<h1>Welcome to '''+ app_type.replace("_", " ").title() + '''</h1>
<p>Users: {{ users }}</p>
"""

@app.route("/")
def home():
    return render_template_string(HTML, users=len(store))

@app.route("/api/data", methods=["GET", "POST"])
def api_data():
    if request.method == "POST":
        data = request.get_json(force=True)
        store[data.get("id", "x")] = data
        return jsonify({"saved": True})
    return jsonify(store)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
'''
        return {
            "success": True,
            "files": {"app.py": code, "requirements.txt": "Flask\n"},
        }

    def _exec_deploy_app(self, params: dict) -> dict:
        app_name = params.get("app_name")
        app = next((a for a in self._apps if a["name"] == app_name), None)
        if not app:
            return {"success": False, "error": f"App '{app_name}' not found"}

        # Use Render dashboard (Railway fallback commented for clarity)
        platform = params.get("platform", "render")
        self.browser.open_chrome(url=f"https://dashboard.{platform}.com", new_window=True)
        time.sleep(3)
        self.browser.wait_for_load(timeout=10)

        # Simulate deployment interactions (percentages tuned for typical dashboards)
        # 1) Click "New" or "New +" button (upper-leftish)
        self.browser.win_click(0.08, 0.12)
        time.sleep(1.5)

        # 2) Click "Web Service" (modal middle)
        self.browser.win_click(0.35, 0.45)
        time.sleep(1.5)

        # 3) Type project name into first prominent text field
        self.browser.fill_form_field(0.35, 0.38, app_name)
        time.sleep(0.5)

        # 4) Click "Deploy" / "Create Web Service" (lower-rightish)
        self.browser.win_click(0.75, 0.75)
        time.sleep(2)

        # 5) Screenshot for verification
        state = self.browser.screenshot(filename=f"deploy_{app_name}.png")

        # Mark deployed and accrue one-time revenue
        app["deployed"] = True
        app["deploy_url"] = f"https://{app_name.lower()}.onrender.com"
        app["deployed_at"] = time.time()
        self._save_app_registry()

        revenue = REVENUE_PER_DEPLOYMENT
        self.log(f"Deployed '{app_name}' on {platform}. Revenue +${revenue}")
        return {
            "success": True,
            "platform": platform,
            "app_name": app_name,
            "screenshot": state.screenshot_path,
            "revenue": revenue,
            "costs": 0.0,
        }

    def _exec_update_app(self, params: dict) -> dict:
        app_name = params.get("app_name")
        app = next((a for a in self._apps if a["name"] == app_name), None)
        if not app:
            return {"success": False, "error": f"App '{app_name}' not found"}

        folder = Path(app["folder"])
        app_py = folder / "app.py"
        if not app_py.exists():
            return {"success": False, "error": f"app.py missing for {app_name}"}

        original = app_py.read_text(encoding="utf-8")

        # Inject a simple /health endpoint if missing
        if "@app.route(\"/health\")" not in original:
            patch = '''

@app.route("/health")
def health():
    return {"status": "ok", "version": "1.0.1"}
'''
            app_py.write_text(original + patch, encoding="utf-8")
            change = "added /health endpoint"
        else:
            change = "no changes needed"

        self.log(f"Updated '{app_name}': {change}")
        return {
            "success": True,
            "app_name": app_name,
            "change": change,
            "revenue": 0.0,
            "costs": 0.0,
        }

    def _exec_check_analytics(self, params: dict) -> dict:
        app_name = params.get("app_name")
        app = next((a for a in self._apps if a["name"] == app_name), None)
        if not app:
            return {"success": False, "error": f"App '{app_name}' not found"}

        # Simulate user growth: base + random daily growth
        import random
        new_users = random.randint(1, 8)
        app["users"] = app.get("users", 0) + new_users
        self._save_app_registry()

        revenue = new_users * REVENUE_PER_USER
        self.log(f"Analytics for '{app_name}': +{new_users} users. Revenue +${revenue:.2f}")
        return {
            "success": True,
            "app_name": app_name,
            "new_users": new_users,
            "total_users": app["users"],
            "revenue": revenue,
            "costs": 0.0,
        }

    def _exec_screenshot_app(self, params: dict) -> dict:
        app_name = params.get("app_name")
        app = next((a for a in self._apps if a["name"] == app_name), None)
        if not app:
            return {"success": False, "error": f"App '{app_name}' not found"}

        url = app.get("deploy_url") or f"http://localhost:5000"
        self.browser.open_chrome(url=url, new_window=True)
        time.sleep(2)
        state = self.browser.wait_for_load(timeout=10)
        filename = f"saas_{app_name}_{int(time.time())}.png"
        state = self.browser.screenshot(filename=filename)

        self.log(f"Screenshot captured for '{app_name}': {state.screenshot_path}")
        return {
            "success": True,
            "app_name": app_name,
            "screenshot_path": state.screenshot_path,
            "revenue": 0.0,
            "costs": 0.0,
        }
