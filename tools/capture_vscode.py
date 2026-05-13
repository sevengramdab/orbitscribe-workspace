#!/usr/bin/env python3
"""
Capture VS Code:/Cursor window and save as PNG so Kimi can "see" the UI.
Usage: python capture_vscode.py [output_path]
"""
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
    os.path.dirname(__file__), "..", "vscode_screenshot.png"
)
OUTPUT_PATH = os.path.abspath(OUTPUT_PATH)

# Keywords to match VS Code: or Cursor window titles
KEYWORDS = ["Visual Studio Code", "Cursor", "Code:-OSS", "VSCodium"]


def find_vscode_window():
    windows = gw.getAllWindows()
    candidates = []
    for w in windows:
        if not w.title:
            continue
        for kw in KEYWORDS:
            if kw.lower() in w.title.lower():
                candidates.append(w)
                break
    if not candidates:
        return None
    # Prefer the largest window (main editor vs small popups)
    candidates.sort(key=lambda w: w.width * w.height, reverse=True)
    return candidates[0]


def capture_window(win, path):
    # Small delay to let any pending UI render
    time.sleep(0.3)
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(path)
    return path


def main():
    print("[capture_vscode] Searching for VS Code:/Cursor window...")
    win = find_vscode_window()
    if not win:
        print("[capture_vscode] ERROR: No VS Code: or Cursor window found.")
        print("[capture_vscode] Available windows:")
        for w in gw.getAllWindows():
            if w.title:
                print(f"  - '{w.title}' ({w.width}x{w.height})")
        sys.exit(1)

    try:
        print(f"[capture_vscode] Found window: '{win.title}' ({win.width}x{win.height})")
    except UnicodeEncodeError:
        print(f"[capture_vscode] Found window: (title contains unicode) ({win.width}x{win.height})")

    # Bring to front so it's not occluded
    try:
        if hasattr(win, "activate"):
            win.activate()
        time.sleep(0.2)
    except Exception as e:
        print(f"[capture_vscode] Could not activate window: {e}")

    capture_window(win, OUTPUT_PATH)
    print(f"[capture_vscode] Screenshot saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
