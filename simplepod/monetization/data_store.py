"""Data persistence layer for the monetization dashboard."""

import json
import os
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Paths (relative to this file)
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_SETTINGS_PATH = os.path.join(_BASE_DIR, "..", "..", "swarm-backend", "business_config.json")
_CREDENTIALS_PATH = os.path.join(_BASE_DIR, "..", "..", "tools", "saved_sessions", "monetization_credentials.json")
_LINKS_PATH = os.path.join(_BASE_DIR, "..", "..", "tools", "saved_sessions", "monetization_links.json")
_CONTROL_STATE_PATH = os.path.join(_BASE_DIR, "..", "..", "tools", "saved_sessions", "monetization_control_state.json")
_VAULT_PATH = os.path.join(_BASE_DIR, "..", "..", "tools", "saved_sessions", "unified_business_vault.json")

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _safe_read_json(path: str, default):
    """Read JSON from *path*; return *default* if missing or corrupt."""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    except (json.JSONDecodeError, OSError, TypeError):
        pass
    return default


def _safe_write_json(path: str, data):
    """Write *data* as JSON to *path*, creating parent dirs if needed."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Directory bootstrap
# ---------------------------------------------------------------------------

def ensure_data_dirs():
    """Create all directories required by the persistence layer."""
    for p in (_SETTINGS_PATH, _CREDENTIALS_PATH, _LINKS_PATH, _CONTROL_STATE_PATH, _VAULT_PATH):
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    """Load dashboard settings from ``swarm-backend/business_config.json``."""
    return _safe_read_json(_SETTINGS_PATH, {})


def save_settings(data: dict):
    """Persist dashboard settings to ``swarm-backend/business_config.json``."""
    _safe_write_json(_SETTINGS_PATH, data)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def load_credentials() -> list:
    """Load credentials from ``tools/saved_sessions/monetization_credentials.json``."""
    return _safe_read_json(_CREDENTIALS_PATH, [])


def save_credentials(data: list):
    """Persist credentials to ``tools/saved_sessions/monetization_credentials.json``."""
    _safe_write_json(_CREDENTIALS_PATH, data)


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

def load_links() -> list:
    """Load links from ``tools/saved_sessions/monetization_links.json``."""
    return _safe_read_json(_LINKS_PATH, [])


def save_links(data: list):
    """Persist links to ``tools/saved_sessions/monetization_links.json``."""
    _safe_write_json(_LINKS_PATH, data)


# ---------------------------------------------------------------------------
# Control state
# ---------------------------------------------------------------------------

def load_control_state() -> dict:
    """Load control state from ``tools/saved_sessions/monetization_control_state.json``."""
    return _safe_read_json(_CONTROL_STATE_PATH, {})


def save_control_state(data: dict):
    """Persist control state to ``tools/saved_sessions/monetization_control_state.json``."""
    _safe_write_json(_CONTROL_STATE_PATH, data)


# ---------------------------------------------------------------------------
# Vault summary
# ---------------------------------------------------------------------------

def load_vault_summary() -> dict:
    """Load vault summary from ``tools/saved_sessions/unified_business_vault.json``."""
    data = _safe_read_json(_VAULT_PATH, {})
    if isinstance(data, dict) and "summary" in data:
        return data["summary"]
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

def get_demo_data() -> dict:
    """Return realistic demo data for the monetization dashboard."""
    now = datetime.utcnow()

    agents = [
        {"name": "Sales Scout", "revenue": 12400.50, "costs": 2100.00, "status": "active"},
        {"name": "Lead Hunter", "revenue": 8750.25, "costs": 1500.50, "status": "active"},
        {"name": "Content Crafter", "revenue": 5300.00, "costs": 900.00, "status": "paused"},
        {"name": "Support Sage", "revenue": 3200.75, "costs": 600.25, "status": "active"},
        {"name": "Billing Bot", "revenue": 9800.00, "costs": 1200.00, "status": "active"},
        {"name": "SEO Sentinel", "revenue": 4100.00, "costs": 800.00, "status": "active"},
        {"name": "Email Enchanter", "revenue": 6700.50, "costs": 1100.00, "status": "paused"},
        {"name": "Ad Architect", "revenue": 11200.00, "costs": 3400.00, "status": "active"},
        {"name": "Social Sorcerer", "revenue": 4500.25, "costs": 950.75, "status": "active"},
        {"name": "Analytics Ace", "revenue": 7800.00, "costs": 1300.00, "status": "active"},
    ]

    decisions = []
    for i in range(20):
        ts = now - timedelta(hours=i * 3 + 1)
        decisions.append(
            {
                "id": i + 1,
                "timestamp": ts.isoformat() + "Z",
                "action": [
                    "increase_ad_spend",
                    "pause_underperformer",
                    "launch_campaign",
                    "adjust_pricing",
                    "approve_budget",
                    "reject_proposal",
                    "scale_winner",
                    "test_creative",
                    "optimize_funnel",
                    "review_mrr",
                ][i % 10],
                "agent": agents[i % len(agents)]["name"],
                "outcome": ["success", "pending", "failure"][i % 3],
                "impact_usd": round((i + 1) * 150.50, 2),
            }
        )

    vault_collections = [
        {"name": "Leads", "count": 1247, "value_usd": 42100.00},
        {"name": "Campaigns", "count": 38, "value_usd": 18750.00},
        {"name": "Assets", "count": 156, "value_usd": 0.00},
        {"name": "Subscriptions", "count": 512, "value_usd": 76800.00},
        {"name": "Invoices", "count": 893, "value_usd": 124300.00},
    ]

    total_revenue = sum(a["revenue"] for a in agents)
    total_costs = sum(a["costs"] for a in agents)
    pl_summary = {
        "revenue": round(total_revenue, 2),
        "costs": round(total_costs, 2),
        "profit": round(total_revenue - total_costs, 2),
        "margin_pct": round(((total_revenue - total_costs) / total_revenue) * 100, 2) if total_revenue else 0.0,
        "active_agents": sum(1 for a in agents if a["status"] == "active"),
        "paused_agents": sum(1 for a in agents if a["status"] == "paused"),
        "total_agents": len(agents),
    }

    return {
        "agents": agents,
        "decisions": decisions,
        "vault_collections": vault_collections,
        "pl_summary": pl_summary,
    }
