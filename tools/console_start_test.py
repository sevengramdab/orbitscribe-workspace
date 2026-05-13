#!/usr/bin/env python3
"""Open console drawer and type start command to test fluid."""
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
    os.path.dirname(__file__), "..", "screenshots", "jukebox_console_start.png"
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

def type_in_console(text):
    pyautogui.typewrite(text, interval=0.01)
    time.sleep(0.1)
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(0.3)

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

    # Open console drawer with Ctrl+Shift+J
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('shift')
    pyautogui.keyDown('j')
    pyautogui.keyUp('j')
    pyautogui.keyUp('shift')
    pyautogui.keyUp('ctrl')
    time.sleep(1.0)

    # Type commands in console
    type_in_console("console.log('fluid exists:', !!window.jukeboxFluid)")
    type_in_console("if (window.jukeboxFluid) { window.jukeboxFluid.start(); console.log('started'); } else { console.log('NO FLUID'); }")
    
    time.sleep(3)
    
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(OUTPUT_PATH)
    print(f"Screenshot saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
