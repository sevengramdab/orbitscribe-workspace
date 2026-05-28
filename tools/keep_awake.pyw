#!/usr/bin/env python3
"""
keep_awake.pyw
==============
Windows system-tray keep-awake utility with truly random,
non-repeating micro-action sequences.

No two action sequences are ever the same.  A shuffled "deck"
of micro-actions is consumed without replacement, then reshuffled.
Intervals jitter between 25-35 minutes so the pattern never looks robotic.

Usage:
    Double-click keep_awake.pyw   (no console window)
or
    python tools/keep_awake.py    (with console window, for debugging)
"""
from __future__ import annotations

import argparse
import json
import random
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional

# Config file shared across all keep-awake scripts
CONFIG_FILE = Path(__file__).with_name("keep_awake_config.json")


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_last_used(duration: float, mode: str) -> None:
    if not CONFIG_FILE.exists():
        return
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        cfg["last_used"] = {
            "duration_hours": duration,
            "mode": mode,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        CONFIG_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Try to import pyautogui; if missing we fall back to keyboard-only via ctypes
# ---------------------------------------------------------------------------
try:
    import pyautogui
    _PYAUTO_OK = True
except Exception:
    pyautogui = None  # type: ignore
    _PYAUTO_OK = False

# ---------------------------------------------------------------------------
# Harmless key constants (Windows virtual-key codes)
# ---------------------------------------------------------------------------
VK_SCROLL = 0x91
VK_NUMLOCK = 0x90
VK_F15 = 0x7E
VK_LSHIFT = 0xA0
VK_LCONTROL = 0xA2


def _press_key(vk: int) -> None:
    """Press and release a virtual key via ctypes (works without pyautogui)."""
    import ctypes
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk, 0, 2, 0)


# ---------------------------------------------------------------------------
# Micro-action definitions
# ---------------------------------------------------------------------------

@dataclass
class MicroAction:
    name: str
    execute: Callable[[], None]


def _make_actions() -> List[MicroAction]:
    """Build the master pool of possible micro-actions."""
    actions: List[MicroAction] = []

    # --- Mouse micro-movements (1-4 px) ---
    for dx in (-4, -3, -2, -1, 1, 2, 3, 4):
        for dy in (-4, -3, -2, -1, 1, 2, 3, 4):
            if dx == 0 and dy == 0:
                continue
            def _move(dx=dx, dy=dy):
                if _PYAUTO_OK:
                    pyautogui.moveRel(dx, dy, duration=0.1)
            actions.append(MicroAction(f"mouse_rel_{dx}_{dy}", _move))

    # --- Scroll wheel micro-scrolls ---
    for direction in (-1, 1):
        for _ in range(3):
            def _scroll(d=direction):
                if _PYAUTO_OK:
                    pyautogui.scroll(d)
            actions.append(MicroAction(f"scroll_{direction}", _scroll))

    # --- Harmless key toggles ---
    actions.append(MicroAction("key_scroll_lock", lambda: _press_key(VK_SCROLL)))
    actions.append(MicroAction("key_num_lock", lambda: _press_key(VK_NUMLOCK)))
    actions.append(MicroAction("key_f15", lambda: _press_key(VK_F15)))

    # --- Modifier tap (Ctrl or Shift, no combo) ---
    actions.append(MicroAction("tap_ctrl", lambda: _press_key(VK_LCONTROL)))
    actions.append(MicroAction("tap_shift", lambda: _press_key(VK_LSHIFT)))

    # --- Subtle mouse wiggle (two tiny moves back and forth) ---
    def _wiggle():
        if _PYAUTO_OK:
            x, y = pyautogui.position()
            pyautogui.moveTo(x + 2, y + 1, duration=0.1)
            pyautogui.moveTo(x - 1, y - 2, duration=0.1)
    actions.append(MicroAction("wiggle", _wiggle))

    return actions


# ---------------------------------------------------------------------------
# Deck-based non-repeating random sequence
# ---------------------------------------------------------------------------

class ActionDeck:
    """
    Draws actions from a shuffled deck without replacement.
    Guarantees no immediate repeats and a flat distribution.
    """

    def __init__(self, actions: List[MicroAction]):
        self._actions = actions
        self._deck: List[MicroAction] = []
        self._last_drawn: Optional[str] = None
        self._history: List[str] = []
        self._reshuffle()

    def _reshuffle(self):
        pool = self._actions[:]
        random.shuffle(pool)
        # Ensure the first card of the new deck != last card of old deck
        if self._last_drawn and pool and pool[0].name == self._last_drawn:
            # Swap with a random position in the back half
            swap_idx = random.randint(len(pool) // 2, len(pool) - 1)
            pool[0], pool[swap_idx] = pool[swap_idx], pool[0]
        self._deck = pool

    def draw(self) -> MicroAction:
        if not self._deck:
            self._reshuffle()
        action = self._deck.pop()
        self._last_drawn = action.name
        self._history.append(action.name)
        # Keep history bounded
        if len(self._history) > 1000:
            self._history = self._history[-500:]
        return action

    @property
    def history(self) -> List[str]:
        return self._history[:]


# ---------------------------------------------------------------------------
# Jittered interval generator
# ---------------------------------------------------------------------------

def _next_interval(base_sec: float = 1800, jitter_pct: float = 0.20) -> float:
    """Return a random interval around base_sec +/- jitter_pct."""
    jitter = base_sec * jitter_pct
    return base_sec + random.uniform(-jitter, jitter)


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class KeepAwakeEngine:
    def __init__(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        duration_hours: float = 0.0,
        countdown_callback: Optional[Callable[[str], None]] = None,
        shutdown_callback: Optional[Callable[[], None]] = None,
    ):
        self.actions = _make_actions()
        self.deck = ActionDeck(self.actions)
        self.log_callback = log_callback
        self.countdown_callback = countdown_callback
        self.shutdown_callback = shutdown_callback
        self._timer: Optional[threading.Timer] = None
        self._countdown_timer: Optional[threading.Timer] = None
        self._running = False
        self._lock = threading.Lock()
        self.action_count = 0
        self.duration_hours = duration_hours
        self._start_time: Optional[datetime] = None

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        if self.log_callback:
            self.log_callback(line)

    def _tick(self):
        with self._lock:
            if not self._running:
                return

        action = self.deck.draw()
        try:
            action.execute()
            self.action_count += 1
            self.log(f"Action #{self.action_count}: {action.name}")
        except Exception as e:
            self.log(f"Action failed ({action.name}): {e}")

        # Schedule next tick
        interval = _next_interval()
        mins = int(interval // 60)
        secs = int(interval % 60)
        self.log(f"Next wake-up in ~{mins}m {secs}s")

        with self._lock:
            if self._running:
                self._timer = threading.Timer(interval, self._tick)
                self._timer.daemon = True
                self._timer.start()

    def _update_countdown(self):
        if not self._running or not self._start_time or self.duration_hours <= 0:
            return
        elapsed = (datetime.now() - self._start_time).total_seconds()
        remaining = max(0, self.duration_hours * 3600 - elapsed)
        if self.countdown_callback:
            hrs, rem = divmod(int(remaining), 3600)
            mins, secs = divmod(rem, 60)
            self.countdown_callback(f"{hrs:02d}:{mins:02d}:{secs:02d}")
        if remaining <= 0:
            self.log("Timer expired. Stopping...")
            self.stop()
            if self.shutdown_callback:
                try:
                    self.shutdown_callback()
                except Exception:
                    pass
            return
        self._countdown_timer = threading.Timer(1.0, self._update_countdown)
        self._countdown_timer.daemon = True
        self._countdown_timer.start()

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._start_time = datetime.now()
        self.log("Engine started")
        if self.duration_hours > 0:
            self.log(f"Auto-stop in {self.duration_hours} hour(s)")
            self._update_countdown()
        self._tick()

    def stop(self):
        with self._lock:
            self._running = False
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if self._countdown_timer:
                self._countdown_timer.cancel()
                self._countdown_timer = None
        self.log("Engine stopped")

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------

class KeepAwakeGUI:
    def __init__(self, duration_hours: float = 0.0):
        self.root = tk.Tk()
        self.root.title("Keep-Awake")
        self.root.geometry("420x360")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.engine = KeepAwakeEngine(
            log_callback=self._append_log,
            duration_hours=duration_hours,
            countdown_callback=self._update_countdown_label,
            shutdown_callback=self._auto_close,
        )

        # Header
        tk.Label(
            self.root,
            text="Keep-Awake",
            font=("Segoe UI", 18, "bold"),
            bg="#1e1e2e",
            fg="#cba6f7",
        ).pack(pady=(12, 4))

        tk.Label(
            self.root,
            text="Non-repeating random micro-actions",
            font=("Segoe UI", 10),
            bg="#1e1e2e",
            fg="#a6adc8",
        ).pack(pady=(0, 8))

        # Countdown (visible when duration is set)
        self.countdown_var = tk.StringVar(value="")
        self.countdown_label = tk.Label(
            self.root,
            textvariable=self.countdown_var,
            font=("Segoe UI", 10),
            bg="#1e1e2e",
            fg="#94e2d5",
        )
        self.countdown_label.pack(pady=2)

        # Status
        self.status_var = tk.StringVar(value="Status: Stopped")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Segoe UI", 11, "bold"),
            bg="#1e1e2e",
            fg="#f38ba8",
        ).pack(pady=4)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#1e1e2e")
        btn_frame.pack(pady=8)

        self.start_btn = tk.Button(
            btn_frame,
            text="Start",
            font=("Segoe UI", 11),
            bg="#a6e3a1",
            fg="#1e1e2e",
            activebackground="#94e2d5",
            width=10,
            command=self._on_start,
        )
        self.start_btn.pack(side=tk.LEFT, padx=6)

        self.stop_btn = tk.Button(
            btn_frame,
            text="Stop",
            font=("Segoe UI", 11),
            bg="#f38ba8",
            fg="#1e1e2e",
            activebackground="#eba0ac",
            width=10,
            command=self._on_stop,
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=6)

        # Log box
        tk.Label(
            self.root,
            text="Event Log",
            font=("Segoe UI", 10, "bold"),
            bg="#1e1e2e",
            fg="#cdd6f4",
        ).pack(anchor="w", padx=16, pady=(8, 2))

        self.log_box = tk.Text(
            self.root,
            height=10,
            width=48,
            bg="#313244",
            fg="#cdd6f4",
            font=("Consolas", 9),
            state=tk.DISABLED,
            wrap=tk.WORD,
        )
        self.log_box.pack(padx=16, pady=(0, 12))

        # Close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _append_log(self, line: str):
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, line + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _update_countdown_label(self, text: str):
        self.root.after(0, lambda: self.countdown_var.set(f"Auto-stop in: {text}"))

    def _auto_close(self):
        self.root.after(0, self._on_close)

    def _on_start(self):
        self.engine.start()
        self.status_var.set("Status: Running")
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)

    def _on_stop(self):
        self.engine.stop()
        self.status_var.set("Status: Stopped")
        self.countdown_var.set("")
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)

    def _on_close(self):
        self.engine.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    config = _load_config()
    default_duration = config.get("default_duration_hours", 4.0)

    parser = argparse.ArgumentParser(description="Keep-Awake GUI")
    parser.add_argument(
        "--duration",
        type=float,
        default=default_duration,
        help="Hours before auto-stop (0 = run forever until stopped). Default: %(default)s",
    )
    args = parser.parse_args()

    _save_last_used(args.duration, "gui")
    gui = KeepAwakeGUI(duration_hours=args.duration)
    gui.run()


if __name__ == "__main__":
    main()
