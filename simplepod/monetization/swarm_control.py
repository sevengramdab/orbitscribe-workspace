"""Streamlit control panel for managing the monetization swarm agents."""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

# ── Constants ──
AGENTS: List[str] = [
    "dropshipping",
    "stripe",
    "affiliate",
    "content",
    "saas",
    "marketplace",
    "ads",
    "licensing",
    "subscriptions",
    "consulting",
]

CONTROL_STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools",
    "saved_sessions",
    "monetization_control_state.json",
)

LOGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools",
    "saved_sessions",
)

DEFAULT_STATE: Dict[str, Any] = {
    "running": False,
    "autonomy_tier": "DEFAULT",
    "total_revenue": 0.0,
    "total_costs": 0.0,
    "net_profit": 0.0,
    "cycle_interval": 300,
    "agents": {
        name: {"status": "idle", "revenue": 0.0, "decisions": 0}
        for name in AGENTS
    },
    "logs": [],
}


# ── Helpers ──
def _load_state() -> Dict[str, Any]:
    """Load control state from JSON file."""
    if os.path.exists(CONTROL_STATE_PATH):
        try:
            with open(CONTROL_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged = DEFAULT_STATE.copy()
            merged.update(data)
            # Ensure agents dict has all keys
            for name in AGENTS:
                if name not in merged.get("agents", {}):
                    merged["agents"][name] = {"status": "idle", "revenue": 0.0, "decisions": 0}
            return merged
        except Exception:
            pass
    return DEFAULT_STATE.copy()


def _save_state(state: Dict[str, Any]) -> None:
    """Persist control state to JSON file."""
    os.makedirs(os.path.dirname(CONTROL_STATE_PATH), exist_ok=True)
    with open(CONTROL_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _add_log(state: Dict[str, Any], message: str) -> None:
    """Append a timestamped log entry."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {message}"
    state["logs"].append(entry)
    if len(state["logs"]) > 200:
        state["logs"] = state["logs"][-200:]


def _read_logs_from_disk() -> List[str]:
    """Read any .log or .txt files from saved_sessions as recent events."""
    logs: List[str] = []
    if not os.path.isdir(LOGS_DIR):
        return logs
    for fname in sorted(os.listdir(LOGS_DIR), reverse=True):
        if fname.endswith((".log", ".txt")):
            fpath = os.path.join(LOGS_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                logs.append(f"--- {fname} ---")
                logs.extend(line.rstrip() for line in lines[-20:])
            except Exception:
                pass
    return logs[-100:]


# ── UI Sections ──
def _render_status_header(state: Dict[str, Any]) -> None:
    """1. Swarm Status Header"""
    st.subheader("🐝 Swarm Status")

    running = state.get("running", False)
    tier = state.get("autonomy_tier", "DEFAULT")
    revenue = state.get("total_revenue", 0.0)
    profit = state.get("net_profit", 0.0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_color = "🟢" if running else "🔴"
        st.metric("Status", f"{status_color} {'RUNNING' if running else 'STOPPED'}")
    with col2:
        st.metric("Autonomy Tier", tier)
    with col3:
        st.metric("Total Revenue", f"${revenue:,.2f}")
    with col4:
        st.metric("Net Profit", f"${profit:,.2f}")

    st.divider()


def _render_control_buttons(state: Dict[str, Any]) -> None:
    """2. Control Buttons"""
    st.subheader("🎛️ Controls")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("▶️ START SWARM", type="primary"):
            state["running"] = True
            _add_log(state, "Swarm STARTED")
            _save_state(state)
            st.success("Swarm started!")
            time.sleep(0.3)
            st.rerun()
    with col2:
        if st.button("⏹️ STOP SWARM", type="primary"):
            state["running"] = False
            _add_log(state, "Swarm STOPPED")
            _save_state(state)
            st.error("Swarm stopped!")
            time.sleep(0.3)
            st.rerun()
    with col3:
        if st.button("⚡ ONE-SHOT CYCLE"):
            _add_log(state, "One-shot cycle triggered")
            for agent in state.get("agents", {}).values():
                agent["status"] = "running"
            _save_state(state)
            st.info("One-shot cycle executed!")
            time.sleep(0.3)
            st.rerun()
    with col4:
        if st.button("🔄 REFRESH STATUS"):
            st.success("Status refreshed")
            time.sleep(0.2)
            st.rerun()

    st.divider()


def _render_agent_grid(state: Dict[str, Any]) -> None:
    """3. Agent Control Grid (5 columns x 2 rows)"""
    st.subheader("🤖 Agents")

    agents = state.get("agents", {})
    rows = [AGENTS[i : i + 5] for i in range(0, len(AGENTS), 5)]

    for row in rows:
        cols = st.columns(5)
        for col, name in zip(cols, row):
            with col:
                info = agents.get(name, {"status": "idle", "revenue": 0.0})
                status_emoji = "🟢" if info.get("status") == "running" else "⚪"
                st.markdown(f"**{status_emoji} {name.title()}**")
                st.caption(f"Status: `{info.get('status', 'idle')}`")
                st.caption(f"Revenue: `${info.get('revenue', 0.0):,.2f}`")
                if st.button("CYCLE", key=f"cycle_{name}"):
                    info["status"] = "running"
                    _add_log(state, f"Agent '{name}' cycled manually")
                    _save_state(state)
                    st.success(f"{name.title()} cycled!")
                    time.sleep(0.3)
                    st.rerun()

    st.divider()


def _render_manual_injection(state: Dict[str, Any]) -> None:
    """4. Manual Decision Injection"""
    st.subheader("💉 Manual Decision Injection")

    with st.form("inject_form"):
        agent_name = st.selectbox("Agent", AGENTS, key="inject_agent")
        decision_type = st.text_input("Decision Type", value="create_invoice", key="inject_type")
        payload_json = st.text_area(
            "JSON Payload",
            value='{"amount": 100, "currency": "USD"}',
            height=120,
            key="inject_payload",
        )
        submitted = st.form_submit_button("💉 INJECT DECISION")

        if submitted:
            try:
                payload = json.loads(payload_json) if payload_json.strip() else {}
            except json.JSONDecodeError:
                st.error("Invalid JSON payload")
                return

            _add_log(
                state,
                f"Manual decision injected into '{agent_name}': {decision_type} | {json.dumps(payload)}",
            )
            _save_state(state)
            st.success(f"Decision injected into {agent_name.title()}!")

    st.divider()


def _render_live_log(state: Dict[str, Any]) -> None:
    """5. Live Log"""
    st.subheader("📜 Live Log")

    # Combine persisted logs with any on-disk log files
    disk_logs = _read_logs_from_disk()
    all_logs = disk_logs + state.get("logs", [])
    if not all_logs:
        all_logs = ["[placeholder] No swarm events recorded yet."]

    log_text = "\n".join(all_logs[-100:])
    st.text_area(
        "Recent Events",
        value=log_text,
        height=250,
        key="live_log_area",
        disabled=True,
    )

    st.divider()


def _render_settings(state: Dict[str, Any]) -> None:
    """6. Settings"""
    st.subheader("⚙️ Settings")

    col1, col2 = st.columns(2)
    with col1:
        new_tier = st.radio(
            "Autonomy Tier",
            options=["DEFAULT", "OVERRIDE", "AUTOPILOT"],
            index=["DEFAULT", "OVERRIDE", "AUTOPILOT"].index(
                state.get("autonomy_tier", "DEFAULT")
            ),
            key="settings_tier",
        )
    with col2:
        new_interval = st.slider(
            "Cycle Interval (seconds)",
            min_value=60,
            max_value=3600,
            value=int(state.get("cycle_interval", 300)),
            step=60,
            key="settings_interval",
        )

    if st.button("💾 Save Settings"):
        state["autonomy_tier"] = new_tier
        state["cycle_interval"] = new_interval
        _add_log(state, f"Settings updated: tier={new_tier}, interval={new_interval}s")
        _save_state(state)
        st.success("Settings saved!")
        time.sleep(0.3)
        st.rerun()


# ── Public API ──
def render_swarm_control() -> None:
    """Render the full monetization swarm control panel."""
    state = _load_state()

    st.title("🤖 Monetization Swarm Control")
    st.caption("Manage the 10-agent business swarm")

    _render_status_header(state)
    _render_control_buttons(state)
    _render_agent_grid(state)
    _render_manual_injection(state)
    _render_live_log(state)
    _render_settings(state)
