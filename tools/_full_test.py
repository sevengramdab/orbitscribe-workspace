#!/usr/bin/env python3
"""Comprehensive test of the auto-resume system (no reload, no clicks)."""
import sys
import os
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TESTS_PASSED = 0
TESTS_FAILED = 0


def ok(name):
    global TESTS_PASSED
    TESTS_PASSED += 1
    print(f"  [PASS] {name}")


def fail(name, msg):
    global TESTS_FAILED
    TESTS_FAILED += 1
    print(f"  [FAIL] {name}: {msg}")


def test_imports():
    print("\n[TEST] Imports")
    try:
        import pygetwindow as gw
        ok("pygetwindow")
    except Exception as e:
        fail("pygetwindow", str(e))

    try:
        import pyautogui
        ok("pyautogui")
    except Exception as e:
        fail("pyautogui", str(e))


def test_backend_health():
    print("\n[TEST] Backend Health")
    try:
        req = urllib.request.Request("http://127.0.0.1:58081/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read().decode('utf-8')
            if resp.status == 200:
                ok(f"backend health ({data})")
            else:
                fail("backend health", f"status {resp.status}")
    except Exception as e:
        fail("backend health", str(e))


def test_vscode_window():
    print("\n[TEST] VS Code: Window Detection")
    try:
        import pygetwindow as gw
        wins = [w for w in gw.getAllWindows() if w.title and ('Visual Studio Code' in w.title or 'Cursor' in w.title)]
        if wins:
            for w in wins:
                ok(f"window '{w.title}' ({w.width}x{w.height})")
        else:
            fail("vscode window", "no window found")
    except Exception as e:
        fail("vscode window", str(e))


def test_coordinate_computation():
    print("\n[TEST] Coordinate Computation")
    try:
        import pygetwindow as gw
        from auto_resume_kimi import compute_coordinates, find_vscode_window
        win = find_vscode_window(gw)
        if not win:
            fail("coordinates", "no vscode window")
            return
        coords = compute_coordinates(win)
        for name, (x, y) in coords.items():
            abs_x = win.left + x
            abs_y = win.top + y
            if 0 <= x <= win.width and 0 <= y <= win.height:
                ok(f"{name} relative=({x},{y}) absolute=({abs_x},{abs_y})")
            else:
                fail(f"{name}", f"out of bounds relative=({x},{y})")
    except Exception as e:
        fail("coordinates", str(e))


def test_screenshot():
    print("\n[TEST] Screenshot Capture")
    try:
        import pygetwindow as gw
        from auto_resume_kimi import take_screenshot, find_vscode_window
        import pyautogui
        win = find_vscode_window(gw)
        if not win:
            fail("screenshot", "no vscode window")
            return
        path = take_screenshot(pyautogui, win, "test_screenshot")
        if path and os.path.exists(path):
            ok(f"screenshot saved to {path}")
        else:
            fail("screenshot", "file not created")
    except Exception as e:
        fail("screenshot", str(e))


def test_context_file():
    print("\n[TEST] Context File")
    ctx_file = os.path.join(os.path.dirname(__file__), '.reload-context.txt')
    if os.path.exists(ctx_file):
        with open(ctx_file, 'r', encoding='utf-8') as f:
            content = f.read()
        ok(f"context file exists ({len(content)} chars)")
    else:
        fail("context file", "not found")


def test_file_syntax():
    print("\n[TEST] File Syntax")
    files = [
        'auto_resume_kimi.py',
        'reload_with_resume.py',
        'save_context.py',
        'capture_vscode.py',
        'test_resume_setup.py',
    ]
    for fname in files:
        fpath = os.path.join(os.path.dirname(__file__), fname)
        if not os.path.exists(fpath):
            fail(fname, "file not found")
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                compile(f.read(), fpath, 'exec')
            ok(f"{fname} syntax")
        except SyntaxError as e:
            fail(fname, str(e))


def test_reload_lock():
    print("\n[TEST] Reload Lock")
    lock_file = os.path.join(os.path.dirname(__file__), '.reload-lock')
    if os.path.exists(lock_file):
        ok(f"reload lock exists")
    else:
        ok("reload lock not present (will be created on reload)")


def main():
    print("=" * 50)
    print("Auto-Resume System Comprehensive Test")
    print("=" * 50)

    test_imports()
    test_backend_health()
    test_vscode_window()
    test_coordinate_computation()
    test_screenshot()
    test_context_file()
    test_file_syntax()
    test_reload_lock()

    print("\n" + "=" * 50)
    print(f"Results: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 50)

    if TESTS_FAILED > 0:
        print("\nSome tests failed. Review the failures above.")
        sys.exit(1)
    else:
        print("\nAll tests passed! The auto-resume system should work correctly.")


if __name__ == '__main__':
    main()
