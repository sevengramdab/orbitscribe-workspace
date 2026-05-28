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
        "me_status": None,
        "me_refresh": 0,
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

# ── Sidebar Navigation ──
with st.sidebar:
    st.header("🧭 Navigation")
    page = st.radio(
        "Go to",
        [
            "📊 Dashboard",
            "🕸️ Mesh Network",
            "📁 Projects",
            "🛠️ Tools",
            "💰 Monetization",
            "📊 Status",
            "🖥️ Execute",
            "🔧 Setup",
            "📁 Files",
            "📷 Screen",
            "📁 Remote Files",
        ],
        label_visibility="collapsed",
    )

    st.divider()
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


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.header("📊 Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Node Name", NODE_NAME)
    with c2:
        st.metric("Role", NODE_ROLE)
    with c3:
        peer_count = len(st.session_state.discovery.get_peers())
        st.metric("Discovered Peers", peer_count)
    with c4:
        st.metric("Node ID", NODE_ID[:8] + "...")

    st.divider()
    st.subheader("Quick Actions")
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if st.button("🔄 Refresh Discovery"):
            st.session_state.discovery.discover()
            st.rerun()
    with qa2:
        if st.button("📊 Check Local Backend"):
            try:
                r = requests.get("http://127.0.0.1:58081/api/health", timeout=3)
                st.success(f"Backend healthy: {r.json()}")
            except Exception as e:
                st.error(f"Backend unreachable: {e}")
    with qa3:
        if st.button("💰 Check Money Engine"):
            try:
                from money_engine_bridge import get_status
                status = get_status()
                if status.get("ok"):
                    st.success(f"Money Engine: ${status.get('net_profit', 0):.2f} profit")
                else:
                    st.warning(f"Money Engine: {status.get('error')}")
            except Exception as e:
                st.error(f"Money Engine not available: {e}")

    st.divider()
    st.subheader("Connected Peer Status")
    if not st.session_state.client:
        st.info("No peer connected. Use the sidebar to connect to a discovered peer.")
    else:
        if st.button("🔄 Refresh Status", key="dash_refresh"):
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


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Mesh Network
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🕸️ Mesh Network":
    st.header("🕸️ Mesh Network")
    st.info("Mesh network visualization and node management.")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Discovered Nodes")
        peers = st.session_state.discovery.get_peers()
        if not peers:
            st.warning("No nodes discovered yet.")
        else:
            for p in peers:
                with st.container():
                    st.write(f"**{p.name}** ({p.role})")
                    st.caption(f"{p.ip}:{p.api_port} | ID: {p.node_id}")
                    if st.button("Ping", key=f"mesh_ping_{p.node_id}"):
                        try:
                            r = requests.get(f"http://{p.ip}:{p.api_port}/health", timeout=3)
                            st.success(f"Alive — {r.status_code}")
                        except Exception as e:
                            st.error(f"Unreachable: {e}")
    with c2:
        st.subheader("Local Node Info")
        st.json({
            "node_id": NODE_ID,
            "name": NODE_NAME,
            "role": NODE_ROLE,
            "api_port": API_PORT,
        })
        st.subheader("Backend Nodes (58081)")
        try:
            r = requests.get("http://127.0.0.1:58081/api/nodes", timeout=3)
            nodes = r.json().get("nodes", [])
            if nodes:
                for n in nodes:
                    st.write(f"• **{n.get('name', '?')}** — {n.get('status', '?')} ({n.get('latency_ms', '?')}ms)")
            else:
                st.info("No backend nodes registered.")
        except Exception as e:
            st.warning(f"Backend nodes unavailable: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Projects
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📁 Projects":
    st.header("📁 Projects")
    st.info("Project workspace management.")

    try:
        r = requests.get("http://127.0.0.1:58081/api/workspace", timeout=3)
        workspace = r.json().get("workspace_root", "Unknown")
        st.write(f"**Current workspace:** `{workspace}`")
    except Exception:
        st.warning("Could not fetch workspace from backend.")

    new_workspace = st.text_input("Set workspace root", value="")
    if st.button("Update Workspace") and new_workspace:
        try:
            r = requests.post(
                "http://127.0.0.1:58081/api/workspace",
                json={"workspace_root": new_workspace},
                timeout=3,
            )
            if r.json().get("ok"):
                st.success("Workspace updated")
            else:
                st.error("Update failed")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    st.subheader("Saved Sessions")
    try:
        r = requests.get("http://127.0.0.1:58081/api/sessions", timeout=3)
        sessions = r.json().get("sessions", [])
        if sessions:
            for s in sessions:
                st.write(f"• `{s}`")
        else:
            st.info("No saved sessions.")
    except Exception:
        st.warning("Sessions endpoint unavailable.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Tools
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🛠️ Tools":
    st.header("🛠️ Tools")
    st.info("Utility tools and integrations.")

    tool = st.selectbox(
        "Select tool",
        ["Etsy Listing Generator", "Etsy Keywords", "Etsy Pricing", "URL Shortener", "QR Generator"],
    )

    if tool == "Etsy Listing Generator":
        product = st.text_input("Product name")
        category = st.text_input("Category", value="General Handmade")
        if st.button("Generate") and product:
            try:
                r = requests.post(
                    "http://127.0.0.1:58081/api/tools/etsy/listing",
                    json={"product_name": product, "category": category},
                    timeout=30,
                )
                data = r.json()
                if data.get("ok") and data.get("listing"):
                    st.json(data["listing"])
                else:
                    st.code(data.get("listing_raw", "No output"))
            except Exception as e:
                st.error(f"Error: {e}")

    elif tool == "Etsy Keywords":
        niche = st.text_input("Niche")
        if st.button("Generate Keywords") and niche:
            try:
                r = requests.post(
                    "http://127.0.0.1:58081/api/tools/etsy/keywords",
                    json={"niche": niche},
                    timeout=30,
                )
                st.json(r.json())
            except Exception as e:
                st.error(f"Error: {e}")

    elif tool == "Etsy Pricing":
        cost = st.number_input("Product cost", value=10.0)
        shipping = st.number_input("Shipping cost", value=0.0)
        margin = st.number_input("Target margin %", value=40.0)
        if st.button("Calculate"):
            try:
                r = requests.post(
                    "http://127.0.0.1:58081/api/tools/etsy/pricing",
                    json={"product_cost": cost, "shipping_cost": shipping, "target_margin": margin},
                    timeout=10,
                )
                st.json(r.json())
            except Exception as e:
                st.error(f"Error: {e}")

    elif tool in ("URL Shortener", "QR Generator"):
        st.info(f"{tool} would be launched as a micro-app here.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Monetization (fully integrated)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💰 Monetization":
    st.header("💰 Monetization Swarm Command Center")

    # Try to import the bridge
    try:
        from money_engine_bridge import get_status, start_swarm, stop_swarm, list_pending, approve_decision, reject_decision
        bridge_available = True
    except Exception as e:
        bridge_available = False
        st.error(f"Money Engine bridge not available: {e}")

    if bridge_available:
        # ── Status & Metrics ──
        if st.button("🔄 Refresh") or st.session_state.me_refresh == 0:
            st.session_state.me_status = get_status()
            st.session_state.me_refresh += 1

        status = st.session_state.me_status or {}
        if status.get("ok"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Net Profit", f"${status.get('net_profit', 0):.2f}")
            with col2:
                st.metric("Total Revenue", f"${status.get('total_revenue', 0):.2f}")
            with col3:
                st.metric("Active Agents", len(status.get("agents", {})))
            with col4:
                st.metric("Autonomy", status.get("autonomy_tier", "DEFAULT"))

            # ── Control Panel ──
            st.divider()
            st.subheader("Control Panel")
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                autonomy = st.selectbox(
                    "Autonomy Mode",
                    ["DEFAULT", "OVERRIDE", "AUTOPILOT"],
                    index=["DEFAULT", "OVERRIDE", "AUTOPILOT"].index(status.get("autonomy_tier", "DEFAULT")),
                )
            with c2:
                interval = st.number_input("Interval (sec)", value=status.get("cycle_interval", 300), min_value=30)
            with c3:
                st.write("Actions")
                start_col, stop_col = st.columns(2)
                with start_col:
                    if st.button("▶️ Start", type="primary"):
                        result = start_swarm(autonomy_tier=autonomy, interval_seconds=int(interval))
                        if result.get("ok"):
                            st.success("Swarm started")
                        else:
                            st.error(result.get("error", "Start failed"))
                        st.session_state.me_status = get_status()
                        st.rerun()
                with stop_col:
                    if st.button("⏹️ Stop", type="secondary"):
                        result = stop_swarm()
                        if result.get("ok"):
                            st.success("Swarm stopped")
                        else:
                            st.error(result.get("error", "Stop failed"))
                        st.session_state.me_status = get_status()
                        st.rerun()

            # ── Agents ──
            st.divider()
            st.subheader("Agents")
            agents = status.get("agents", {})
            if agents:
                for aid, data in agents.items():
                    with st.container():
                        c1, c2, c3 = st.columns([3, 2, 1])
                        with c1:
                            st.write(f"**{data.get('vertical', aid).title()}**")
                            st.caption(f"Status: {data.get('status', 'idle')} | Decisions: {data.get('decisions_executed', 0)}")
                        with c2:
                            revenue = data.get("revenue", 0)
                            st.write(f"💰 `${revenue:.2f}`")
                        with c3:
                            if st.button("Cycle", key=f"cycle_{aid}"):
                                from money_engine_bridge import inject_decision
                                inject_decision(aid, "cycle", {})
                                st.success("Cycled")
                                st.session_state.me_status = get_status()
                                st.rerun()
            else:
                st.info("No agents running. Start the swarm to activate agents.")

            # ── Pending Decisions (Kimi Bridge) ──
            st.divider()
            st.subheader("⏳ Pending Decisions")
            pending = list_pending()
            if pending:
                for p in pending:
                    with st.container():
                        st.write(f"**{p.get('agent_id', '?')}** — {p.get('action', '?')}")
                        st.caption(p.get("reasoning", "No reasoning"))
                        st.json(p.get("params", {}))
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Approve", key=f"app_{p['decision_id']}"):
                                approve_decision(p["decision_id"])
                                st.success("Approved")
                                st.rerun()
                        with c2:
                            if st.button("❌ Reject", key=f"rej_{p['decision_id']}"):
                                reject_decision(p["decision_id"])
                                st.success("Rejected")
                                st.rerun()
            else:
                st.info("No pending decisions. Decisions appear here when agents require approval.")

            # ── Logs ──
            st.divider()
            st.subheader("Event Log")
            logs = status.get("logs", [])
            if logs:
                st.code("\n".join(logs[-20:]), language="text")
            else:
                st.info("No logs yet.")
        else:
            st.warning(f"Money Engine status unavailable: {status.get('error', 'Unknown error')}")
            st.info("Tip: Make sure the Money Engine dependencies are installed.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Status
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Status":
    st.header("📊 Remote Status")
    if not st.session_state.client:
        st.info("Connect to a peer from the sidebar to see remote status.")
    else:
        if st.button("🔄 Refresh Status", key="status_refresh"):
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


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Execute
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🖥️ Execute":
    st.header("🖥️ Remote Execute")
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


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Setup
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔧 Setup":
    st.header("🔧 Remote Setup")
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


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Files
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📁 Files":
    st.header("📁 File Transfer")
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


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Screen
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📷 Screen":
    st.header("📷 Remote Screen")
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


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Remote Files
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📁 Remote Files":
    st.header("📁 Remote Files")
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
