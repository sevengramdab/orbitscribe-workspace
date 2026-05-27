#!/usr/bin/env python3
"""
Auto-resume Kimi Code: session after VS Code: reload — TERMINAL-BASED APPROACH.
This uses Kimi's native CLI session resumption instead of fragile coordinate clicking.

Usage:
    python auto_resume_kimi_v2.py [context_file_path]

Flow:
1. Wait for VS Code: window
2. Wait for backend to be healthy
3. Open integrated terminal (Ctrl+`)
4. Wait for shell to initialize (~2.5s)
5. Run: kimi -r <session_id> -w <work_dir>
6. Wait for TUI to load
7. Type the saved context and press Enter
"""
import sys
import os
import time
import urllib.request
import subprocess

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
CONTEXT_FILE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TOOLS_DIR, '.reload-context.txt')
SESSION_ID_FILE = os.path.join(TOOLS_DIR, '.kimi-last-session')

WAIT_FOR_VSCODE = 20
WAIT_FOR_BACKEND = 30
WAIT_FOR_TUI = 8
TYPE_INTERVAL = 0.01

LOG_FILE = os.path.join(ROOT_DIR, 'auto_resume_v2.log')
CIRCUIT_BREAKER_FILE = os.path.join(TOOLS_DIR, '.resume-circuit-breaker')
MAX_RESTARTS_IN_WINDOW = 3
CIRCUIT_WINDOW_SECONDS = 120


def check_circuit_breaker():
    """Abort if we've restarted too many times recently (prevents infinite loops)."""
    now = time.time()
    try:
        if os.path.exists(CIRCUIT_BREAKER_FILE):
            with open(CIRCUIT_BREAKER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            timestamps = [t for t in data.get('starts', []) if now - t < CIRCUIT_WINDOW_SECONDS]
            if len(timestamps) >= MAX_RESTARTS_IN_WINDOW:
                log(f"CIRCUIT BREAKER: {len(timestamps)} restarts in {CIRCUIT_WINDOW_SECONDS}s. Aborting to prevent infinite loop.")
                return False
            timestamps.append(now)
        else:
            timestamps = [now]
        with open(CIRCUIT_BREAKER_FILE, 'w', encoding='utf-8') as f:
            json.dump({'starts': timestamps}, f)
        return True
    except Exception as e:
        log(f"Circuit breaker check failed: {e}. Proceeding anyway.")
        return True


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def import_gui():
    try:
        import pygetwindow as gw
        import pyautogui
        pyautogui.FAILSAFE = True
        return gw, pyautogui
    except ImportError as e:
        log(f"Missing dependency: {e}. Install: pip install pygetwindow pyautogui")
        sys.exit(1)


def find_vscode_window(gw):
    for w in gw.getAllWindows():
        if not w.title:
            continue
        if 'Visual Studio Code' in w.title or 'Cursor' in w.title:
            return w
    return None


def is_backend_healthy():
    try:
        req = urllib.request.Request("http://127.0.0.1:58081/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_backend(max_seconds=WAIT_FOR_BACKEND):
    log(f"Waiting up to {max_seconds}s for backend...")
    for i in range(max_seconds * 2):
        if is_backend_healthy():
            log("Backend is online.")
            return True
        time.sleep(0.5)
    log("WARNING: Backend not healthy. Proceeding anyway.")
    return False


def get_session_id():
    """Resolve session ID from file or latest directory."""
    # 1. Try saved session file
    if os.path.exists(SESSION_ID_FILE):
        try:
            sid = open(SESSION_ID_FILE, 'r', encoding='utf-8').read().strip()
            if sid:
                log(f"Using saved session: {sid}")
                return sid
        except Exception:
            pass

    # 2. Try most recent session directory
    sessions_dir = os.path.join(os.path.expanduser('~'), '.kimi', 'sessions')
    if os.path.isdir(sessions_dir):
        try:
            dirs = sorted(
                [d for d in os.listdir(sessions_dir) if os.path.isdir(os.path.join(sessions_dir, d))],
                key=lambda x: os.path.getmtime(os.path.join(sessions_dir, x)),
                reverse=True
            )
            if dirs:
                sid = dirs[0]
                log(f"Using latest session dir: {sid}")
                return sid
        except Exception:
            pass

    return None


def load_context():
    if not os.path.exists(CONTEXT_FILE):
        return None
    try:
        with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
            context = f.read().strip()
        os.remove(CONTEXT_FILE)
        return context
    except Exception as e:
        log(f"Error reading context: {e}")
        return None


def open_terminal(win, pyautogui):
    """Open integrated terminal via Command Palette (reliable)."""
    log("Opening integrated terminal via Command Palette...")
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


def type_command(pyautogui, cmd):
    """Type a command safely."""
    log(f"Typing command: {cmd}")
    pyautogui.typewrite(cmd, interval=TYPE_INTERVAL)
    time.sleep(0.3)


def press_enter(pyautogui):
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(0.3)


def send_ctrl_c(pyautogui):
    """Send Ctrl+C to cancel any running process in terminal."""
    log("Sending Ctrl+C to ensure clean prompt...")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('c')
    pyautogui.keyUp('c')
    pyautogui.keyUp('ctrl')
    time.sleep(0.5)


def take_screenshot(pyautogui, win, name):
    try:
        ss_dir = os.path.join(ROOT_DIR, 'screenshots')
        os.makedirs(ss_dir, exist_ok=True)
        ss_path = os.path.join(ss_dir, f"{name}.png")
        ss = pyautogui.screenshot(region=(win.left, win.top, win.width, win.height))
        ss.save(ss_path)
        log(f"Screenshot: {ss_path}")
        return ss_path
    except Exception as e:
        log(f"Screenshot failed: {e}")
        return None


def compute_coordinates(win):
    """Compute UI coordinates based on actual window size."""
    sidebar_width = min(300, max(200, int(win.width * 0.18)))
    history_x = sidebar_width - 20
    history_y = min(100, int(win.height * 0.08) + 40)
    session_x = sidebar_width - 20
    session_y = history_y + 50
    return {
        'history': (history_x, history_y),
        'session': (session_x, session_y),
    }


def attempt_webview_restore(win, pyautogui):
    """Best-effort webview session restore (fallback). Does not type context."""
    log("Attempting webview session restore as fallback...")
    try:
        # Open Kimi sidebar via Command Palette
        pyautogui.keyDown('ctrl')
        pyautogui.keyDown('shift')
        pyautogui.keyDown('p')
        pyautogui.keyUp('p')
        pyautogui.keyUp('shift')
        pyautogui.keyUp('ctrl')
        time.sleep(0.8)
        pyautogui.typewrite("Kimi Code: Open in Side Panel", interval=TYPE_INTERVAL)
        time.sleep(0.5)
        pyautogui.keyDown('return')
        pyautogui.keyUp('return')
        time.sleep(2.0)

        coords = compute_coordinates(win)
        # Click History
        hx, hy = coords['history']
        x = win.left + hx
        y = win.top + hy
        pyautogui.click(x, y)
        log(f"Clicked History button at ({x}, {y})")
        time.sleep(1.0)

        # Click first session in dropdown
        sx, sy = coords['session']
        x = win.left + sx
        y = win.top + sy
        pyautogui.click(x, y)
        log(f"Clicked most recent session at ({x}, {y})")
        time.sleep(1.5)
        take_screenshot(pyautogui, win, "v2_06_webview_fallback")
        log("Webview fallback attempt complete.")
    except Exception as e:
        log(f"Webview fallback failed (non-critical): {e}")


def main():
    gw, pyautogui = import_gui()

    # Clear old log
    try:
        open(LOG_FILE, 'w').close()
    except Exception:
        pass

    # Circuit breaker: prevent infinite restart loops
    import json
    if not check_circuit_breaker():
        sys.exit(1)

    # Check if extension already handled auto-resume
    lock_file = os.path.join(TOOLS_DIR, '.reload-resume-lock')
    if os.path.exists(lock_file):
        try:
            import json
            with open(lock_file, 'r') as f:
                lock = json.load(f)
            lock_age = (time.time() * 1000 - lock.get('timestamp', 0)) / 1000
            if lock_age < 45:
                log(f"Extension lock file exists (age={lock_age:.0f}s). Extension auto-resume in progress. Skipping.")
                return
        except Exception:
            pass

    # Check if Kimi is already running
    try:
        import subprocess
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq kimi.exe'],
                                capture_output=True, text=True, timeout=5)
        if 'kimi.exe' in result.stdout:
            log("Kimi process already running. Extension auto-resume likely succeeded. Skipping.")
            return
    except Exception:
        pass

    context = load_context()
    if not context:
        log("No context to resume. Exiting.")
        return

    # Truncate if too long
    if len(context) > 4000:
        log(f"Context too long ({len(context)}), truncating to 4000 chars.")
        context = context[:4000] + "\n[truncated]"

    session_id = get_session_id()
    if not session_id:
        log("ERROR: No Kimi session ID found. Cannot resume.")
        # Write context back for manual retry
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            f.write(context)
        return

    log(f"Context: {len(context)} chars | Session: {session_id}")

    # 1. Find VS Code: window
    log(f"Waiting up to {WAIT_FOR_VSCODE}s for VS Code: window...")
    win = None
    for i in range(WAIT_FOR_VSCODE * 2):
        win = find_vscode_window(gw)
        if win:
            break
        time.sleep(0.5)

    if not win:
        log("ERROR: VS Code: window not found.")
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            f.write(context)
        return

    log(f"Window: '{win.title}' ({win.width}x{win.height})")
    try:
        win.activate()
    except Exception as e:
        log(f"Could not activate window: {e}")

    # 2. Wait for backend
    wait_for_backend(WAIT_FOR_BACKEND)

    # 3. Open terminal
    open_terminal(win, pyautogui)
    take_screenshot(pyautogui, win, "v2_01_terminal_opened")

    # 4. Wait for PowerShell to fully initialize in the new terminal
    log("Waiting 2.5s for terminal shell to initialize...")
    time.sleep(2.5)

    # 5. Ensure clean prompt
    send_ctrl_c(pyautogui)
    time.sleep(0.5)

    # 6. Show recent chat history before resuming
    history_cmd = f'python tools/show_kimi_history.py {session_id} --turns 5'
    type_command(pyautogui, history_cmd)
    press_enter(pyautogui)
    time.sleep(2.0)

    # 7. Build and type the resume command
    work_dir = ROOT_DIR
    cmd = f'kimi -r {session_id} -w "{work_dir}"'
    type_command(pyautogui, cmd)
    press_enter(pyautogui)
    log("Resume command sent. Waiting for TUI to load...")
    take_screenshot(pyautogui, win, "v2_02_after_resume_cmd")

    # 8. Wait for TUI to initialize
    time.sleep(WAIT_FOR_TUI)
    take_screenshot(pyautogui, win, "v2_03_after_tui_wait")

    # 9. Type context message
    log("Typing context into TUI...")
    pyautogui.typewrite(context, interval=TYPE_INTERVAL)
    time.sleep(0.3)
    take_screenshot(pyautogui, win, "v2_04_after_typing")

    # 10. Press Enter to send
    press_enter(pyautogui)
    log("Message sent! Session resumed in terminal.")
    take_screenshot(pyautogui, win, "v2_05_after_send")

    # 9. Best-effort webview fallback (no context typed, just restore session)
    time.sleep(1.0)
    attempt_webview_restore(win, pyautogui)

    log("Done.")


if __name__ == '__main__':
    main()
