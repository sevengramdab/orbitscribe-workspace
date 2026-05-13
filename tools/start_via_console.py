#!/usr/bin/env python3
"""Use Chrome DevTools console to start the jukebox engine, then capture screenshot."""
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
    os.path.dirname(__file__), "..", "screenshots", "jukebox_running.png"
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

    # Open devtools
    pyautogui.keyDown('f12')
    pyautogui.keyUp('f12')
    time.sleep(0.8)

    # Click in console input area (bottom of devtools panel on right)
    # DevTools is on the right side, console input is near bottom-right
    console_x = win.left + win.width - 100
    console_y = win.top + win.height - 80
    pyautogui.click(console_x, console_y)
    time.sleep(0.3)

    # Type command to click the start button
    cmd = "document.getElementById('btn-start').click()"
    pyautogui.typewrite(cmd, interval=0.01)
    time.sleep(0.2)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    print("Sent console command to click btn-start")
    time.sleep(0.5)

    # Close devtools
    pyautogui.keyDown('f12')
    pyautogui.keyUp('f12')
    time.sleep(0.5)

    # Wait for fluid to develop
    print("Waiting 12 seconds for fluid to develop...")
    time.sleep(12.0)

    # Screenshot
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(OUTPUT_PATH)
    print(f"Screenshot saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
