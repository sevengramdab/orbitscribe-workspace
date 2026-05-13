#!/usr/bin/env python3
"""Close devtools by clicking on page then pressing F12."""
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

    # Click on page content (left side, away from devtools)
    pyautogui.click(win.left + 200, win.top + 300)
    time.sleep(0.3)

    # Press F12 to close devtools
    pyautogui.keyDown('f12')
    pyautogui.keyUp('f12')
    time.sleep(0.5)

    print("Done")

if __name__ == "__main__":
    main()
