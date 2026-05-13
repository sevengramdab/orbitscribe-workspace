#!/usr/bin/env python3
"""Click the Initialize Engine button directly, wait, screenshot."""
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
    os.path.dirname(__file__), "..", "screenshots", "jukebox_clicked.png"
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

    try:
        if hasattr(win, "activate"):
            win.activate()
        time.sleep(0.5)
    except Exception as e:
        print(f"Could not activate: {e}")

    # Ensure devtools are closed
    pyautogui.keyDown('f12')
    pyautogui.keyUp('f12')
    time.sleep(0.5)

    # Click directly on the Initialize Engine button text
    # The button is at bottom center, roughly y=0.92 of window height
    cx = win.left + win.width // 2
    cy = win.top + int(win.height * 0.92)
    pyautogui.click(cx, cy)
    print(f"Clicked button at ({cx}, {cy})")
    time.sleep(0.5)

    # Wait for fluid to develop
    print("Waiting 12 seconds for fluid to develop...")
    time.sleep(12.0)

    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(OUTPUT_PATH)
    print(f"Screenshot saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
