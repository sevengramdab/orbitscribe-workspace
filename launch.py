#!/usr/bin/env python3
"""
OrbitScribe Auto-Launcher
=========================
One command to rule them all:
  1. Checks / starts Ollama
  2. Starts the Swarm Backend
  3. Opens VS Code: with the extension loaded

Usage:
    python launch.py          # Dev mode (opens extension folder, press F5)
    python launch.py --install # Package & install .vsix into VS Code:
    python launch.py --run     # Dev mode + auto F5 (launch Extension Host)
"""
import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
SWARM_BACKEND = PROJECT_ROOT / "swarm-backend"
EXTENSION = PROJECT_ROOT / "extension"
VSCODE_EXE = None


def find_vscode() -> str | None:
    """Find VS Code: executable on Windows."""
    global VSCODE_EXE
    if VSCODE_EXE:
        return VSCODE_EXE
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
        r"C:\Program Files\Microsoft VS Code\bin\code.cmd",
        r"C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd",
    ]
    for c in candidates:
        if os.path.exists(c):
            VSCODE_EXE = c
            return c
    # Try PATH
    try:
        result = subprocess.run(["where", "code"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            VSCODE_EXE = result.stdout.strip().splitlines()[0]
            return VSCODE_EXE
    except Exception:
        pass
    return None


def is_ollama_running() -> bool:
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_ollama() -> subprocess.Popen | None:
    print("[Launcher] Starting Ollama...")
    try:
        # Try to start ollama in background (hidden window on Windows)
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            proc = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            proc = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        # Wait for it to come online
        for _ in range(20):
            time.sleep(0.5)
            if is_ollama_running():
                print("[Launcher] Ollama is online.")
                return proc
        print("[Launcher] WARNING: Ollama started but not responding yet.")
        return proc
    except FileNotFoundError:
        print("[Launcher] ERROR: Ollama not found in PATH. Install from https://ollama.com")
        return None
    except Exception as e:
        print(f"[Launcher] ERROR starting Ollama: {e}")
        return None


def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def kill_stale_python_on_port(port: int) -> bool:
    import re
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line:
                    parts = line.strip().split()
                    pid = parts[-1]
                    if re.match(r"^\d+$", pid):
                        tasklist = subprocess.run(
                            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                            capture_output=True, text=True, timeout=3,
                        )
                        if "python" in tasklist.stdout.lower():
                            print(f"[Launcher] Killing stale python.exe on port {port} (PID {pid})")
                            subprocess.run(["taskkill", "/F", "/PID", pid], timeout=3)
                            return True
        else:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
            )
            for pid in result.stdout.strip().splitlines():
                pid = pid.strip()
                if pid:
                    print(f"[Launcher] Killing stale process on port {port} (PID {pid})")
                    subprocess.run(["kill", "-9", pid], timeout=3)
                    return True
    except Exception:
        pass
    return False


def find_free_port(start_port: int, range_size: int = 10) -> int | None:
    for p in range(start_port, start_port + range_size):
        if not is_port_in_use(p):
            return p
    return None


def resolve_port(port: int) -> int:
    if not is_port_in_use(port):
        return port
    if kill_stale_python_on_port(port):
        time.sleep(1)
        if not is_port_in_use(port):
            print(f"[Launcher] Port {port} freed.")
            return port
    free = find_free_port(port + 1)
    if free:
        print(f"[Launcher] Port {port} occupied. Using fallback port {free}.")
        return free
    print(f"[Launcher] FATAL: No free port found in range {port + 1}-{port + 9}")
    sys.exit(1)


def is_backend_running(port: int = 58081) -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_backend() -> tuple[subprocess.Popen | None, int]:
    port = resolve_port(58081)
    print(f"[Launcher] Starting Swarm Backend on port {port}...")
    python = sys.executable
    main_py = SWARM_BACKEND / "main.py"
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["SWARM_PORT"] = str(port)
    try:
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            proc = subprocess.Popen(
                [python, str(main_py)],
                cwd=str(SWARM_BACKEND),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            proc = subprocess.Popen(
                [python, str(main_py)],
                cwd=str(SWARM_BACKEND),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
        # Wait for it to come online
        for _ in range(20):
            time.sleep(0.5)
            if is_backend_running(port):
                print(f"[Launcher] Swarm Backend is online at http://127.0.0.1:{port}")
                return proc, port
        print("[Launcher] WARNING: Backend started but not responding yet.")
        return proc, port
    except Exception as e:
        print(f"[Launcher] ERROR starting backend: {e}")
        return None, port


def package_extension() -> Path | None:
    print("[Launcher] Packaging extension...")
    try:
        # On Windows, npx may need to be called as npx.cmd
        npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
        result = subprocess.run(
            [npx_cmd, "vsce", "package"],
            cwd=str(EXTENSION),
            capture_output=True,
            text=True,
            timeout=60,
            shell=True if sys.platform == "win32" else False,
        )
        if result.returncode != 0:
            print(f"[Launcher] Packaging failed:\n{result.stderr}")
            return None
        # Find the generated .vsix
        vsix_files = list(EXTENSION.glob("*.vsix"))
        if vsix_files:
            print(f"[Launcher] Packaged: {vsix_files[0].name}")
            return vsix_files[0]
        return None
    except Exception as e:
        print(f"[Launcher] ERROR packaging: {e}")
        return None


def install_extension(vsix: Path) -> bool:
    print(f"[Launcher] Installing {vsix.name} into VS Code:...")
    code = find_vscode()
    if not code:
        print("[Launcher] ERROR: VS Code: not found. Cannot install extension.")
        return False
    try:
        result = subprocess.run(
            [code, "--install-extension", str(vsix)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("[Launcher] Extension installed. Reload VS Code: to activate.")
            return True
        else:
            print(f"[Launcher] Install output: {result.stderr or result.stdout}")
            return False
    except Exception as e:
        print(f"[Launcher] ERROR installing: {e}")
        return False


def open_vscode_dev() -> bool:
    code = find_vscode()
    if not code:
        print("[Launcher] ERROR: VS Code: not found.")
        print("[Launcher] Install from https://code.visualstudio.com/")
        return False
    print(f"[Launcher] Opening VS Code: extension workspace...")
    try:
        subprocess.Popen(
            [code, str(EXTENSION)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("[Launcher] VS Code: opened. Press F5 to launch Extension Development Host.")
        return True
    except Exception as e:
        print(f"[Launcher] ERROR opening VS Code:: {e}")
        return False


def open_vscode_run() -> bool:
    """Open VS Code: extension workspace AND auto-launch Extension Host (F5 equivalent)."""
    code = find_vscode()
    if not code:
        print("[Launcher] ERROR: VS Code: not found.")
        return False
    print(f"[Launcher] Launching VS Code: Extension Development Host...")
    try:
        # Launch VS Code: with the extension folder, then run the extension
        subprocess.Popen(
            [code, "--extensionDevelopmentPath", str(EXTENSION)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("[Launcher] Extension Development Host launched!")
        print("[Launcher] Look for the 🐝 OrbitScribe icon in the Activity Bar.")
        return True
    except Exception as e:
        print(f"[Launcher] ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="OrbitScribe Auto-Launcher")
    parser.add_argument("--install", action="store_true", help="Package and install .vsix into VS Code:")
    parser.add_argument("--run", action="store_true", help="Launch Extension Development Host directly")
    args = parser.parse_args()

    print("=" * 60)
    print("  ORBITSCRIBE AUTO-LAUNCHER")
    print("=" * 60)

    # 1. Ollama
    if is_ollama_running():
        print("[Launcher] Ollama is already running.")
    else:
        ollama_proc = start_ollama()
        if not ollama_proc:
            print("[Launcher] Continuing without Ollama — cloud mode will be used if configured.")

    # 2. Swarm Backend
    if is_backend_running():
        print("[Launcher] Swarm Backend is already running.")
    else:
        backend_proc, backend_port = start_backend()
        if not backend_proc:
            print("[Launcher] FATAL: Could not start swarm backend.")
            sys.exit(1)

    # Small delay to let things settle
    time.sleep(1)

    # 3. VS Code:
    if args.install:
        vsix = package_extension()
        if vsix:
            install_extension(vsix)
        else:
            print("[Launcher] Skipping install — packaging failed.")
    elif args.run:
        open_vscode_run()
    else:
        open_vscode_dev()

    print("=" * 60)
    print("  All systems go. Happy swarming!")
    print("=" * 60)


if __name__ == "__main__":
    main()
