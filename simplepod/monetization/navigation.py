import streamlit as st


def render_navigation() -> str:
    """Render the monetization sidebar navigation and return the selected page."""
    st.sidebar.markdown(
        """
        <h3 style='display: flex; align-items: center; gap: 8px;'>
            Monetization Swarm
            <span style='display: inline-block; width: 10px; height: 10px; background-color: #4CAF50; border-radius: 50%;'></span>
        </h3>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.divider()

    options = [
        "🏠 Overview",
        "💰 Financial Analysis",
        "⚙️ API Settings",
        "🔐 Credentials",
        "🛒 Marketplace",
        "📊 Stats",
        "🔗 Links",
        "🤖 Swarm Control",
    ]

    selected = st.sidebar.radio("Menu", options, key="monetization_nav")

    return selected
