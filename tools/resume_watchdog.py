#!/usr/bin/env python3
"""
Resume Watchdog — External safety-net daemon for OrbitScribe crash recovery.

Monitors the extension heartbeat file. If the extension host dies (stale heartbeat)
but VS Code: is still running, this daemon automatically opens the integrated terminal
and resumes the Kimi CLI session.

Started automatically by the OrbitScribe extension on activate().
"""
import sys
import os
import time
import json
import subprocess

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
HEARTBEAT_FILE = os.path.join(TOOLS_DIR, '.orbitscribe-heartbeat')
PID_FILE = os.path.join(TOOLS_DIR, '.watchdog.pid')
RECOVERY_LOCK = os.path.join(TOOLS_DIR, '.recovery-in-progress')
SESSION_FILE = os.path.join(TOOLS_DIR, '.kimi-last-session')
RESUME_CMD_FILE = os.path.join(TOOLS_DIR, '.kimi-resume-cmd.txt')
CONTEXT_FILE = os.path.join(TOOLS_DIR, '.reload-context.txt')
LOG_FILE = os.path.join(TOOLS_DIR, 'resume_watchdog.log')

CHECK_INTERVAL = 30          # seconds between heartbeat checks
STALE_THRESHOLD = 180        # 3 minutes without heartbeat = potential crash
RECOVERY_TIMEOUT = 300       # 5 minutes max for a recovery attempt
WAIT_FOR_VSCODE = 20
WAIT_FOR_TUI = 8
TYPE_INTERVAL = 0.01


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def is_vscode_running():
    """Check if VS Code: process is alive."""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq Code.exe'],
            capture_output=True, text=True, timeout=5
        )
        return 'Code.exe' in result.stdout
    except Exception:
        return False


def get_session_id():
    """Resolve session ID from file or latest directory."""
    if os.path.exists(SESSION_FILE):
        try:
            sid = open(SESSION_FILE, 'r', encoding='utf-8').read().strip()
            if sid:
                return sid
        except Exception:
            pass
    if os.path.exists(RESUME_CMD_FILE):
        try:
            cmd = open(RESUME_CMD_FILE, 'r', encoding='utf-8').read().strip()
            match = __import__('re').search(r'kimi\s+-r\s+(\S+)', cmd)
            if match:
                return match.group(1)
        except Exception:
            pass
    sessions_dir = os.path.join(os.path.expanduser('~'), '.kimi', 'sessions')
    if os.path.isdir(sessions_dir):
        try:
            dirs = sorted(
                [d for d in os.listdir(sessions_dir) if os.path.isdir(os.path.join(sessions_dir, d))],
                key=lambda x: os.path.getmtime(os.path.join(sessions_dir, x)),
                reverse=True
            )
            if dirs:
                return dirs[0]
        except Exception:
            pass
    return None


def load_context():
    if not os.path.exists(CONTEXT_FILE):
        return 'Continue from where we left off.'
    try:
        with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
            ctx = f.read().strip()
        os.remove(CONTEXT_FILE)
        return ctx if ctx else 'Continue from where we left off.'
    except Exception:
        return 'Continue from where we left off.'


def find_vscode_window(gw):
    for w in gw.getAllWindows():
        if not w.title:
            continue
        if 'Visual Studio Code' in w.title or 'Cursor' in w.title:
            return w
    return None


def open_terminal(win, pyautogui):
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('shift')
    pyautogui.keyDown('p')
    pyautogui.keyUp('p')
    pyautogui.keyUp('shift')
    pyautogui.keyUp('ctrl')
    time.sleep(0.8)
    pyautogui.typewrite("View: Toggle Terminal", interval=0.01)
    time.sleep(0.4)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(1.5)


def send_ctrl_c(pyautogui):
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('c')
    pyautogui.keyUp('c')
    pyautogui.keyUp('ctrl')
    time.sleep(0.5)


def attempt_recovery(session_id, context):
    """Use pyautogui to open terminal and resume Kimi session."""
    try:
        import pygetwindow as gw
        import pyautogui
        pyautogui.FAILSAFE = True
    except ImportError as e:
        log(f"Missing dependency: {e}")
        return False

    log("Waiting for VS Code: window...")
    win = None
    for _ in range(WAIT_FOR_VSCODE * 2):
        win = find_vscode_window(gw)
        if win:
            break
        time.sleep(0.5)
    if not win:
        log("ERROR: VS Code: window not found.")
        return False

    try:
        win.activate()
    except Exception as e:
        log(f"Could not activate window: {e}")

    log(f"Window: '{win.title}' ({win.width}x{win.height})")

    # Open terminal
    open_terminal(win, pyautogui)
    log("Waiting 2.5s for terminal shell to initialize...")
    time.sleep(2.5)
    send_ctrl_c(pyautogui)
    time.sleep(0.5)

    # Show recent chat history before resuming
    history_cmd = f'python tools/show_kimi_history.py {session_id} --turns 5'
    log(f"Typing history command: {history_cmd}")
    pyautogui.typewrite(history_cmd, interval=TYPE_INTERVAL)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(2.0)

    # Type resume command
    cmd = f'kimi -r {session_id} -w "{ROOT_DIR}"'
    log(f"Typing command: {cmd}")
    pyautogui.typewrite(cmd, interval=TYPE_INTERVAL)
    time.sleep(0.3)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    log("Resume command sent. Waiting for TUI...")
    time.sleep(WAIT_FOR_TUI)

    # Type context
    if len(context) > 4000:
        context = context[:4000] + "\n[truncated]"
    log(f"Typing context ({len(context)} chars)...")
    pyautogui.typewrite(context, interval=TYPE_INTERVAL)
    time.sleep(0.3)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    log("Context sent. Recovery complete.")
    return True


def is_recovery_in_progress():
    if not os.path.exists(RECOVERY_LOCK):
        return False
    try:
        data = json.load(open(RECOVERY_LOCK, 'r', encoding='utf-8'))
        age = time.time() - data.get('started', 0)
        return age < RECOVERY_TIMEOUT
    except Exception:
        return False


def set_recovery_lock(active: bool):
    try:
        if active:
            with open(RECOVERY_LOCK, 'w', encoding='utf-8') as f:
                json.dump({'started': time.time()}, f)
        else:
            if os.path.exists(RECOVERY_LOCK):
                os.remove(RECOVERY_LOCK)
    except Exception:
        pass


def get_heartbeat_age():
    """Returns age in seconds, or None if no heartbeat."""
    if not os.path.exists(HEARTBEAT_FILE):
        return None
    try:
        hb = json.load(open(HEARTBEAT_FILE, 'r', encoding='utf-8'))
        if hb.get('status') == 'shutdown':
            return 0  # Treat shutdown as healthy (extension exited cleanly)
        return (time.time() * 1000 - hb.get('timestamp', 0)) / 1000
    except Exception:
        return None


def main():
    # Write PID file
    try:
        with open(PID_FILE, 'w', encoding='utf-8') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        log(f"Failed to write PID file: {e}")
        sys.exit(1)

    log(f"Watchdog started (PID {os.getpid()}). Monitoring {HEARTBEAT_FILE}")

    try:
        while True:
            age = get_heartbeat_age()
            if age is None:
                log("No heartbeat file yet. Waiting...")
            elif age > STALE_THRESHOLD:
                log(f"Stale heartbeat detected ({age:.0f}s old).")
                if not is_vscode_running():
                    log("VS Code: is not running. Waiting...")
                elif is_recovery_in_progress():
                    log("Recovery already in progress. Skipping.")
                else:
                    session_id = get_session_id()
                    if session_id:
                        context = load_context()
                        log(f"Triggering recovery for session {session_id}...")
                        set_recovery_lock(True)
                        success = attempt_recovery(session_id, context)
                        if success:
                            log("Recovery succeeded. Waiting for heartbeat to resume...")
                            # Wait up to 5 min for heartbeat to come back
                            for _ in range(60):
                                time.sleep(5)
                                new_age = get_heartbeat_age()
                                if new_age is not None and new_age < STALE_THRESHOLD:
                                    log("Heartbeat resumed. Watchdog healthy.")
                                    break
                            else:
                                log("Heartbeat did not resume after recovery.")
                        else:
                            log("Recovery failed.")
                        set_recovery_lock(False)
                    else:
                        log("No session ID found. Cannot recover.")
            else:
                # Heartbeat is healthy; clear any stale recovery lock
                if os.path.exists(RECOVERY_LOCK):
                    set_recovery_lock(False)

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        log("Watchdog stopped by user.")
    finally:
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass


if __name__ == '__main__':
    main()
