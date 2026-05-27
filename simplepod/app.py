"""SimplePod — Streamlit remote control dashboard.
Run on both computers. They auto-discover each other via UDP broadcast.
"""
import base64
import os
import sys
import time
import threading
from typing import Optional

import streamlit as st
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NODE_ID, NODE_NAME, NODE_ROLE, API_PORT
from discovery import DiscoveryService, Peer
from client import PeerClient

st.set_page_config(page_title="SimplePod", page_icon="🛰️", layout="wide")

# ── Session state ──
def ensure_state():
    defaults = {
        "discovery": None,
        "connected_peer": None,
        "client": None,
        "logs": [],
        "auto_connect": True,
        "remote_status": None,
        "remote_path": ".",
        "remote_files": [],
        "pending_download": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if st.session_state.discovery is None:
        st.session_state.discovery = DiscoveryService(on_peer_found=_on_peer_found)
        st.session_state.discovery.start()


def _on_peer_found(peer: Peer) -> None:
    _log(f"🟢 Discovered: {peer.name} ({peer.role}) at {peer.ip}:{peer.api_port}")
    if st.session_state.auto_connect and not st.session_state.connected_peer:
        _connect_to(peer)


def _connect_to(peer: Peer) -> None:
    st.session_state.connected_peer = peer
    st.session_state.client = PeerClient(peer.api_url())
    _log(f"🔗 Connected to {peer.name}")


def _disconnect() -> None:
    if st.session_state.connected_peer:
        _log(f"🔴 Disconnected from {st.session_state.connected_peer.name}")
    st.session_state.connected_peer = None
    st.session_state.client = None


def _log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{ts}] {msg}")
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
        except requests.exceptions.ConnectionError:
            st.error("💥 Connection lost. Peer may have gone offline.")
            st.session_state.client = None
            return None
        except Exception as e:
            st.error(f"Request failed: {e}")
            return None


ensure_state()

# ── Header ──
st.title("🛰️ SimplePod")
st.caption(f"This node: **{NODE_NAME}** (`{NODE_ROLE}`) — ID: `{NODE_ID}`")

# Check if local API is reachable
col_h1, col_h2 = st.columns([3, 1])
with col_h2:
    try:
        r = requests.get("http://localhost:58091/", timeout=2)
        if r.status_code == 200:
            st.success("API online")
        else:
            st.warning("API offline")
    except Exception:
        st.error("API unreachable")

# ── Sidebar ──
with st.sidebar:
    st.header("Peers")
    peers = st.session_state.discovery.get_peers()
    if not peers:
        st.info("No peers discovered yet...")
    else:
        for p in peers:
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"**{p.name}** ({p.role})")
                st.caption(f"{p.ip}:{p.api_port}")
            with c2:
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
        st.caption(f"{peer.api_url()}")
        if st.button("Disconnect"):
            _disconnect()
            st.rerun()

        if st.button("💓 Heartbeat"):
            result = _run_client_method(st.session_state.client.health)
            if result and result.get("ok"):
                latency = result.get("latency_ms", "?")
                st.success(f"Peer is alive — latency: {latency}ms")
            elif result:
                st.error(result.get("error", "Heartbeat failed"))
    else:
        st.warning("No peer connected")

    st.divider()
    st.header("Event Log")
    for line in reversed(st.session_state.logs[-15:]):
        st.text(line)

# ── Tabs ──
tab_status, tab_exec, tab_setup, tab_files, tab_screen, tab_remote_files, tab_monetization = st.tabs(
    ["📊 Status", "🖥️ Execute", "🔧 Setup", "📁 Files", "📷 Screen", "📁 Remote Files", "💰 Monetization"]
)

with tab_status:
    if not st.session_state.client:
        st.info("Connect to a peer from the sidebar to see remote status.")
    else:
        if st.button("🔄 Refresh Status"):
            result = _run_client_method(st.session_state.client.status)
            if result and result.get("ok"):
                st.session_state.remote_status = result
            elif result:
                st.error(result.get("error", "Unknown error"))

        if st.session_state.remote_status:
            s = st.session_state.remote_status
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Platform", s.get("platform", "?"))
                st.metric("Role", s.get("role", "?"))
            with c2:
                st.metric("CPU %", s.get("cpu_percent", "N/A"))
                st.metric("Python", s.get("python_version", "?"))
            with c3:
                mu = s.get("memory_used_gb")
                mt = s.get("memory_total_gb")
                if mu is not None and mt is not None:
                    st.metric("Memory", f"{mu} / {mt} GB")
                df = s.get("disk_free_gb")
                if df is not None:
                    st.metric("Disk Free", f"{df} GB")
            st.json(s)

with tab_exec:
    if not st.session_state.client:
        st.info("Connect to a peer to run remote commands.")
    else:
        cmd = st.text_input("Command", value="whoami", key="exec_cmd")
        cwd = st.text_input("Working dir (optional)", value="", key="exec_cwd")
        timeout = st.slider("Timeout", 5, 120, 30, key="exec_timeout")
        if st.button("▶️ Run"):
            result = _run_client_method(
                st.session_state.client.exec, cmd, cwd=cwd or None, timeout=timeout
            )
            if result:
                st.metric("Return Code", result.get("returncode", "?"))
                if result.get("stdout"):
                    st.code(result["stdout"], language="bash")
                if result.get("stderr"):
                    st.code(result["stderr"], language="bash")
                if result.get("error"):
                    st.error(result["error"])

with tab_setup:
    if not st.session_state.client:
        st.info("Connect to a peer to run setup scripts.")
    else:
        desc = st.text_input("Description", value="Install dependencies", key="setup_desc")
        script = st.text_area("Script", height=200, key="setup_script")
        if st.button("🔧 Run Setup"):
            result = _run_client_method(
                st.session_state.client.setup, script, description=desc
            )
            if result:
                st.metric("Return Code", result.get("returncode", "?"))
                if result.get("stdout"):
                    st.code(result["stdout"], language="bash")
                if result.get("stderr"):
                    st.code(result["stderr"], language="bash")

with tab_files:
    if not st.session_state.client:
        st.info("Connect to a peer to transfer files.")
    else:
        uploaded = st.file_uploader("Choose file", key="file_up")
        if uploaded and st.button("📤 Send"):
            result = _run_client_method(
                st.session_state.client.sync_file, uploaded.name, uploaded.getvalue()
            )
            if result:
                if result.get("ok"):
                    st.success(f"Saved to: `{result.get('saved_to')}`")
                else:
                    st.error(result.get("error", "Unknown error"))

with tab_screen:
    if not st.session_state.client:
        st.info("Connect to a peer to view remote screen.")
    else:
        auto_refresh = st.checkbox("Auto-refresh every 5s", key="screen_auto_refresh")
        placeholder = st.empty()

        if st.button("📸 Capture") or auto_refresh:
            result = _run_client_method(st.session_state.client.screenshot)
            if result and result.get("image_b64"):
                with placeholder.container():
                    st.image(base64.b64decode(result["image_b64"]), use_column_width=True)
            elif result:
                st.error(result.get("error", "Screenshot failed"))

        if auto_refresh:
            time.sleep(5)
            st.rerun()

with tab_remote_files:
    if not st.session_state.client:
        st.info("Connect to a peer to browse remote files.")
    else:
        path = st.text_input(
            "Remote path", value=st.session_state.remote_path, key="remote_path_input"
        )
        if st.button("📂 List Files"):
            result = _run_client_method(st.session_state.client.list_files, path)
            if result and result.get("ok"):
                st.session_state.remote_files = result.get("files", [])
                st.session_state.remote_path = path
            elif result:
                st.error(result.get("error", "Failed to list files"))

        if st.session_state.remote_files:
            files = st.session_state.remote_files
            st.write(f"**{len(files)}** items in `{st.session_state.remote_path}`")

            # Header row
            h1, h2, h3, h4 = st.columns([4, 2, 1, 1])
            h1.write("**Name**")
            h2.write("**Size**")
            h3.write("")
            h4.write("")

            for i, f in enumerate(files):
                c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
                with c1:
                    if f.get("is_dir"):
                        if st.button(f"📁 {f['name']}", key=f"cd_{i}"):
                            new_path = os.path.join(st.session_state.remote_path, f["name"])
                            st.session_state.remote_path = os.path.normpath(new_path)
                            st.session_state.remote_files = []
                            st.rerun()
                    else:
                        st.write(f"📄 {f['name']}")
                with c2:
                    if f.get("is_dir"):
                        st.write("—")
                    else:
                        st.write(f"{f.get('size', 0):,}")
                with c3:
                    if not f.get("is_dir"):
                        if st.button("⬇️", key=f"dl_{i}"):
                            file_path = os.path.join(st.session_state.remote_path, f["name"])
                            result = _run_client_method(
                                st.session_state.client.download_file, file_path
                            )
                            if result and result.get("content_b64"):
                                st.session_state.pending_download = {
                                    "name": f["name"],
                                    "data": base64.b64decode(result["content_b64"]),
                                }
                                st.rerun()
                with c4:
                    if st.button("🗑️", key=f"del_{i}"):
                        file_path = os.path.join(st.session_state.remote_path, f["name"])
                        result = _run_client_method(
                            st.session_state.client.delete_file, file_path
                        )
                        if result and result.get("ok"):
                            st.success(f"Deleted `{f['name']}`")
                            st.session_state.remote_files = []
                            st.rerun()
                        elif result:
                            st.error(result.get("error", "Delete failed"))

            if st.session_state.pending_download:
                pd = st.session_state.pending_download
                st.download_button(
                    label=f"⬇️ Download {pd['name']}",
                    data=pd["data"],
                    file_name=pd["name"],
                    key="pending_dl_btn",
                )
                if st.button("Clear download"):
                    st.session_state.pending_download = None
                    st.rerun()

with tab_monetization:
    st.info("The monetization dashboard is now served directly by the FastAPI backend.")
    st.write("Open the dashboard in your browser for the full experience with all 8 sections:")
    st.write("• Overview • Financial Analysis • API Settings • Credentials • Marketplace • Stats • Links • Swarm Control")
    
    api_port = os.environ.get("SIMPLEPOD_API_PORT", "58091")
    dashboard_url = f"http://localhost:{api_port}/monetization"
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 Open Monetization Dashboard", type="primary"):
            import webbrowser
            webbrowser.open(dashboard_url)
            st.success(f"Opened {dashboard_url}")
    with col2:
        st.code(dashboard_url, language="text")
    
    st.divider()
    st.caption("Tip: You can also access it from any device on your network by replacing `localhost` with this machine's IP address.")
