"""Streamlit settings page for monetization swarm API keys."""

import json
import os
from pathlib import Path

import streamlit as st

# Path to the shared business config (two levels up from simplepod/monetization/)
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "swarm-backend" / "business_config.json"

# Ordered field definitions: (label, json_path, is_secret)
FIELDS = [
    ("STRIPE_API_KEY", ["stripe", "publishable_key"], True),
    ("STRIPE_SECRET_KEY", ["stripe", "secret_key"], True),
    ("PRINTIFY_API_KEY", ["printify", "api_key"], True),
    ("PRINTIFY_SHOP_ID", ["printify", "shop_id"], False),
    ("ETSY_API_KEY", ["etsy", "api_key"], True),
    ("ETSY_SHOP_ID", ["etsy", "shop_id"], False),
    ("SHOPIFY_SHOP_DOMAIN", ["shopify", "shop_domain"], False),
    ("SHOPIFY_ACCESS_TOKEN", ["shopify", "access_token"], True),
    ("SMTP_HOST", ["email", "smtp_host"], False),
    ("SMTP_PORT", ["email", "smtp_port"], False),
    ("SMTP_USER", ["email", "username"], False),
    ("SMTP_PASS", ["email", "password"], True),
    ("AMAZON_ASSOCIATES_TAG", ["affiliate", "amazon_associates_tag"], False),
    ("BINANCE_REF", ["affiliate", "binance_ref"], False),
    ("GEMINI_API_KEY", ["gemini", "api_key"], True),
    ("ANTHROPIC_API_KEY (CLAUDE)", ["claude", "api_key"], True),
]

# Helpful links for obtaining keys
LINKS = {
    "STRIPE_API_KEY": "https://dashboard.stripe.com/apikeys",
    "STRIPE_SECRET_KEY": "https://dashboard.stripe.com/apikeys",
    "PRINTIFY_API_KEY": "https://printify.com/account/api-access",
    "PRINTIFY_SHOP_ID": "https://printify.com/app/account/shops",
    "ETSY_API_KEY": "https://www.etsy.com/developers/register",
    "ETSY_SHOP_ID": "https://www.etsy.com/your/shops/me/tools",
    "SHOPIFY_SHOP_DOMAIN": "https://admin.shopify.com",
    "SHOPIFY_ACCESS_TOKEN": "https://admin.shopify.com/settings/apps-and-sales-channels/development",
    "SMTP_HOST": "https://support.google.com/a/answer/176600",
    "SMTP_PORT": "https://support.google.com/a/answer/176600",
    "SMTP_USER": "https://support.google.com/a/answer/176600",
    "SMTP_PASS": "https://support.google.com/a/answer/176600",
    "AMAZON_ASSOCIATES_TAG": "https://affiliate-program.amazon.com",
    "BINANCE_REF": "https://www.binance.com/en/activity/referral",
    "GEMINI_API_KEY": "https://aistudio.google.com/app/apikey",
    "ANTHROPIC_API_KEY (CLAUDE)": "https://console.anthropic.com/settings/keys",
}


def _load_config() -> dict:
    """Load existing config or return a sensible default."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error("⚠️ business_config.json is malformed — starting with defaults.")
    return {
        "_comment": "Add your real API keys here to enable live transactions and integrations.",
        "stripe": {},
        "printify": {},
        "etsy": {},
        "shopify": {},
        "openai": {},
        "claude": {},
        "gemini": {},
        "email": {},
        "affiliate": {},
        "swarm_settings": {},
    }


def _save_config(config: dict) -> None:
    """Persist config back to disk, preserving formatting."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _get_nested(data: dict, path: list[str], default: str = "") -> str:
    """Safely retrieve a nested string value."""
    for key in path:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
    if isinstance(data, (int, float)):
        return str(data)
    return data if isinstance(data, str) else default


def _set_nested(data: dict, path: list[str], value: str) -> None:
    """Safely set a nested string value, creating intermediates as needed."""
    for key in path[:-1]:
        if key not in data or not isinstance(data[key], dict):
            data[key] = {}
        data = data[key]
    data[path[-1]] = value


def _is_configured(value: str) -> bool:
    """Return True if the value looks like a real credential."""
    return bool(value) and value.strip() not in {"", "...", "sk_live_...", "pk_live_...", "whsec_..."}


def render_settings() -> None:
    """Render the monetization settings page in Streamlit."""
    st.title("🔐 Monetization Swarm Settings")
    st.caption("Configure API keys and credentials for the monetization swarm backends.")

    config = _load_config()
    values = {}
    configured_count = 0

    st.subheader("API Keys & Credentials")

    for label, path, is_secret in FIELDS:
        current = _get_nested(config, path)
        values[label] = current

        col1, col2 = st.columns([4, 1])
        with col1:
            if is_secret:
                new_val = st.text_input(
                    label,
                    value=current,
                    type="password",
                    key=f"setting_{label}",
                )
            else:
                new_val = st.text_input(
                    label,
                    value=current,
                    key=f"setting_{label}",
                )
            values[label] = new_val

        with col2:
            st.write("")
            st.write("")
            if _is_configured(new_val):
                st.markdown("<span style='color:green'>✅ Configured</span>", unsafe_allow_html=True)
                configured_count += 1
            else:
                st.markdown("<span style='color:red'>❌ Missing</span>", unsafe_allow_html=True)

    st.markdown("---")

    col_save, col_status = st.columns([1, 3])
    with col_save:
        if st.button("💾 Save Settings", use_container_width=True):
            for label, path, _ in FIELDS:
                _set_nested(config, path, values[label])
            _save_config(config)
            st.success("Settings saved successfully!", icon="✅")

    with col_status:
        total = len(FIELDS)
        st.write(f"**{configured_count}/{total}** keys configured")

    st.markdown("---")
    st.subheader("🔗 Where to get these keys")

    for label, url in LINKS.items():
        st.markdown(f"- **{label}** → [{url}]({url})")
