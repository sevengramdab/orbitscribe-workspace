#!/usr/bin/env python3
"""
Reload VS Code: with auto-resume context.

The OrbitScribe extension now automatically detects reloads and spawns the
auto-resume watcher. This script only needs to save the context and trigger
the reload.

Usage:
    python reload_with_resume.py "Your continuation context here"
    python reload_with_resume.py --full-reload "Your context here"

Example:
    python reload_with_resume.py "Continue working on the Command Deck UI."
"""
import sys
import os
import subprocess
import time
import argparse

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)


def main():
    parser = argparse.ArgumentParser(description="Reload VS Code: with auto-resume context")
    parser.add_argument("context", nargs="?", default="Continue from where we left off.", help="Context message to send")
    parser.add_argument("--full-reload", action="store_true", help="Do a full window reload instead of Extension Host restart")
    args = parser.parse_args()

    context = args.context

    # 1. Save context (extension will read this on reload)
    print("[reload_with_resume] Saving context...")
    subprocess.run([
        sys.executable,
        os.path.join(TOOLS_DIR, 'save_context.py'),
        context
    ], check=True)

    # 1b. Clear any stale locks so reload isn't blocked by a previous crash
    for lock_name in ('.reload-resume-lock', '.recovery-in-progress'):
        lock_path = os.path.join(TOOLS_DIR, lock_name)
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
                print(f"[reload_with_resume] Cleared stale lock: {lock_name}")
            except Exception:
                pass

    # 2. Trigger VS Code: reload via command palette
    reload_cmd = "Developer: Reload Window" if args.full_reload else "Developer: Restart Extension Host"
    print(f"[reload_with_resume] Triggering VS Code: {reload_cmd}...")
    time.sleep(0.5)

    try:
        import pygetwindow as gw
        import pyautogui

        win = None
        for w in gw.getAllWindows():
            if w.title and ('Visual Studio Code' in w.title or 'Cursor' in w.title):
                win = w
                break

        if win:
            win.activate()
            time.sleep(0.3)
            pyautogui.keyDown('ctrl')
            pyautogui.keyDown('shift')
            pyautogui.keyDown('p')
            pyautogui.keyUp('p')
            pyautogui.keyUp('shift')
            pyautogui.keyUp('ctrl')
            time.sleep(0.8)
            pyautogui.typewrite(reload_cmd, interval=0.01)
            time.sleep(0.5)
            pyautogui.keyDown('return')
            pyautogui.keyUp('return')
            print(f"[reload_with_resume] {reload_cmd} sent!")
        else:
            print("[reload_with_resume] VS Code: window not found. Reload manually.")
    except Exception as e:
        print(f"[reload_with_resume] Could not send reload keys: {e}")
        print(f"[reload_with_resume] Please reload VS Code: manually (Ctrl+ShiftP -> {reload_cmd})")

    print(f"[reload_with_resume] Extension will auto-resume after reload.")
    print(f"[reload_with_resume] Logs: {os.path.join(ROOT_DIR, 'auto_resume_watcher.log')}")


if __name__ == '__main__':
    main()
