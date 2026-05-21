"""
ACE-Step V1.5 Auto-Launcher
============================
Checks if ACE-Step is installed; if not, clones and installs it.
Then launches the Gradio server in the background.

Usage:
    python tools/launch_acestep.py [--install-path D:\\ACE-Step-1.5]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


DEFAULT_INSTALL_PATH = Path("D:/ACE-Step-1.5")
REPO_URL = "https://github.com/ACE-Step/ACE-Step-1.5.git"


def log(msg: str) -> None:
    print(f"[AceStepLauncher] {msg}", flush=True)


def is_port_open(host: str = "127.0.0.1", port: int = 7860, timeout: float = 2.0) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def check_acestep_online() -> bool:
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:7860/gradio_api/info",
            method="GET",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def find_uv() -> str:
    for candidate in ["uv", "uv.exe", str(Path.home() / ".local" / "bin" / "uv.exe")]:
        try:
            subprocess.run([candidate, "--version"], capture_output=True, check=True)
            return candidate
        except Exception:
            pass
    raise RuntimeError("uv not found. Install it from https://astral.sh/uv")


def find_git() -> str:
    for candidate in ["git", "git.exe"]:
        try:
            subprocess.run([candidate, "--version"], capture_output=True, check=True)
            return candidate
        except Exception:
            pass
    raise RuntimeError("git not found. Install Git for Windows.")


def clone_repo(install_path: Path) -> None:
    git = find_git()
    log(f"Cloning ACE-Step-1.5 into {install_path} ...")
    install_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [git, "clone", "--depth", "1", REPO_URL, str(install_path)],
        check=True,
    )
    log("Clone complete.")


def sync_deps(install_path: Path) -> None:
    uv = find_uv()
    log("Syncing dependencies with uv (this may take a few minutes)...")
    subprocess.run(
        [uv, "sync"],
        cwd=str(install_path),
        check=True,
    )
    log("Dependencies synced.")


def launch_acestep(install_path: Path) -> subprocess.Popen:
    uv = find_uv()
    log("Launching ACE-Step Gradio server on port 7860...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    # Use uv run to launch acestep
    proc = subprocess.Popen(
        [uv, "run", "acestep"],
        cwd=str(install_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    return proc


def wait_for_ready(timeout: float = 300.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check_acestep_online():
            return True
        time.sleep(2.0)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch ACE-Step V1.5")
    parser.add_argument("--install-path", type=Path, default=DEFAULT_INSTALL_PATH)
    parser.add_argument("--wait", action="store_true", help="Block until server is ready")
    args = parser.parse_args()

    install_path: Path = args.install_path

    if check_acestep_online():
        log("ACE-Step is already running on port 7860.")
        return 0

    if not install_path.exists():
        try:
            clone_repo(install_path)
        except subprocess.CalledProcessError as e:
            log(f"Clone failed: {e}")
            return 1
    else:
        log(f"Using existing installation at {install_path}")

    # Check if uv sync has been run (look for .venv)
    if not (install_path / ".venv").exists() and not (install_path / "uv.lock").exists():
        log("No uv lock found; forcing sync...")
        try:
            sync_deps(install_path)
        except subprocess.CalledProcessError as e:
            log(f"Sync failed: {e}")
            return 1

    # Try launching
    try:
        proc = launch_acestep(install_path)
        log(f"ACE-Step started (PID {proc.pid}).")
    except Exception as e:
        log(f"Launch failed: {e}")
        return 1

    if args.wait:
        log("Waiting for server to be ready...")
        if wait_for_ready():
            log("ACE-Step is online!")
            return 0
        else:
            log("Timed out waiting for ACE-Step.")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
