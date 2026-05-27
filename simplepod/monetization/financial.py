"""Streamlit financial analysis dashboard for the monetization swarm."""

import json
import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st


def _load_vault_data():
    """Load business vault data or return realistic demo data."""
    vault_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "tools", "saved_sessions", "unified_business_vault.json"
    )
    vault_path = os.path.normpath(vault_path)

    if os.path.exists(vault_path):
        try:
            with open(vault_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Realistic demo fallback data
    agents = [
        {"name": "Dropship Agent", "revenue": 12450.0, "costs": 4150.0, "decisions_made": 48, "decisions_executed": 41, "category": "dropshipping"},
        {"name": "Content Agent", "revenue": 8320.0, "costs": 1200.0, "decisions_made": 62, "decisions_executed": 55, "category": "content"},
        {"name": "SaaS Agent", "revenue": 18700.0, "costs": 5600.0, "decisions_made": 35, "decisions_executed": 30, "category": "SaaS"},
        {"name": "Affiliate Agent", "revenue": 4100.0, "costs": 350.0, "decisions_made": 28, "decisions_executed": 25, "category": "affiliate"},
        {"name": "LeadGen Agent", "revenue": 6750.0, "costs": 1800.0, "decisions_made": 40, "decisions_executed": 36, "category": "leads"},
        {"name": "POD Agent", "revenue": 5200.0, "costs": 2100.0, "decisions_made": 22, "decisions_executed": 19, "category": "POD"},
    ]

    transactions = []
    base = datetime.now() - timedelta(days=30)
    for i in range(15):
        agent = agents[i % len(agents)]
        rev = round(50 + (i * 37.5), 2)
        cost = round(rev * 0.3, 2)
        transactions.append({
            "timestamp": (base + timedelta(days=i * 2)).isoformat(),
            "agent": agent["name"],
            "description": f"Decision #{i + 1}: optimized {agent['category']} campaign",
            "revenue_impact": rev,
            "cost_impact": cost,
        })

    # Sort descending by time
    transactions.sort(key=lambda x: x["timestamp"], reverse=True)

    dates = pd.date_range(end=datetime.now(), periods=12, freq="MS").strftime("%Y-%m").tolist()
    revenue_series = [8200, 9100, 10500, 11200, 12800, 13500, 14200, 15600, 16300, 17500, 18200, 19500]

    return {
        "agents": agents,
        "transactions": transactions,
        "revenue_over_time": {"dates": dates, "revenue": revenue_series},
    }


def render_financial():
    """Render the full financial analysis dashboard."""
    st.title("📊 Financial Dashboard")
    st.caption("Real-time monetization swarm P&L, trends, and agent performance.")

    data = _load_vault_data()
    agents = data.get("agents", [])
    transactions = data.get("transactions", [])
    revenue_over_time = data.get("revenue_over_time", {})

    # ------------------------------------------------------------------
    # 1. Top metric cards
    # ------------------------------------------------------------------
    total_revenue = sum(a.get("revenue", 0) for a in agents)
    total_costs = sum(a.get("costs", 0) for a in agents)
    net_profit = total_revenue - total_costs

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Total Revenue",
            value=f"${total_revenue:,.2f}",
            delta=None,
        )
    with col2:
        st.metric(
            label="Total Costs",
            value=f"${total_costs:,.2f}",
            delta=None,
        )
    with col3:
        delta_color = "normal" if net_profit >= 0 else "inverse"
        st.metric(
            label="Net Profit",
            value=f"${net_profit:,.2f}",
            delta=None,
            delta_color=delta_color,
        )

    st.markdown("---")

    # ------------------------------------------------------------------
    # 2. Revenue over time (line chart)
    # ------------------------------------------------------------------
    st.subheader("📈 Revenue Over Time")
    if revenue_over_time and "dates" in revenue_over_time and "revenue" in revenue_over_time:
        rev_df = pd.DataFrame({
            "Date": revenue_over_time["dates"],
            "Revenue": revenue_over_time["revenue"],
        }).set_index("Date")
    else:
        # Mock line chart fallback
        mock_dates = pd.date_range(end=datetime.now(), periods=12, freq="MS").strftime("%Y-%m").tolist()
        mock_revenue = [8000 + i * 950 for i in range(12)]
        rev_df = pd.DataFrame({"Date": mock_dates, "Revenue": mock_revenue}).set_index("Date")

    st.line_chart(rev_df, use_container_width=True, color="#2ecc71")

    # ------------------------------------------------------------------
    # 3. Per-agent revenue breakdown (bar chart)
    # ------------------------------------------------------------------
    st.subheader("🤖 Per-Agent Revenue Breakdown")
    if agents:
        agent_rev_df = pd.DataFrame({
            "Agent": [a["name"] for a in agents],
            "Revenue": [a.get("revenue", 0) for a in agents],
        }).set_index("Agent")
        st.bar_chart(agent_rev_df, use_container_width=True, color="#3498db")
    else:
        st.info("No agent data available for bar chart.")

    # ------------------------------------------------------------------
    # 4. Revenue by category (pie / breakdown)
    # ------------------------------------------------------------------
    st.subheader("🍰 Revenue by Category")
    if agents:
        cat_totals = {}
        for a in agents:
            cat = a.get("category", "Uncategorized")
            cat_totals[cat] = cat_totals.get(cat, 0) + a.get("revenue", 0)

        cat_df = pd.DataFrame({
            "Category": list(cat_totals.keys()),
            "Revenue": list(cat_totals.values()),
        })

        # Try Altair for a proper pie chart (bundled with Streamlit)
        try:
            import altair as alt
            pie = (
                alt.Chart(cat_df)
                .mark_arc(innerRadius=50)
                .encode(
                    theta=alt.Theta(field="Revenue", type="quantitative"),
                    color=alt.Color(field="Category", type="nominal"),
                    tooltip=["Category", "Revenue"],
                )
                .properties(height=350)
            )
            st.altair_chart(pie, use_container_width=True)
        except Exception:
            # Fallback to horizontal bar if Altair fails
            st.bar_chart(cat_df.set_index("Category"), use_container_width=True, color="#9b59b6")
    else:
        st.info("No category data available.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # 5. P&L Detail (expandable table)
    # ------------------------------------------------------------------
    with st.expander("📋 P&L Detail"):
        if agents:
            pl_df = pd.DataFrame([
                {
                    "Agent": a["name"],
                    "Category": a.get("category", "N/A"),
                    "Revenue": a.get("revenue", 0),
                    "Costs": a.get("costs", 0),
                    "Net": round(a.get("revenue", 0) - a.get("costs", 0), 2),
                    "Decisions Made": a.get("decisions_made", 0),
                    "Decisions Executed": a.get("decisions_executed", 0),
                }
                for a in agents
            ])

            # Style: green for positive net, red for negative
            def _color_net(val):
                color = "#27ae60" if val >= 0 else "#e74c3c"
                return f"color: {color}; font-weight: 600;"

            styled = (
                pl_df.style
                .format({
                    "Revenue": "${:,.2f}",
                    "Costs": "${:,.2f}",
                    "Net": "${:,.2f}",
                })
                .map(_color_net, subset=["Net"])
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)
        else:
            st.info("No agent P&L data available.")

    # ------------------------------------------------------------------
    # 6. Recent Transactions (expandable list)
    # ------------------------------------------------------------------
    with st.expander("💳 Recent Transactions"):
        recent = transactions[:10]
        if recent:
            tx_df = pd.DataFrame([
                {
                    "Time": t.get("timestamp", "N/A"),
                    "Agent": t.get("agent", "N/A"),
                    "Description": t.get("description", ""),
                    "Revenue Impact": t.get("revenue_impact", 0),
                    "Cost Impact": t.get("cost_impact", 0),
                    "Net Impact": round(
                        t.get("revenue_impact", 0) - t.get("cost_impact", 0), 2
                    ),
                }
                for t in recent
            ])

            def _color_tx(val):
                color = "#27ae60" if val >= 0 else "#e74c3c"
                return f"color: {color}; font-weight: 600;"

            styled_tx = (
                tx_df.style
                .format({
                    "Revenue Impact": "${:,.2f}",
                    "Cost Impact": "${:,.2f}",
                    "Net Impact": "${:,.2f}",
                })
                .map(_color_tx, subset=["Net Impact"])
            )
            st.dataframe(styled_tx, use_container_width=True, hide_index=True)
        else:
            st.info("No recent transactions available.")
