#!/usr/bin/env python3
"""Capture the Infinite Jukebox Chrome window and save as PNG."""
import sys
import os
import time

try:
    import pygetwindow as gw
except ImportError:
    print("pygetwindow not installed. Install with: pip install pygetwindow")
    sys.exit(1)

try:
    import pyautogui
except ImportError:
    print("pyautogui not installed. Install with: pip install pyautogui")
    sys.exit(1)

OUTPUT_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), "..", "screenshots", "jukebox_current_state.png"
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

def capture_window(win, path):
    time.sleep(0.3)
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(path)
    return path

def main():
    win = find_jukebox_window()
    if not win:
        print("ERROR: No Infinite Jukebox Chrome window found.")
        print("Available windows:")
        for w in gw.getAllWindows():
            if w.title:
                print(f"  - '{w.title}' ({w.width}x{w.height})")
        sys.exit(1)

    print(f"Found window: '{win.title}' ({win.width}x{win.height})")
    try:
        if hasattr(win, "activate"):
            win.activate()
        time.sleep(0.5)
    except Exception as e:
        print(f"Could not activate window: {e}")

    capture_window(win, OUTPUT_PATH)
    print(f"Screenshot saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
