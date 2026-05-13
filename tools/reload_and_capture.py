#!/usr/bin/env python3
"""Hard-reload the Jukebox page and capture a screenshot."""
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
    os.path.dirname(__file__), "..", "screenshots", "jukebox_after_reload.png"
)
OUTPUT_PATH = os.path.abspath(OUTPUT_PATH)

def find_jukebox_window():
    windows = gw.getAllWindows()
    candidates = []
    for w in windows:
        if not w.title:
            continue
        if "infinite jukebox" in w.title.lower():
            candidates.append(w)
    if not candidates:
        return None
    candidates.sort(key=lambda w: w.width * w.height, reverse=True)
    return candidates[0]

def main():
    win = find_jukebox_window()
    if not win:
        print("ERROR: No Infinite Jukebox window found.")
        sys.exit(1)

    print(f"Found window: '{win.title}' ({win.width}x{win.height})")
    try:
        if hasattr(win, "activate"):
            win.activate()
        time.sleep(0.5)
    except Exception as e:
        print(f"Could not activate: {e}")

    # Click center of page to focus, then hard reload
    cx = win.left + win.width // 2
    cy = win.top + win.height // 2
    pyautogui.click(cx, cy)
    time.sleep(0.2)
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('f5')
    pyautogui.keyUp('f5')
    pyautogui.keyUp('ctrl')
    print("Hard reload sent (Ctrl+F5)")
    time.sleep(3.0)

    # Screenshot
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(OUTPUT_PATH)
    print(f"Screenshot saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
