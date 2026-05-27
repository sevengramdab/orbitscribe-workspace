#!/usr/bin/env python3
"""SimplePod launcher — starts API server + Streamlit dashboard."""
import os
import sys
import time
import subprocess
import signal
import socket
import argparse

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


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def _kill_process_on_port(port: int) -> bool:
    """Attempt to kill whatever is listening on the given port (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano", "|", "findstr", f":{port}"],
            capture_output=True, text=True, shell=True
        )
        for line in result.stdout.splitlines():
            if f"LISTENING" in line and f":{port}" in line:
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    print(f"[SimplePod] Killing stale process PID {pid} on port {port}")
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                    time.sleep(1)
                    return True
    except Exception as e:
        print(f"[SimplePod] Warning: could not kill process on port {port}: {e}")
    return False


def wait_for_api(port, max_wait=15):
    import requests
    for i in range(max_wait * 2):
        try:
            r = requests.get(f"http://localhost:{port}/", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
        # Print a dot every 2 seconds to show progress
        if i % 4 == 0 and i > 0:
            print(".", end="", flush=True)
    print()  # newline after dots
    return False


def start_api_server(api_port, env):
    global api_proc
    api_script = os.path.join(SCRIPT_DIR, "remote_api.py")
    print(f"[SimplePod] Starting API server on port {api_port}...")
    api_proc = subprocess.Popen(
        [sys.executable, api_script],
        cwd=SCRIPT_DIR,
        env=env,
        stdout=open(API_LOG, "a"),
        stderr=subprocess.STDOUT,
    )


def main():
    global api_proc

    parser = argparse.ArgumentParser(description="SimplePod launcher")
    parser.add_argument("--api-only", action="store_true", help="Start only the FastAPI backend, no Streamlit")
    parser.add_argument("--api-port", type=int, default=None, help="Override API port")
    parser.add_argument("--streamlit-port", type=int, default=None, help="Override Streamlit port")
    args = parser.parse_args()

    api_port = args.api_port or int(os.environ.get("SIMPLEPOD_API_PORT", "58091"))
    streamlit_port = args.streamlit_port or int(os.environ.get("STREAMLIT_SERVER_PORT", "8501"))
    env = os.environ.copy()
    env["PYTHONPATH"] = SCRIPT_DIR + os.pathsep + env.get("PYTHONPATH", "")

    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # --- Port conflict resolution ---
    if _port_in_use(api_port):
        print(f"[SimplePod] WARNING: Port {api_port} is already in use.")
        _kill_process_on_port(api_port)
        if _port_in_use(api_port):
            print(f"[SimplePod] FATAL: Port {api_port} still in use after cleanup. Another service may be holding it.")
            print(f"[SimplePod] Try:  netstat -ano | findstr :{api_port}")
            sys.exit(1)

    if not args.api_only and _port_in_use(streamlit_port):
        print(f"[SimplePod] WARNING: Port {streamlit_port} is already in use.")
        _kill_process_on_port(streamlit_port)
        if _port_in_use(streamlit_port):
            print(f"[SimplePod] WARNING: Port {streamlit_port} still in use. Streamlit may fail to start.")
            print(f"[SimplePod] Try:  netstat -ano | findstr :{streamlit_port}")

    # --- Start API server ---
    start_api_server(api_port, env)

    if not wait_for_api(api_port):
        print("[SimplePod] FATAL: API server failed to start within timeout.")
        print(f"[SimplePod] Check {API_LOG} for details.")
        # Try to read last few lines of log
        try:
            with open(API_LOG, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if lines:
                    print("[SimplePod] Last log lines:")
                    for line in lines[-10:]:
                        print("  ", line.rstrip())
        except Exception:
            pass
        cleanup()
        return

    print(f"[SimplePod] API server online at http://localhost:{api_port}")
    print(f"[SimplePod] Monetization Dashboard: http://localhost:{api_port}/monetization")

    if args.api_only:
        print("[SimplePod] Running in API-only mode. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
                if api_proc.poll() is not None:
                    print("[SimplePod] API server exited unexpectedly.")
                    break
        except KeyboardInterrupt:
            pass
        finally:
            cleanup()
        return

    # --- Start Streamlit ---
    app_path = os.path.join(SCRIPT_DIR, "app.py")
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", str(streamlit_port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    print(f"[SimplePod] Starting Streamlit dashboard on port {streamlit_port}...")
    print(f"[SimplePod] Streamlit URL: http://localhost:{streamlit_port}")
    try:
        subprocess.run(cmd, cwd=SCRIPT_DIR, env=env)
    finally:
        cleanup()


if __name__ == "__main__":
    main()
