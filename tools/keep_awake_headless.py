#!/usr/bin/env python3
"""
keep_awake_headless.py
======================
Prevents Windows from going to sleep without GUI or fake input.
Uses SetThreadExecutionState (SYSTEM_REQUIRED | CONTINUOUS).

Usage:
    python tools/keep_awake_headless.py --duration 4
    python tools/keep_awake_headless.py --duration 0   # run forever

Stop early:
    Ctrl+C or delete tools/.keep_awake_active
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# Config file shared across all keep-awake scripts
CONFIG_FILE = Path(__file__).with_name("keep_awake_config.json")
# PID file so other processes can find / kill us
PID_FILE = Path(__file__).with_suffix(".pid")
# Sentinel file — delete this to signal shutdown
SENTINEL_FILE = Path(__file__).parent / ".keep_awake_active"


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


def _write_pid():
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _clear_pid():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _create_sentinel():
    SENTINEL_FILE.write_text("active", encoding="utf-8")


def _sentinel_exists() -> bool:
    return SENTINEL_FILE.exists()


def _remove_sentinel():
    try:
        SENTINEL_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def keep_awake(duration_hours: float):
    # Tell Windows: this thread needs the system awake continuously
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )

    _write_pid()
    _create_sentinel()

    start = datetime.now()
    end_time = start + timedelta(hours=duration_hours) if duration_hours > 0 else None

    if end_time:
        eta = end_time.strftime("%H:%M:%S")
        print(f"[keep-awake] PC will NOT sleep until ~{eta} ({duration_hours}h).", flush=True)
    else:
        print("[keep-awake] PC will NOT sleep. Run forever mode.", flush=True)

    print("[keep-awake] Delete tools/.keep_awake_active or press Ctrl+C to stop.", flush=True)

    try:
        while True:
            time.sleep(10)
            if not _sentinel_exists():
                print("[keep-awake] Sentinel removed. Shutting down.", flush=True)
                break
            if end_time and datetime.now() >= end_time:
                print("[keep-awake] Timer expired. Shutting down.", flush=True)
                break
    except KeyboardInterrupt:
        print("[keep-awake] Interrupted by user.", flush=True)
    finally:
        # Reset to default (allow sleep again)
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        _clear_pid()
        _remove_sentinel()
        print("[keep-awake] Stopped. PC may sleep now.", flush=True)


def main():
    config = _load_config()
    default_duration = config.get("default_duration_hours", 4.0)

    parser = argparse.ArgumentParser(description="Keep Windows awake (headless)")
    parser.add_argument(
        "--duration",
        type=float,
        default=default_duration,
        help="Hours to keep awake (0 = forever). Default: %(default)s",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop a running keep-awake instance",
    )
    args = parser.parse_args()

    if args.stop:
        _remove_sentinel()
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text(encoding="utf-8"))
                os.kill(pid, 9)
                print(f"[keep-awake] Killed PID {pid}")
            except Exception as e:
                print(f"[keep-awake] Could not kill: {e}")
        else:
            print("[keep-awake] No PID file found. Already stopped?")
        return

    _save_last_used(args.duration, "headless")
    keep_awake(args.duration)


if __name__ == "__main__":
    main()
