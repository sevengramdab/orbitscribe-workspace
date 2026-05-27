import json
import os
import streamlit as st
import pandas as pd


def render_stats():
    st.title("📊 Monetization Analytics Dashboard")
    st.markdown("---")

    # ------------------------------------------------------------------
    # Load vault data (or fallback to demo data)
    # ------------------------------------------------------------------
    vault_path = os.path.join("..", "..", "tools", "saved_sessions", "unified_business_vault.json")
    if os.path.exists(vault_path):
        try:
            with open(vault_path, "r", encoding="utf-8") as f:
                vault = json.load(f)
        except Exception:
            vault = {}
    else:
        vault = {}

    # Extract agent data
    agents = vault.get("agents", [])
    if not agents:
        agents = _demo_agents()

    # Extract deliverables
    deliverables = vault.get("deliverables", {})
    if not deliverables:
        deliverables = _demo_deliverables()

    # Extract decisions / activity
    decisions = vault.get("decisions", [])
    if not decisions:
        decisions = _demo_decisions()

    # Extract vault collections
    collections = vault.get("collections", {})
    if not collections:
        collections = _demo_collections()

    # ------------------------------------------------------------------
    # 1. Agent Performance Cards
    # ------------------------------------------------------------------
    st.header("🤖 Agent Performance")
    cols = st.columns(5)
    for idx, agent in enumerate(agents[:10]):
        col = cols[idx % 5]
        with col:
            _agent_card(agent)
    st.markdown("---")

    # ------------------------------------------------------------------
    # 2. Deliverable Stats
    # ------------------------------------------------------------------
    st.header("📦 Deliverable Stats")
    dcols = st.columns(5)
    metric_items = [
        ("Products / Apps", deliverables.get("products_apps", 0)),
        ("Assets", deliverables.get("assets", 0)),
        ("Content Pieces", deliverables.get("content", 0)),
        ("Leads", deliverables.get("leads", 0)),
        ("Campaigns", deliverables.get("campaigns", 0)),
    ]
    for col, (label, value) in zip(dcols, metric_items):
        col.metric(label=label, value=value)
    st.markdown("---")

    # ------------------------------------------------------------------
    # 3. Recent Activity Timeline
    # ------------------------------------------------------------------
    st.header("🕒 Recent Activity Timeline")
    recent = sorted(decisions, key=lambda x: x.get("timestamp", ""), reverse=True)[:20]
    if recent:
        df = pd.DataFrame(recent)
        # Ensure expected columns exist
        for c in ["timestamp", "agent", "decision_type", "revenue_impact", "status"]:
            if c not in df.columns:
                df[c] = ""
        df = df[["timestamp", "agent", "decision_type", "revenue_impact", "status"]]
        df.columns = ["Time", "Agent", "Decision Type", "Revenue Impact", "Status"]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No recent activity found.")
    st.markdown("---")

    # ------------------------------------------------------------------
    # 4. Vault Collections Summary
    # ------------------------------------------------------------------
    st.header("🏛️ Vault Collections Summary")
    if collections:
        coll_df = pd.DataFrame(
            {"Collection": list(collections.keys()), "Documents": list(collections.values())}
        )
        st.bar_chart(coll_df.set_index("Collection"))
    else:
        st.info("No vault collections available.")
    st.markdown("---")

    # ------------------------------------------------------------------
    # 5. Top Performing Agent
    # ------------------------------------------------------------------
    st.header("🏆 Top Performing Agent")
    top_agent = max(agents, key=lambda a: a.get("revenue", 0), default=None)
    if top_agent:
        rev = top_agent.get("revenue", 0)
        costs = top_agent.get("costs", 0)
        profit = rev - costs
        st.success(
            f"**{top_agent.get('name', 'Unknown')}**  \n"
            f"Revenue: `${rev:,.2f}` | Costs: `${costs:,.2f}` | Net Profit: `${profit:,.2f}`"
        )
    else:
        st.info("No agent data available.")


def _agent_card(agent: dict):
    name = agent.get("name", "Unknown")
    revenue = agent.get("revenue", 0.0)
    costs = agent.get("costs", 0.0)
    profit = revenue - costs
    decisions_made = agent.get("decisions_made", 0)
    decisions_executed = agent.get("decisions_executed", 0)
    status = agent.get("status", "idle")

    status_emoji = "🟢" if status.lower() == "running" else "⚪"
    st.markdown(f"**{status_emoji} {name}**")
    st.markdown(f"<span style='color:green'>Revenue: `${revenue:,.2f}`</span>", unsafe_allow_html=True)
    st.markdown(f"<span style='color:red'>Costs: `${costs:,.2f}`</span>", unsafe_allow_html=True)
    st.markdown(f"**Net Profit: `${profit:,.2f}`**")
    st.caption(f"Decisions: {decisions_executed}/{decisions_made}")


def _demo_agents():
    return [
        {"name": "SalesBot-Alpha", "revenue": 12500.0, "costs": 2100.0, "decisions_made": 45, "decisions_executed": 42, "status": "running"},
        {"name": "AdOptimizer", "revenue": 8700.0, "costs": 1500.0, "decisions_made": 32, "decisions_executed": 30, "status": "running"},
        {"name": "ContentForge", "revenue": 5400.0, "costs": 800.0, "decisions_made": 28, "decisions_executed": 25, "status": "idle"},
        {"name": "LeadScout", "revenue": 3200.0, "costs": 400.0, "decisions_made": 19, "decisions_executed": 18, "status": "running"},
        {"name": "PriceWizard", "revenue": 6800.0, "costs": 950.0, "decisions_made": 24, "decisions_executed": 22, "status": "idle"},
        {"name": "EmailMaven", "revenue": 4500.0, "costs": 600.0, "decisions_made": 21, "decisions_executed": 20, "status": "running"},
        {"name": "AffiliateAce", "revenue": 9100.0, "costs": 1200.0, "decisions_made": 35, "decisions_executed": 33, "status": "running"},
        {"name": "PODCraft", "revenue": 2800.0, "costs": 350.0, "decisions_made": 15, "decisions_executed": 14, "status": "idle"},
        {"name": "SaaSScout", "revenue": 11200.0, "costs": 1800.0, "decisions_made": 40, "decisions_executed": 38, "status": "running"},
        {"name": "DropShipPro", "revenue": 7600.0, "costs": 1100.0, "decisions_made": 27, "decisions_executed": 26, "status": "idle"},
    ]


def _demo_deliverables():
    return {
        "products_apps": 12,
        "assets": 47,
        "content": 85,
        "leads": 320,
        "campaigns": 18,
    }


def _demo_decisions():
    import random
    agents = ["SalesBot-Alpha", "AdOptimizer", "ContentForge", "LeadScout", "PriceWizard",
              "EmailMaven", "AffiliateAce", "PODCraft", "SaaSScout", "DropShipPro"]
    types = ["pricing", "launch", "optimize", "promote", "pause", "scale"]
    statuses = ["executed", "pending", "rejected"]
    base = pd.Timestamp("2026-05-27 07:00:00")
    out = []
    for i in range(25):
        ts = (base + pd.Timedelta(minutes=i * 7)).strftime("%Y-%m-%d %H:%M:%S")
        rev = round(random.uniform(-200, 800), 2)
        out.append({
            "timestamp": ts,
            "agent": random.choice(agents),
            "decision_type": random.choice(types),
            "revenue_impact": rev,
            "status": random.choice(statuses),
        })
    return out


def _demo_collections():
    return {
        "products": 12,
        "assets": 47,
        "content": 85,
        "leads": 320,
        "campaigns": 18,
        "analytics": 56,
        "logs": 210,
    }
