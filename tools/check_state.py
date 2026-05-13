#!/usr/bin/env python3
"""Check fluid state via console tab in right panel."""
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
    os.path.dirname(__file__), "..", "screenshots", "jukebox_state.png"
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

    # Click Console tab in right panel (calibrated for 1696x1018)
    console_tab_x = win.left + int(win.width * 0.73)
    console_tab_y = win.top + 115
    pyautogui.click(console_tab_x, console_tab_y)
    time.sleep(0.5)

    # Click in console input area at bottom of right panel
    input_x = win.left + int(win.width * 0.82)
    input_y = win.top + int(win.height * 0.96)
    pyautogui.click(input_x, input_y)
    time.sleep(0.3)

    type_in_console("console.log('dyeRes:', window.jukeboxFluid.dyeResolution, 'simRes:', window.jukeboxFluid.simResolution)")
    type_in_console("console.log('bloom:', window.jukeboxFluid.bloomIntensity)")
    
    time.sleep(1)
    
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(OUTPUT_PATH)
    print(f"Screenshot saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
