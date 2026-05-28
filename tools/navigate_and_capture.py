#!/usr/bin/env python3
"""
navigate_and_capture.py
=======================
Simple Chrome navigation + screenshot capture using direct pyautogui + mss.
Much lighter than BrowserController wrapper.
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import pyautogui
import pygetwindow as gw

try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

SCREENSHOT_DIR = Path("screenshots/extraction")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def find_chrome_window():
    wins = [w for w in gw.getAllWindows() if w.title and "google chrome" in w.title.lower()]
    if not wins:
        return None
    wins.sort(key=lambda w: w.width * w.height, reverse=True)
    return wins[0]


def focus_chrome():
    win = find_chrome_window()
    if not win:
        print("[ERROR] Chrome not found. Open Chrome first.")
        return None
    try:
        if hasattr(win, "activate"):
            win.activate()
        elif hasattr(win, "restore"):
            win.restore()
        time.sleep(0.5)
        return win
    except Exception as e:
        print(f"[ERROR] Could not focus Chrome: {e}")
        return None


def screenshot(name: str):
    path = SCREENSHOT_DIR / name
    if HAS_MSS:
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            img = sct.grab(monitor)
            mss.tools.to_png(img.rgb, img.size, output=str(path))
    else:
        img = pyautogui.screenshot()
        img.save(path)
    print(f"[screenshot] Saved: {path}")
    return path


def navigate(url: str):
    print(f"[navigate] Going to: {url}")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('l')
    pyautogui.keyUp('l')
    pyautogui.keyUp('ctrl')
    time.sleep(0.3)
    pyautogui.typewrite(url, interval=0.01)
    time.sleep(0.2)
    pyautogui.press('enter')
    time.sleep(4)


def click_at(x, y):
    pyautogui.click(x, y)
    time.sleep(0.5)


def run():
    print("=" * 60)
    print("NAVIGATE & CAPTURE")
    print("=" * 60)

    win = focus_chrome()
    if not win:
        sys.exit(1)

    print(f"[OK] Chrome focused: {win.title} ({win.width}x{win.height})")

    # --- Medium ---
    print("\n--- MEDIUM ---")
    navigate("https://medium.com/me/settings/security")
    screenshot("medium_security.png")
    # Scroll down in case token is lower
    pyautogui.scroll(-5, win.left + win.width // 2, win.top + win.height // 2)
    time.sleep(1)
    screenshot("medium_security_scrolled.png")

    # --- Substack ---
    print("\n--- SUBSTACK ---")
    navigate("https://substack.com/settings")
    screenshot("substack_settings.png")

    # --- ClickBank ---
    print("\n--- CLICKBANK ---")
    navigate("https://accounts.clickbank.com")
    screenshot("clickbank_accounts.png")

    print("\n" + "=" * 60)
    print("DONE. Screenshots saved to screenshots/extraction/")
    print("=" * 60)


if __name__ == "__main__":
    run()
