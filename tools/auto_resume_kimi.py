#!/usr/bin/env python3
"""
Auto-resume Kimi Code: session after VS Code: reload.
Run this as a DETACHED process before reloading VS Code:.

Usage:
    python auto_resume_kimi.py [context_file_path]

It will:
1. Wait for VS Code: window to appear
2. Wait for extensions + backend to fully load
3. Open Kimi Code: via Command Palette (reliable)
4. Click Kimi Code: sidebar History -> most recent session
5. Type the saved context into the chat input and press Enter
"""
import sys
import os
import time
import subprocess
import urllib.request

CONTEXT_FILE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '.reload-context.txt'
)

WAIT_FOR_VSCODE = 20       # max seconds to wait for VS Code: window
WAIT_FOR_EXTENSIONS = 10   # seconds to wait for extensions after window appears
WAIT_FOR_BACKEND = 30      # max seconds to wait for backend health
CLICK_DELAY = 1.0          # delay between clicks
TYPE_INTERVAL = 0.01       # typing speed (slower = more reliable)
MAX_RETRIES = 3


def import_gui():
    try:
        import pygetwindow as gw
        import pyautogui
        pyautogui.FAILSAFE = True
        return gw, pyautogui
    except ImportError as e:
        print(f"[auto_resume] Missing dependency: {e}")
        print("[auto_resume] Install with: pip install pygetwindow pyautogui")
        sys.exit(1)


def find_vscode_window(gw):
    """Find VS Code: or Cursor window."""
    for w in gw.getAllWindows():
        if not w.title:
            continue
        if 'Visual Studio Code' in w.title or 'Cursor' in w.title:
            return w
    return None


def load_context():
    """Read and delete the context file."""
    if not os.path.exists(CONTEXT_FILE):
        return None
    try:
        with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
            context = f.read().strip()
        os.remove(CONTEXT_FILE)
        return context
    except Exception as e:
        print(f"[auto_resume] Error reading context: {e}")
        return None


def is_backend_healthy():
    """Poll the OrbitScribe swarm backend."""
    try:
        req = urllib.request.Request("http://127.0.0.1:58081/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_backend(max_seconds=WAIT_FOR_BACKEND):
    """Block until backend is healthy or timeout."""
    print(f"[auto_resume] Waiting up to {max_seconds}s for backend...")
    for i in range(max_seconds * 2):
        if is_backend_healthy():
            print("[auto_resume] Backend is online.")
            return True
        time.sleep(0.5)
    print("[auto_resume] WARNING: Backend not healthy yet. Proceeding anyway.")
    return False


def click_at(win, rel_x, rel_y, pyautogui, label=""):
    """Click at coordinates relative to the window."""
    x = win.left + rel_x
    y = win.top + rel_y
    pyautogui.click(x, y)
    if label:
        print(f"[auto_resume] Clicked {label} at ({x}, {y})")


def focus_input_via_command_palette(win, pyautogui):
    """Use VS Code: Command Palette to focus Kimi input (reliable)."""
    print("[auto_resume] Focusing Kimi input via Command Palette...")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('shift')
    pyautogui.keyDown('p')
    pyautogui.keyUp('p')
    pyautogui.keyUp('shift')
    pyautogui.keyUp('ctrl')
    time.sleep(0.8)
    send_keys(pyautogui, "Kimi Code: Focus Input", "focus input command")
    time.sleep(0.5)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(1.0)


def send_keys(pyautogui, keys, label=""):
    """Safely send keystrokes with a small delay."""
    pyautogui.typewrite(keys, interval=TYPE_INTERVAL)
    if label:
        print(f"[auto_resume] Sent keys: {label}")


def take_screenshot(pyautogui, win, name):
    """Save a screenshot for debugging."""
    try:
        ss_dir = os.path.join(os.path.dirname(__file__), '..', 'screenshots')
        os.makedirs(ss_dir, exist_ok=True)
        ss_path = os.path.join(ss_dir, f"{name}.png")
        ss = pyautogui.screenshot(region=(win.left, win.top, win.width, win.height))
        ss.save(ss_path)
        print(f"[auto_resume] Screenshot: {ss_path}")
        return ss_path
    except Exception as e:
        print(f"[auto_resume] Screenshot failed: {e}")
        return None


def open_kimi_via_command_palette(win, pyautogui):
    """Use VS Code: Command Palette to open Kimi sidebar (reliable)."""
    print("[auto_resume] Opening Kimi via Command Palette...")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('shift')
    pyautogui.keyDown('p')
    pyautogui.keyUp('p')
    pyautogui.keyUp('shift')
    pyautogui.keyUp('ctrl')
    time.sleep(0.8)
    send_keys(pyautogui, "Kimi Code: Open in Side Panel", "open sidebar command")
    time.sleep(0.5)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(2.0)


def compute_coordinates(win):
    """Compute UI coordinates based on actual window size."""
    # Sidebar is typically ~260-300px wide on the left
    sidebar_width = min(300, max(200, int(win.width * 0.18)))

    # History button: near top-right of sidebar
    history_x = sidebar_width - 20
    history_y = min(100, int(win.height * 0.08) + 40)

    # First session item: below history button
    session_x = sidebar_width - 20
    session_y = history_y + 50

    # Chat input: near bottom of window, inside sidebar area
    input_x = sidebar_width // 2
    input_y = win.height - 80

    # Kimi icon in activity bar (leftmost)
    kimi_icon_x = 25
    kimi_icon_y = int(win.height * 0.18)

    return {
        'history': (history_x, history_y),
        'session': (session_x, session_y),
        'input': (input_x, input_y),
        'kimi_icon': (kimi_icon_x, kimi_icon_y),
    }


def main():
    gw, pyautogui = import_gui()
    context = load_context()

    if not context:
        print("[auto_resume] No context to resume. Exiting.")
        return

    # Truncate context if too long (prevent input overflow)
    if len(context) > 4000:
        print(f"[auto_resume] Context too long ({len(context)} chars), truncating to 4000.")
        context = context[:4000] + "\n[truncated]"

    print(f"[auto_resume] Context loaded ({len(context)} chars)")
    print(f"[auto_resume] Waiting up to {WAIT_FOR_VSCODE}s for VS Code: window...")

    win = None
    for i in range(WAIT_FOR_VSCODE * 2):
        win = find_vscode_window(gw)
        if win:
            break
        time.sleep(0.5)

    if not win:
        print("[auto_resume] ERROR: VS Code: window not found.")
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            f.write(context)
        return

    print(f"[auto_resume] Window found: '{win.title}' ({win.width}x{win.height})")

    try:
        win.activate()
    except Exception as e:
        print(f"[auto_resume] Could not activate window: {e}")

    # Wait for extensions to settle
    print(f"[auto_resume] Waiting {WAIT_FOR_EXTENSIONS}s for extensions...")
    time.sleep(WAIT_FOR_EXTENSIONS)

    # Wait for backend before doing any UI interaction
    wait_for_backend(WAIT_FOR_BACKEND)

    # Compute coordinates based on actual window size
    coords = compute_coordinates(win)
    print(f"[auto_resume] Coordinates: {coords}")

    # Step 1: Open Kimi sidebar via Command Palette (most reliable)
    open_kimi_via_command_palette(win, pyautogui)
    take_screenshot(pyautogui, win, "01_after_open_sidebar")

    # Step 2: Try clicking History button (with retries)
    history_x, history_y = coords['history']
    for attempt in range(MAX_RETRIES):
        click_at(win, history_x, history_y, pyautogui, f"History button (attempt {attempt+1})")
        time.sleep(CLICK_DELAY)
        take_screenshot(pyautogui, win, f"02_after_history_click_{attempt+1}")
        # We can't easily verify if the dropdown opened, so we just proceed
        break

    # Step 3: Click first session in dropdown
    session_x, session_y = coords['session']
    click_at(win, session_x, session_y, pyautogui, "most recent session")
    time.sleep(CLICK_DELAY + 1.5)
    take_screenshot(pyautogui, win, "03_after_session_click")

    # Step 4: Focus chat input via Command Palette (much more reliable than clicking)
    focus_input_via_command_palette(win, pyautogui)
    take_screenshot(pyautogui, win, "04_after_input_focus")

    # Step 5: Type context (slowly and safely)
    print("[auto_resume] Typing context into chat input...")
    send_keys(pyautogui, context, "context message")
    time.sleep(0.5)

    # Step 6: Press Enter to send
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    print("[auto_resume] Message sent!")
    time.sleep(1.0)
    take_screenshot(pyautogui, win, "05_after_send")

    print("[auto_resume] Done.")


if __name__ == '__main__':
    main()
