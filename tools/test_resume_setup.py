#!/usr/bin/env python3
"""
Diagnostic script to test the auto-resume setup.
Run this to verify everything is configured correctly.
"""
import sys
import os
import urllib.request

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

def test_dependencies():
    print("[test] Checking dependencies...")
    try:
        import pygetwindow as gw
        print("  pygetwindow: OK")
    except ImportError:
        print("  pygetwindow: MISSING (pip install pygetwindow)")
        return False
    try:
        import pyautogui
        print("  pyautogui: OK")
    except ImportError:
        print("  pyautogui: MISSING (pip install pyautogui)")
        return False
    return True


def test_backend():
    print("[test] Checking swarm backend...")
    try:
        req = urllib.request.Request("http://127.0.0.1:58081/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read().decode('utf-8')
            print(f"  Backend: OK ({data})")
            return True
    except Exception as e:
        print(f"  Backend: NOT REACHABLE ({e})")
        return False


def test_vscode_window():
    print("[test] Checking VS Code: window...")
    try:
        import pygetwindow as gw
        wins = [w for w in gw.getAllWindows() if w.title and ('Visual Studio Code' in w.title or 'Cursor' in w.title)]
        if wins:
            for w in wins:
                print(f"  Found: '{w.title}' ({w.width}x{w.height})")
            return True
        else:
            print("  No VS Code: window found. Open VS Code: first.")
            return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def test_context_file():
    print("[test] Checking context file...")
    ctx_file = os.path.join(TOOLS_DIR, '.reload-context.txt')
    if os.path.exists(ctx_file):
        with open(ctx_file, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"  Context file: EXISTS ({len(content)} chars)")
        return True
    else:
        print("  Context file: NOT FOUND (will be created on reload)")
        return True


def test_screenshot_dir():
    print("[test] Checking screenshot directory...")
    ss_dir = os.path.join(TOOLS_DIR, '..', 'screenshots')
    os.makedirs(ss_dir, exist_ok=True)
    print(f"  Screenshot dir: {ss_dir}")
    return True


def main():
    print("=" * 50)
    print("Auto-Resume Setup Diagnostic")
    print("=" * 50)
    results = []
    results.append(("Dependencies", test_dependencies()))
    results.append(("Backend", test_backend()))
    results.append(("VS Code: Window", test_vscode_window()))
    results.append(("Context File", test_context_file()))
    results.append(("Screenshot Dir", test_screenshot_dir()))

    print("=" * 50)
    print("Results:")
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {name}: {status}")
    print("=" * 50)

    if not all(r[1] for r in results):
        print("Some checks failed. Fix the issues above before using auto-resume.")
        sys.exit(1)
    else:
        print("All checks passed! Auto-resume should work.")


if __name__ == '__main__':
    main()
