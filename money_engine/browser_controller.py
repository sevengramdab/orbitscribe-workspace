"""
browser_controller.py
=====================
High-level browser automation with vision feedback.
Wraps ComputerController with browser-specific smarts:
- Window finding and focus management
- Screenshot-based state detection
- Coordinate mapping for common UI patterns
- Safe retry loops with exponential backoff
"""
from __future__ import annotations

import os
import time
import base64
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Callable
from dataclasses import dataclass

from simpleswarm.simpleswarm.computer_controller import ComputerController


@dataclass
class BrowserState:
    """Current state of the browser as detected by vision."""
    url: Optional[str] = None
    page_title: Optional[str] = None
    has_login_form: bool = False
    has_modal: bool = False
    has_error: bool = False
    loading: bool = False
    screenshot_path: Optional[str] = None
    raw_b64: Optional[str] = None


class BrowserController:
    """
    Browser automation with ComputerController backend.
    Handles Chrome window lifecycle, navigation, and interaction.
    """

    def __init__(self, screenshot_dir: Optional[str] = None):
        self.ctrl = ComputerController(screenshot_dir=screenshot_dir)
        self.chrome_path = self._find_chrome()
        self._window_rect: Optional[Tuple[int, int, int, int]] = None
        self._last_state = BrowserState()

    # ------------------------------------------------------------------
    # Chrome lifecycle
    # ------------------------------------------------------------------

    def _find_chrome(self) -> str:
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv("USERNAME", "Shadow")),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return "chrome"

    def open_chrome(self, url: Optional[str] = None, new_window: bool = False) -> dict:
        """Launch Chrome, optionally to a URL."""
        if new_window or not self._find_chrome_window():
            cmd = f'start "" "{self.chrome_path}"'
            if url:
                cmd += f' "{url}"'
            result = self.ctrl.shell(cmd)
            time.sleep(2.5)
            return result
        if url:
            return self.navigate(url)
        return {"success": True, "message": "Chrome already open"}

    def navigate(self, url: str) -> dict:
        """Navigate current Chrome tab to URL via address bar."""
        self.focus_chrome()
        self.ctrl.hotkey("ctrl", "l")
        time.sleep(0.2)
        self.ctrl.type_text(url, interval=0.01)
        time.sleep(0.1)
        self.ctrl.press("enter")
        time.sleep(1.5)
        return {"success": True, "url": url}

    def new_tab(self, url: Optional[str] = None) -> dict:
        """Open a new tab."""
        self.focus_chrome()
        self.ctrl.hotkey("ctrl", "t")
        time.sleep(0.5)
        if url:
            return self.navigate(url)
        return {"success": True}

    def close_tab(self) -> dict:
        """Close current tab."""
        self.focus_chrome()
        self.ctrl.hotkey("ctrl", "w")
        time.sleep(0.3)
        return {"success": True}

    # ------------------------------------------------------------------
    # Window management
    # ------------------------------------------------------------------

    def _find_chrome_window(self) -> Optional[object]:
        try:
            import pygetwindow as gw
            wins = gw.getAllWindows()
            candidates = []
            for w in wins:
                if w.title and "google chrome" in w.title.lower():
                    candidates.append(w)
            if not candidates:
                return None
            candidates.sort(key=lambda w: w.width * w.height, reverse=True)
            return candidates[0]
        except Exception:
            return None

    def focus_chrome(self) -> dict:
        """Bring Chrome to foreground."""
        win = self._find_chrome_window()
        if win:
            try:
                if hasattr(win, "activate"):
                    win.activate()
                elif hasattr(win, "restore"):
                    win.restore()
                time.sleep(0.4)
                self._window_rect = (win.left, win.top, win.width, win.height)
                return {"success": True, "rect": self._window_rect}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Chrome window not found"}

    def get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        win = self._find_chrome_window()
        if win:
            self._window_rect = (win.left, win.top, win.width, win.height)
        return self._window_rect

    # ------------------------------------------------------------------
    # Coordinate helpers (percentage-based inside Chrome window)
    # ------------------------------------------------------------------

    def win_click(self, x_pct: float, y_pct: float, clicks: int = 1) -> dict:
        """Click inside Chrome window at percentage coordinates."""
        rect = self.get_window_rect()
        if not rect:
            return {"success": False, "error": "No Chrome window"}
        left, top, w, h = rect
        x = left + int(w * x_pct)
        y = top + int(h * y_pct)
        return self.ctrl.click(x, y, clicks=clicks)

    def win_type(self, text: str, interval: float = 0.01) -> dict:
        """Type text with Chrome focused."""
        self.focus_chrome()
        return self.ctrl.type_text(text, interval=interval)

    def win_scroll(self, clicks: int, x_pct: float = 0.5, y_pct: float = 0.5) -> dict:
        """Scroll inside Chrome window."""
        rect = self.get_window_rect()
        if not rect:
            return {"success": False, "error": "No Chrome window"}
        left, top, w, h = rect
        x = left + int(w * x_pct)
        y = top + int(h * y_pct)
        return self.ctrl.scroll(clicks, x, y)

    # ------------------------------------------------------------------
    # Screenshot & vision
    # ------------------------------------------------------------------

    def screenshot(self, filename: Optional[str] = None) -> BrowserState:
        """Capture full-screen screenshot and update state."""
        res = self.ctrl.screenshot(save=True, filename=filename)
        state = BrowserState()
        if res.get("success"):
            state.screenshot_path = res.get("path")
            state.raw_b64 = res.get("image_base64")
            # Basic vision heuristics on screenshot
            state = self._heuristic_vision(state, res.get("image"))
        self._last_state = state
        return state

    def screenshot_region(self, x_pct: float, y_pct: float, w_pct: float, h_pct: float, filename: Optional[str] = None) -> dict:
        """Screenshot a region of the Chrome window."""
        rect = self.get_window_rect()
        if not rect:
            return {"success": False, "error": "No Chrome window"}
        left, top, w, h = rect
        x = left + int(w * x_pct)
        y = top + int(h * y_pct)
        rw = int(w * w_pct)
        rh = int(h * h_pct)
        try:
            import pyautogui
            img = pyautogui.screenshot(region=(x, y, rw, rh))
            fname = filename or f"region_{int(time.time())}.png"
            path = Path(self.ctrl.screenshot_dir) / fname
            img.save(path)
            buf = __import__("io").BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return {"success": True, "path": str(path), "image_base64": b64, "width": rw, "height": rh}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _heuristic_vision(self, state: BrowserState, img) -> BrowserState:
        """Simple heuristic analysis of screenshot image."""
        if img is None:
            return state
        # Detect loading spinner / blank page by average brightness
        try:
            import numpy as np
            arr = np.array(img)
            gray = np.mean(arr[:, :, :3]) if len(arr.shape) == 3 else np.mean(arr)
            state.loading = gray > 245  # Mostly white = likely loading/blank
        except Exception:
            pass
        return state

    # ------------------------------------------------------------------
    # Common UI patterns
    # ------------------------------------------------------------------

    def click_text_field(self, x_pct: float, y_pct: float, clear: bool = True) -> dict:
        """Click a text field and optionally select-all then delete."""
        res = self.win_click(x_pct, y_pct)
        time.sleep(0.2)
        if clear and res.get("success"):
            self.ctrl.hotkey("ctrl", "a")
            time.sleep(0.1)
            self.ctrl.press("delete")
            time.sleep(0.1)
        return res

    def fill_form_field(self, x_pct: float, y_pct: float, text: str) -> dict:
        """Click, clear, and type into a form field."""
        self.click_text_field(x_pct, y_pct, clear=True)
        return self.win_type(text)

    def click_button_by_text(self, text: str, search_region: Optional[Tuple[float, float, float, float]] = None) -> dict:
        """
        Stub for text-based button finding.
        In full implementation, this uses OCR or vision model.
        For now, returns an error instructing manual coordinate use.
        """
        return {
            "success": False,
            "error": f"Text-based button finding not yet implemented for '{text}'. Use win_click(x_pct, y_pct) with known coordinates.",
        }

    def wait_for_load(self, timeout: int = 10) -> BrowserState:
        """Poll screenshot until page no longer looks like loading."""
        start = time.time()
        while time.time() - start < timeout:
            state = self.screenshot()
            if not state.loading:
                return state
            time.sleep(0.5)
        return self.screenshot()

    def safe_action(self, action: Callable, retries: int = 3, delay: float = 1.0):
        """Execute an action with retry loop."""
        last_error = None
        for i in range(retries):
            try:
                result = action()
                if isinstance(result, dict) and result.get("success"):
                    return result
                last_error = result.get("error") if isinstance(result, dict) else str(result)
            except Exception as e:
                last_error = str(e)
            time.sleep(delay * (i + 1))
        return {"success": False, "error": f"Failed after {retries} retries: {last_error}"}

    # ------------------------------------------------------------------
    # JavaScript injection via DevTools console
    # ------------------------------------------------------------------

    def open_console(self) -> dict:
        """Open Chrome DevTools console."""
        self.focus_chrome()
        self.ctrl.hotkey("ctrl", "shift", "j")
        time.sleep(1.0)
        return {"success": True}

    def run_js(self, js: str) -> dict:
        """Run JavaScript in Chrome console."""
        self.open_console()
        rect = self.get_window_rect()
        if not rect:
            return {"success": False, "error": "No Chrome window"}
        left, top, w, h = rect
        # Click console input (bottom area)
        input_x = left + int(w * 0.72)
        input_y = top + h - 60
        self.ctrl.click(input_x, input_y)
        time.sleep(0.2)
        self.ctrl.type_text(js, interval=0.01)
        time.sleep(0.1)
        self.ctrl.press("enter")
        time.sleep(0.3)
        return {"success": True, "js": js}

    # ------------------------------------------------------------------
    # HTTP helpers (for API-based money platforms)
    # ------------------------------------------------------------------

    def api_get(self, url: str, headers: Optional[Dict] = None, timeout: int = 15) -> dict:
        return self.ctrl.http_get(url, timeout=timeout)

    def api_post(self, url: str, json_data: dict, timeout: int = 15) -> dict:
        return self.ctrl.http_post(url, json_data, timeout=timeout)
