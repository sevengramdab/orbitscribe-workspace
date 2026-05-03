#!/usr/bin/env python3
"""
Voice-to-Text Tool (Floating Window)
====================================
Launches a small floating window using pywebview.
"""

import sys
import time
import threading
import random
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


def get_scale():
    hdc = ctypes.windll.user32.GetDC(0)
    dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    return dpi / 96.0


def apply_mode(mode):
    """Resize/reposition using pywebview's native methods (logical pixels)."""
    scale = get_scale()
    screen_w = int(ctypes.windll.user32.GetSystemMetrics(0) / scale)
    screen_h = int(ctypes.windll.user32.GetSystemMetrics(1) / scale)
    dock_h = screen_h - 48  # taskbar offset

    if mode == "float":
        window.resize(380, 740)
        window.move((screen_w - 380) // 2, (screen_h - 740) // 2)
        window.on_top = True
    elif mode == "docked_left":
        window.resize(380, dock_h)
        window.move(0, 0)
        window.on_top = True
    elif mode == "docked_right":
        window.resize(380, dock_h)
        window.move(screen_w - 380, 0)
        window.on_top = True
    elif mode == "fullscreen":
        window.resize(screen_w, screen_h)
        window.move(0, 0)
        window.on_top = False
    else:
        print(f"[Mode] Unknown mode: {mode}")
        return
    print(f"[Mode] Switched to {mode}")


def start_flask():
    web.app.run(host=web.HOST, port=web.PORT, threaded=True, debug=False)


def on_closing():
    print("[Shutting down...]")
    web.shutdown_event.set()


def main():
    global window

    hide_console()
    web.init_server()

    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    time.sleep(1.5)

    bust = random.randint(1000, 9999)
    url = f"http://{web.HOST}:{web.PORT}?float=1&_={bust}"

    window = webview.create_window(
        title="OrbitScribe",
        url=url,
        width=380,
        height=740,
        x=100,
        y=100,
        resizable=True,
        on_top=True,
        frameless=False,
    )

    window.events.closing += on_closing

    try:
        web.mode_callback = apply_mode
        web.close_callback = lambda: window.destroy()
    except AttributeError:
        print("[Float] Warning: backend module is stale — buttons may not work.")

    print("[Float] Window opened. Close it to exit.")
    try:
        webview.start()
    except Exception as e:
        print(f"[Float] Error: {e}")
    print("[Float] Exited")


if __name__ == "__main__":
    main()
