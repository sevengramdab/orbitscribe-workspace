#!/usr/bin/env python3
"""Full test: hard reload, click Initialize Engine, wait, screenshot."""
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
    os.path.dirname(__file__), "..", "screenshots", "jukebox_full_test.png"
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

    # Close console if open
    pyautogui.keyDown('f12')
    pyautogui.keyUp('f12')
    time.sleep(0.5)

    # Hard reload
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('f5')
    pyautogui.keyUp('f5')
    pyautogui.keyUp('ctrl')
    print("Hard reload sent...")
    time.sleep(7)

    # Click the Initialize Engine button
    btn_x = win.left + int(win.width * 0.32)
    btn_y = win.top + int(win.height * 0.93)
    pyautogui.click(btn_x, btn_y)
    print(f"Clicked button at ({btn_x}, {btn_y})")
    time.sleep(10)

    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(OUTPUT_PATH)
    print(f"Screenshot saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
