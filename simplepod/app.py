"""SimplePod — Streamlit remote control dashboard.

Run on both computers. They auto-discover each other via UDP broadcast.
Either side can control the other.
"""
import os
import sys
import time
import threading
from typing import Optional

import streamlit as st

# Ensure simplepod modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import NODE_ID, NODE_NAME, NODE_ROLE, API_PORT
from discovery import DiscoveryService, Peer
from client import PeerClient

# ── Page config ──
st.set_page_config(page_title="SimplePod", page_icon="🛰️", layout="wide")

# ── Session state init ──
def ensure_state():
    if "discovery" not in st.session_state:
        st.session_state.discovery = DiscoveryService(on_peer_found=_on_peer_found)
        st.session_state.discovery.start()
    if "api_thread" not in st.session_state:
        st.session_state.api_thread = threading.Thread(target=_start_api, daemon=True)
        st.session_state.api_thread.start()
    if "connected_peer" not in st.session_state:
        st.session_state.connected_peer = None
    if "client" not in st.session_state:
        st.session_state.client = None
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "auto_connect" not in st.session_state:
        st.session_state.auto_connect = True


def _start_api():
    from remote_api import start_api_server
    start_api_server()


def _on_peer_found(peer: Peer) -> None:
    _log(f"🟢 Discovered peer: {peer.name} ({peer.role}) at {peer.ip}:{peer.api_port}")
    if st.session_state.auto_connect and not st.session_state.connected_peer:
        _connect_to(peer)


def _connect_to(peer: Peer) -> None:
    st.session_state.connected_peer = peer
    st.session_state.client = PeerClient(peer.api_url())
    _log(f"🔗 Connected to {peer.name} ({peer.role})")


def _disconnect() -> None:
    if st.session_state.connected_peer:
        _log(f"🔴 Disconnected from {st.session_state.connected_peer.name}")
    st.session_state.connected_peer = None
    st.session_state.client = None


def _log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{ts}] {msg}")
    # Keep last 100
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]


def _run_client_method(method, *args, **kwargs):
    client: Optional[PeerClient] = st.session_state.client
    if not client:
        st.error("Not connected to any peer.")
        return None
    with st.spinner(f"Talking to {st.session_state.connected_peer.name}..."):
        try:
            return method(*args, **kwargs)
        except Exception as e:
            st.error(f"Request failed: {e}")
            return None


# ── UI ──
ensure_state()

st.title("🛰️ SimplePod")
st.caption(f"This node: **{NODE_NAME}** (`{NODE_ROLE}`) — ID: `{NODE_ID}`")

# Sidebar: peers & connection
with st.sidebar:
    st.header("Peers")
    peers = st.session_state.discovery.get_peers()
    if not peers:
        st.info("No peers discovered yet. Waiting for UDP broadcasts...")
    else:
        for p in peers:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{p.name}** ({p.role})")
                st.caption(f"{p.ip}:{p.api_port}")
            with col2:
                if st.button("Connect", key=f"conn_{p.node_id}"):
                    _connect_to(p)
                    st.rerun()

    st.divider()
    st.checkbox("Auto-connect on discovery", key="auto_connect")

    st.divider()
    st.header("Connection")
    peer = st.session_state.connected_peer
    if peer:
        st.success(f"Connected to **{peer.name}**")
        st.caption(f"Role: `{peer.role}` | URL: {peer.api_url()}")
        if st.button("Disconnect"):
            _disconnect()
            st.rerun()
    else:
        st.warning("No peer connected")

    st.divider()
    st.header("Event Log")
    for line in reversed(st.session_state.logs[-20:]):
        st.text(line)

# Main tabs
tab_status, tab_exec, tab_setup, tab_files = st.tabs([
    "📊 Status", "🖥️ Execute", "🔧 Setup", "📁 Files"
])

# ── Status Tab ──
with tab_status:
    if not st.session_state.client:
        st.info("Connect to a peer from the sidebar to see remote status.")
    else:
        if st.button("🔄 Refresh Status"):
            result = _run_client_method(st.session_state.client.status)
            if result and result.get("ok"):
                st.session_state.remote_status = result
            else:
                st.error(result.get("error", "Unknown error"))

        if "remote_status" in st.session_state:
            s = st.session_state.remote_status
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Platform", s.get("platform", "?"))
                st.metric("Role", s.get("role", "?"))
            with col2:
                st.metric("CPU %", s.get("cpu_percent", "N/A"))
                st.metric("Python", s.get("python_version", "?"))
            with col3:
                mem_used = s.get("memory_used_gb")
                mem_total = s.get("memory_total_gb")
                if mem_used is not None and mem_total is not None:
                    st.metric("Memory", f"{mem_used} / {mem_total} GB")
                disk = s.get("disk_free_gb")
                if disk is not None:
                    st.metric("Disk Free", f"{disk} GB")
            st.json(s)

# ── Execute Tab ──
with tab_exec:
    if not st.session_state.client:
        st.info("Connect to a peer to run remote commands.")
    else:
        cmd = st.text_input("Command to run on remote peer", value="whoami", key="exec_cmd")
        cwd = st.text_input("Working directory (optional)", value="", key="exec_cwd")
        timeout = st.slider("Timeout (seconds)", 5, 120, 30, key="exec_timeout")
        if st.button("▶️ Run"):
            result = _run_client_method(
                st.session_state.client.exec,
                cmd,
                cwd=cwd or None,
                timeout=timeout,
            )
            if result:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Return Code", result.get("returncode", "?"))
                with col2:
                    st.write("**OK:**" if result.get("ok") else "**Failed**")
                if result.get("stdout"):
                    st.subheader("stdout")
                    st.code(result["stdout"], language="bash")
                if result.get("stderr"):
                    st.subheader("stderr")
                    st.code(result["stderr"], language="bash")
                if result.get("error"):
                    st.error(result["error"])

# ── Setup Tab ──
with tab_setup:
    if not st.session_state.client:
        st.info("Connect to a peer to run setup scripts.")
    else:
        st.write("Run a setup / bootstrap script on the remote peer.")
        desc = st.text_input("Description", value="Install dependencies", key="setup_desc")
        script = st.text_area(
            "Script",
            value="" if os.name == "nt" else "#!/bin/bash\necho 'Hello from setup'",
            height=200,
            key="setup_script",
        )
        if st.button("🔧 Run Setup"):
            result = _run_client_method(
                st.session_state.client.setup,
                script,
                description=desc,
            )
            if result:
                st.write(f"**Description:** {result.get('description', '')}")
                st.metric("Return Code", result.get("returncode", "?"))
                if result.get("stdout"):
                    st.code(result["stdout"], language="bash")
                if result.get("stderr"):
                    st.code(result["stderr"], language="bash")
                if result.get("error"):
                    st.error(result["error"])

# ── Files Tab ──
with tab_files:
    if not st.session_state.client:
        st.info("Connect to a peer to transfer files.")
    else:
        uploaded = st.file_uploader("Choose a file to send to peer", key="file_up")
        if uploaded and st.button("📤 Send File"):
            data = uploaded.getvalue()
            result = _run_client_method(
                st.session_state.client.sync_file,
                uploaded.name,
                data,
            )
            if result:
                if result.get("ok"):
                    st.success(f"Saved to: `{result.get('saved_to')}`")
                else:
                    st.error(result.get("error", "Unknown error"))

# Footer
st.divider()
st.caption(f"SimplePod v1.0 | Discovery port {st.session_state.discovery._sock.getsockname()[1] if st.session_state.discovery._sock else '?'} | API port {API_PORT}")
