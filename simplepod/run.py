#!/usr/bin/env python3
"""SimplePod launcher — starts API server + Streamlit dashboard."""
import os
import sys
import time
import subprocess
import signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_LOG = os.path.join(SCRIPT_DIR, "api_server.log")

api_proc = None

def cleanup(signum=None, frame=None):
    print("[SimplePod] Shutting down...")
    if api_proc and api_proc.poll() is None:
        api_proc.terminate()
        try:
            api_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_proc.kill()
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def wait_for_api(port, max_wait=15):
    import requests
    for _ in range(max_wait * 2):
        try:
            r = requests.get(f"http://localhost:{port}/", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    global api_proc
    api_port = os.environ.get("SIMPLEPOD_API_PORT", "58091")
    streamlit_port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
    env = os.environ.copy()
    env["PYTHONPATH"] = SCRIPT_DIR + os.pathsep + env.get("PYTHONPATH", "")

    # Start API server as subprocess
    api_script = os.path.join(SCRIPT_DIR, "remote_api.py")
    print(f"[SimplePod] Starting API server on port {api_port}...")
    api_proc = subprocess.Popen(
        [sys.executable, api_script],
        cwd=SCRIPT_DIR,
        env=env,
        stdout=open(API_LOG, "a"),
        stderr=subprocess.STDOUT,
    )

    if not wait_for_api(api_port):
        print("[SimplePod] FATAL: API server failed to start. Check api_server.log")
        cleanup()
        return
    print("[SimplePod] API server online.")

    # Start Streamlit
    app_path = os.path.join(SCRIPT_DIR, "app.py")
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", streamlit_port,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    print(f"[SimplePod] Dashboard: http://localhost:{streamlit_port}")
    try:
        subprocess.run(cmd, cwd=SCRIPT_DIR, env=env)
    finally:
        cleanup()

if __name__ == "__main__":
    main()
