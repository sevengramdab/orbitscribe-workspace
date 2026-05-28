#!/usr/bin/env python3
"""
Swarm Watchdog — monitors main backend (58081) and shadow node (8002).
Restarts shadow node if it dies. Alerts if main backend is unreachable.
"""
import os
import sys
import time
import subprocess
import urllib.request
import logging
from pathlib import Path

LOG_PATH = Path(os.environ.get("USERPROFILE", ".")) / "voice to text engine" / "tools" / "swarm_watchdog.log"
SHADOW_DIR = Path(os.environ.get("USERPROFILE", ".")) / "simplepod-shadow"
SHADOW_BAT = SHADOW_DIR / "shadow-pc-start.bat"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("watchdog")


def check_port(port: int, timeout: int = 5) -> bool:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception as e:
        logger.debug(f"Port {port} check failed: {e}")
        return False


def restart_shadow_node():
    logger.warning("Restarting shadow node...")
    # Kill any existing python processes running shadow_node.py
    try:
        import subprocess as sp
        result = sp.run(["wmic", "process", "where", "CommandLine like '%shadow_node.py%'", "get", "ProcessId"],
                        capture_output=True, text=True)
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                logger.info(f"Killing old shadow node PID {line}")
                sp.run(["taskkill", "/PID", line, "/F"], capture_output=True)
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")

    subprocess.Popen(
        ["cmd", "/c", str(SHADOW_BAT)],
        cwd=str(SHADOW_DIR),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    logger.info("Shadow node restart dispatched.")


def main():
    logger.info("Swarm watchdog started.")
    while True:
        main_ok = check_port(58081)
        shadow_ok = check_port(8002)

        logger.info(f"Health check — main(58081)={'UP' if main_ok else 'DOWN'} shadow(8002)={'UP' if shadow_ok else 'DOWN'}")

        if not main_ok:
            logger.error("Main backend (58081) is DOWN. Extension may need restart.")

        if not shadow_ok:
            restart_shadow_node()

        time.sleep(30)


if __name__ == "__main__":
    main()
