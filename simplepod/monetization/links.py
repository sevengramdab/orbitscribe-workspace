import json
import os
import streamlit as st

_DEFAULT_LINKS = {
    "Payments": [
        {"name": "Stripe Dashboard", "url": "https://dashboard.stripe.com", "emoji": "💳", "desc": "Manage payments, payouts, and billing."},
        {"name": "Stripe API Docs", "url": "https://stripe.com/docs", "emoji": "📘", "desc": "Official Stripe API reference and guides."},
    ],
    "E-commerce": [
        {"name": "Etsy Seller Dashboard", "url": "https://www.etsy.com/sell", "emoji": "🧵", "desc": "Manage Etsy shop listings and orders."},
        {"name": "Shopify Admin", "url": "https://admin.shopify.com", "emoji": "🛍️", "desc": "Your Shopify store admin panel."},
        {"name": "Printify Dashboard", "url": "https://printify.com/app/dashboard", "emoji": "👕", "desc": "Create and manage print-on-demand products."},
        {"name": "Amazon Seller Central", "url": "https://sellercentral.amazon.com", "emoji": "📦", "desc": "Amazon seller account and inventory hub."},
        {"name": "Gumroad", "url": "https://gumroad.com/dashboard", "emoji": "🍬", "desc": "Sell digital products and memberships."},
        {"name": "Payhip", "url": "https://payhip.com/dashboard", "emoji": "💰", "desc": "Sell digital downloads and courses."},
    ],
    "Content & Marketing": [
        {"name": "Medium", "url": "https://medium.com", "emoji": "✍️", "desc": "Publish and monetize blog stories."},
        {"name": "Substack", "url": "https://substack.com", "emoji": "📰", "desc": "Newsletter publishing and paid subscriptions."},
        {"name": "Mailchimp", "url": "https://admin.mailchimp.com", "emoji": "🐒", "desc": "Email marketing campaigns and automation."},
        {"name": "ConvertKit", "url": "https://app.convertkit.com", "emoji": "📧", "desc": "Email marketing for creators."},
    ],
    "Affiliate Programs": [
        {"name": "Amazon Associates", "url": "https://affiliate-program.amazon.com", "emoji": "🔗", "desc": "Amazon affiliate program dashboard."},
        {"name": "Impact", "url": "https://app.impact.com", "emoji": "🌐", "desc": "Partnership and affiliate management platform."},
        {"name": "CJ Affiliate", "url": "https://www.cj.com", "emoji": "🤝", "desc": "Commission Junction affiliate network."},
    ],
    "Deployment": [
        {"name": "Render", "url": "https://dashboard.render.com", "emoji": "🚀", "desc": "Deploy apps, static sites, and databases."},
        {"name": "Railway", "url": "https://railway.app/dashboard", "emoji": "🚂", "desc": "Infrastructure platform for deploying apps."},
        {"name": "Vercel", "url": "https://vercel.com/dashboard", "emoji": "▲", "desc": "Frontend deployment and serverless functions."},
        {"name": "Docker Hub", "url": "https://hub.docker.com", "emoji": "🐳", "desc": "Container image repository and registry."},
    ],
    "Analytics": [
        {"name": "Google Analytics", "url": "https://analytics.google.com", "emoji": "📊", "desc": "Website traffic and user behavior analytics."},
        {"name": "Plausible", "url": "https://plausible.io", "emoji": "🌿", "desc": "Privacy-friendly, lightweight web analytics."},
    ],
}

_CUSTOM_LINKS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "saved_sessions", "monetization_links.json")


def _load_custom_links() -> dict:
    if not os.path.exists(_CUSTOM_LINKS_PATH):
        return {}
    try:
        with open(_CUSTOM_LINKS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_custom_links(data: dict) -> None:
    os.makedirs(os.path.dirname(_CUSTOM_LINKS_PATH), exist_ok=True)
    with open(_CUSTOM_LINKS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _merge_links(default: dict, custom: dict) -> dict:
    merged = {cat: list(links) for cat, links in default.items()}
    for cat, links in custom.items():
        if cat not in merged:
            merged[cat] = []
        for link in links:
            if link not in merged[cat]:
                merged[cat].append(link)
    return merged


def _filter_links(links_data: dict, query: str) -> dict:
    query = query.lower().strip()
    if not query:
        return links_data
    filtered = {}
    for cat, links in links_data.items():
        matched = []
        for link in links:
            text = f"{link.get('name', '')} {link.get('desc', '')} {cat}".lower()
            if query in text:
                matched.append(link)
        if matched:
            filtered[cat] = matched
    return filtered


def render_links() -> None:
    st.title("🌐 Monetization Quick Links")
    st.caption("All your platforms and tools in one place.")

    query = st.text_input("🔍 Search links", placeholder="Type to filter by name, description, or category...")

    custom = _load_custom_links()
    all_links = _merge_links(_DEFAULT_LINKS, custom)
    filtered = _filter_links(all_links, query)

    if not filtered:
        st.info("No links match your search.")

    for category, links in filtered.items():
        with st.expander(f"**{category}** — {len(links)} link(s)", expanded=True if not query else bool(query)):
            cols = st.columns(2)
            for idx, link in enumerate(links):
                col = cols[idx % 2]
                with col:
                    emoji = link.get("emoji", "🔗")
                    name = link.get("name", "Untitled")
                    url = link.get("url", "#")
                    desc = link.get("desc", "")
                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid #333;
                            border-radius: 8px;
                            padding: 12px;
                            margin-bottom: 10px;
                            background-color: #1e1e1e;
                        ">
                            <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 4px;">
                                {emoji} {name}
                            </div>
                            <div style="font-size: 0.85rem; color: #aaaaaa; margin-bottom: 8px;">
                                {desc}
                            </div>
                            <a href="{url}" target="_blank" style="
                                display: inline-block;
                                padding: 6px 14px;
                                background-color: #0e639c;
                                color: #ffffff;
                                text-decoration: none;
                                border-radius: 4px;
                                font-size: 0.85rem;
                            ">Open →</a>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    st.divider()
    st.subheader("➕ Add Custom Link")
    with st.form("add_custom_link"):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Name")
        with c2:
            new_category = st.selectbox(
                "Category",
                options=list(_DEFAULT_LINKS.keys()) + ["Custom"],
                index=len(_DEFAULT_LINKS),
            )
        new_url = st.text_input("URL", placeholder="https://...")
        new_emoji = st.text_input("Emoji", value="🔗", max_chars=4)
        new_desc = st.text_area("Description", placeholder="Short description...")
        submitted = st.form_submit_button("Add Link")
        if submitted:
            if not new_name or not new_url:
                st.warning("Name and URL are required.")
            else:
                category = new_category if new_category else "Custom"
                custom.setdefault(category, [])
                custom[category].append({
                    "name": new_name,
                    "url": new_url,
                    "emoji": new_emoji,
                    "desc": new_desc,
                })
                _save_custom_links(custom)
                st.success(f"Added '{new_name}' to {category}!")
                st.rerun()
