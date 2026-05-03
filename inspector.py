#!/usr/bin/env python3
"""
Voice-to-Text Window Inspector
==============================
Diagnostic tool that tests window creation, positioning, DPI scaling,
and Flask endpoints so we can see exactly what's failing.
"""

import sys
import time
import threading
import random
import ctypes
import urllib.request
import json

# Fix Windows console encoding
if sys.platform == "win32":
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    sys.stdout.reconfigure(encoding="utf-8")
    ctypes.windll.user32.SetProcessDPIAware()

print("=" * 60)
print("  VOICE-TO-TEXT WINDOW INSPECTOR")
print("=" * 60)
print()

# ------------------------------------------------------------------
# 1. System / DPI Info
# ------------------------------------------------------------------
print("[1] System Info")
print("-" * 40)

screen_w = ctypes.windll.user32.GetSystemMetrics(0)
screen_h = ctypes.windll.user32.GetSystemMetrics(1)
print(f"  Screen (GetSystemMetrics): {screen_w} x {screen_h}")

# Try to get DPI
try:
    hdc = ctypes.windll.user32.GetDC(0)
    dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
    dpi_y = ctypes.windll.gdi32.GetDeviceCaps(hdc, 90)  # LOGPIXELSY
    ctypes.windll.user32.ReleaseDC(0, hdc)
    scale = dpi_x / 96.0
    print(f"  DPI: {dpi_x}x{dpi_y}  (scale: {scale:.2f}x)")
    print(f"  Logical screen: {int(screen_w/scale)} x {int(screen_h/scale)}")
except Exception as e:
    print(f"  Could not read DPI: {e}")

print()

# ------------------------------------------------------------------
# 2. Flask Backend Test
# ------------------------------------------------------------------
print("[2] Flask Backend Test")
print("-" * 40)

import voice_to_text_web as web

try:
    web.init_server()
    print("  [OK] init_server() completed")
except Exception as e:
    print(f"  [FAIL] init_server() error: {e}")
    sys.exit(1)

# Check callbacks exist
has_mode_cb = hasattr(web, 'mode_callback')
has_close_cb = hasattr(web, 'close_callback')
print(f"  mode_callback exists: {has_mode_cb}")
print(f"  close_callback exists: {has_close_cb}")

# Start Flask
def start_flask():
    web.app.run(host=web.HOST, port=web.PORT, threaded=True, debug=False)

flask_thread = threading.Thread(target=start_flask, daemon=True)
flask_thread.start()
time.sleep(2)

# Test endpoints
for endpoint, method, body in [
    ("/api/status", "GET", None),
    ("/api/settings", "GET", None),
    ("/api/mode", "POST", json.dumps({"mode": "float"}).encode()),
    ("/api/close", "POST", b""),
]:
    url = f"http://{web.HOST}:{web.PORT}{endpoint}"
    try:
        req = urllib.request.Request(url, method=method, data=body)
        if body:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=3) as resp:
            print(f"  [OK] {method} {endpoint} -> {resp.status}")
    except Exception as e:
        print(f"  [FAIL] {method} {endpoint} -> {e}")

print()

# ------------------------------------------------------------------
# 3. pywebview Window Test
# ------------------------------------------------------------------
print("[3] pywebview Window Test")
print("-" * 40)

try:
    import webview
    print("  [OK] pywebview imported")
except Exception as e:
    print(f"  [FAIL] pywebview import error: {e}")
    sys.exit(1)

bust = random.randint(1000, 9999)
url = f"http://{web.HOST}:{web.PORT}?float=1&_={bust}"

print(f"  Loading URL: {url}")

window = webview.create_window(
    title="Voice to Text",
    url=url,
    width=380,
    height=740,
    x=100,
    y=100,
    resizable=True,
    on_top=False,
    frameless=False,
)

print("  [OK] create_window() returned")

# Register callbacks
web.mode_callback = lambda mode: print(f"  [CB] mode_callback('{mode}') fired")
web.close_callback = lambda: print("  [CB] close_callback() fired")

# Watcher thread: log window handle every second
def watch_window():
    for i in range(15):
        time.sleep(1)
        hwnd = ctypes.windll.user32.FindWindowW(None, "Voice to Text")
        if hwnd:
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            print(f"  [T+{i+1}s] HWND={hwnd}  "
                  f"pos=({rect.left},{rect.top})  "
                  f"size=({rect.right-rect.left}x{rect.bottom-rect.top})")
            
            # Try SetWindowPos to dock-right at T=5
            if i == 4:
                print("  [ACTION] Sending SetWindowPos -> dock right")
                sw = ctypes.windll.user32.GetSystemMetrics(0)
                sh = ctypes.windll.user32.GetSystemMetrics(1)
                ctypes.windll.user32.SetWindowPos(
                    hwnd, -1, sw - 380, 0, 380, sh, 0x0040
                )
        else:
            print(f"  [T+{i+1}s] HWND not found yet")

threading.Thread(target=watch_window, daemon=True).start()

print("  Starting webview (close the window manually to end)...")
print()
print("=" * 60)
webview.start()
print("=" * 60)
print("  webview.start() returned — inspector finished")
