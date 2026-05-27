import datetime

import streamlit as st

from .credentials import render_credentials
from .data_store import ensure_data_dirs
from .financial import render_financial
from .links import render_links
from .marketplace import render_marketplace
from .navigation import render_navigation
from .settings import render_settings
from .stats import render_stats
from .swarm_control import render_swarm_control


def render_monetization_tab() -> None:
    """Render the full Monetization Swarm Dashboard tab."""
    ensure_data_dirs()

    selected = render_navigation()

    st.title("Monetization Swarm Dashboard")
    st.markdown(
        "<h4 style='color: #4CAF50;'>Swarm-powered revenue & marketplace management</h4>",
        unsafe_allow_html=True,
    )

    st.divider()

    if selected == "🏠 Overview":
        with st.container():
            st.subheader("Welcome")
            st.info("Use the sidebar to navigate between sections.")
    elif selected == "💰 Financial Analysis":
        with st.container():
            render_financial()
    elif selected == "⚙️ API Settings":
        with st.container():
            render_settings()
    elif selected == "🔐 Credentials":
        with st.container():
            render_credentials()
    elif selected == "🛒 Marketplace":
        with st.container():
            render_marketplace()
    elif selected == "📊 Stats":
        with st.container():
            render_stats()
    elif selected == "🔗 Links":
        with st.container():
            render_links()
    elif selected == "🤖 Swarm Control":
        with st.container():
            render_swarm_control()

    st.divider()

    with st.container():
        cols = st.columns([3, 1])
        with cols[0]:
            st.caption("SimplePod Monetization Module — v1.0.0")
        with cols[1]:
            st.caption(
                f"Last updated: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
            )
