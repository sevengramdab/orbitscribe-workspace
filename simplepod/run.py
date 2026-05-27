#!/usr/bin/env python3
"""SimplePod launcher.

Usage:
    python run.py

Environment variables:
    SIMPLEPOD_ROLE=shadow       # or 'local'
    SIMPLEPOD_NODE_NAME=ShadowPC
    SIMPLEPOD_API_PORT=58091
    SIMPLEPOD_DISCOVERY_PORT=58090
    SIMPLEPOD_TOKEN=mysecret
"""
import os
import sys
import subprocess

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")

    # Ensure streamlit is available
    try:
        import streamlit
    except ImportError:
        print("[SimplePod] Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", os.path.join(script_dir, "requirements.txt")])

    # Launch Streamlit
    port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", port,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    print(f"[SimplePod] Starting Streamlit on port {port}...")
    os.execv(sys.executable, cmd)


if __name__ == "__main__":
    main()
