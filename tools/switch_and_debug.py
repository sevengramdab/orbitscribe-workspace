#!/usr/bin/env python3
"""Switch back to jukebox tab, open console, check window.jukeboxFluid, screenshot."""
import sys
import os
import time

try:
    import pygetwindow as gw
except ImportError:
    print("pygetwindow not installed.")
    sys.exit(1)

try:
    import pyautogui
except ImportError:
    print("pyautogui not installed.")
    sys.exit(1)

OUTPUT_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), "..", "screenshots", "jukebox_debug.png"
)
OUTPUT_PATH = os.path.abspath(OUTPUT_PATH)

def find_chrome_window():
    windows = gw.getAllWindows()
    candidates = []
    for w in windows:
        if not w.title:
            continue
        if "google chrome" in w.title.lower():
            candidates.append(w)
    if not candidates:
        return None
    candidates.sort(key=lambda w: w.width * w.height, reverse=True)
    return candidates[0]

def main():
    win = find_chrome_window()
    if not win:
        print("ERROR: No Chrome window found.")
        sys.exit(1)

    print(f"Found window: '{win.title}' ({win.width}x{win.height})")
    try:
        if hasattr(win, "activate"):
            win.activate()
        time.sleep(0.5)
    except Exception as e:
        print(f"Could not activate: {e}")

    # Switch to first tab (jukebox)
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('1')
    pyautogui.keyUp('1')
    pyautogui.keyUp('ctrl')
    time.sleep(0.5)

    # Open devtools
    pyautogui.keyDown('f12')
    pyautogui.keyUp('f12')
    time.sleep(0.8)

    # Click console input (bottom right)
    console_x = win.left + win.width - 150
    console_y = win.top + win.height - 50
    pyautogui.click(console_x, console_y)
    time.sleep(0.3)

    # Check if jukeboxFluid exists
    pyautogui.typewrite("window.jukeboxFluid", interval=0.01)
    time.sleep(0.1)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(0.3)

    # Also check for errors
    pyautogui.typewrite("document.getElementById('btn-start')", interval=0.01)
    time.sleep(0.1)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(0.3)

    # Screenshot
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(OUTPUT_PATH)
    print(f"Screenshot saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
