#!/usr/bin/env python3
"""
Voice-to-Text Tool (Docked Sidebar)
====================================
Opens the web UI in a tall sidebar window snapped to the right edge.
"""

import sys
import time
import threading
import random
import urllib.request
import ctypes
import webview

import voice_to_text_web as web

if sys.platform == "win32":
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    sys.stdout.reconfigure(encoding="utf-8")


def hide_console():
    if sys.platform == "win32":
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)


def show_console():
    if sys.platform == "win32":
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 1)


def is_server_running():
    try:
        urllib.request.urlopen(
            f"http://{web.HOST}:{web.PORT}/api/status", timeout=1
        )
        return True
    except Exception:
        return False


def get_scale():
    hdc = ctypes.windll.user32.GetDC(0)
    dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    return dpi / 96.0


def start_flask():
    web.app.run(host=web.HOST, port=web.PORT, threaded=True, debug=False)


def on_closing():
    print("[Shutting down...]")
    web.shutdown_event.set()


def main():
    hide_console()
    if not is_server_running():
        web.init_server()
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        time.sleep(1.5)
    else:
        print("[Docked] Backend already running — connecting to existing server.")

    scale = get_scale()
    screen_w = int(ctypes.windll.user32.GetSystemMetrics(0) / scale)
    screen_h = int(ctypes.windll.user32.GetSystemMetrics(1) / scale)

    # Subtract taskbar height (~48 logical pixels on 200% DPI)
    # pywebview screens reports 1002 work-area height vs 1050 full height
    taskbar_h = 48
    dock_h = screen_h - taskbar_h

    bust = random.randint(1000, 9999)
    url = f"http://{web.HOST}:{web.PORT}?_={bust}"

    window = webview.create_window(
        title="OrbitScribe - Docked",
        url=url,
        width=380,
        height=dock_h,
        x=screen_w - 380,
        y=0,
        resizable=True,
        on_top=False,
        frameless=False,
    )

    window.events.closing += on_closing

    try:
        web.mode_callback = lambda mode: None
        web.close_callback = lambda: window.destroy()
    except AttributeError:
        pass

    print(f"[Docked] Opening: 380x{dock_h} @ x={screen_w - 380}, y=0")
    try:
        webview.start()
    except Exception as e:
        print(f"[Docked] Error: {e}")
    print("[Docked] Exited")


if __name__ == "__main__":
    main()
