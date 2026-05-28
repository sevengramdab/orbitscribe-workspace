#!/usr/bin/env python3
"""
keep_awake_scheduler.py
=======================
Manage Windows Scheduled Tasks for keep-awake using schtasks.exe.

Subcommands:
    create-task --duration N --daily [--at HH:MM] [--mode headless|gui]
    remove-task [--name TASK_NAME]
    list-tasks

Examples:
    python tools/keep_awake_scheduler.py create-task --duration 8 --daily
    python tools/keep_awake_scheduler.py create-task --duration 4 --boot --mode gui
    python tools/keep_awake_scheduler.py remove-task
    python tools/keep_awake_scheduler.py list-tasks
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TASK_NAME = "OrbitScribe-KeepAwake"
CONFIG_PATH = Path(__file__).with_name("keep_awake_config.json")


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"[scheduler] Warning: could not save config: {e}", file=sys.stderr)


def _run_schtasks(*args: str) -> subprocess.CompletedProcess:
    cmd = ["schtasks.exe"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, shell=False)


def _get_pythonw() -> str:
    """Return pythonw.exe path (no console window) derived from sys.executable."""
    exe = sys.executable
    lower = exe.lower()
    if lower.endswith("python.exe"):
        return exe[:-10] + "pythonw.exe"
    if lower.endswith("python3.exe"):
        return exe[:-11] + "pythonw3.exe"
    return exe


def _build_command(duration: float, mode: str) -> str:
    script = "keep_awake_headless.py" if mode == "headless" else "keep_awake.pyw"
    script_path = Path(__file__).parent / script
    python_exe = _get_pythonw()
    return f'"{python_exe}" "{script_path}" --duration {duration}'


def cmd_create_task(args: argparse.Namespace) -> int:
    config = _load_config()
    duration = args.duration
    mode = args.mode or config.get("preferred_mode", "headless")
    schedule_type = "onlogon" if args.boot else "daily"
    start_time = args.at or "09:00"
    task_name = args.name or TASK_NAME

    trigger_args = ["/sc", schedule_type]
    if schedule_type == "daily":
        trigger_args += ["/st", start_time]

    command = _build_command(duration, mode)

    create_cmd = [
        "/create",
        "/tn", task_name,
        "/tr", command,
        *trigger_args,
        "/f",
    ]

    result = _run_schtasks(*create_cmd)

    if result.returncode != 0:
        print(f"[scheduler] Failed to create task:\n{result.stderr}")
        return 1

    print(f"[scheduler] Created task '{task_name}'")
    print(f"  Schedule: {schedule_type}")
    if schedule_type == "daily":
        print(f"  Start at: {start_time}")
    print(f"  Mode:     {mode}")
    print(f"  Duration: {duration} hour(s)")
    print(f"  Command:  {command}")

    config["default_duration_hours"] = duration
    config["preferred_mode"] = mode
    config["auto_start_on_boot"] = args.boot
    config["last_used"] = {
        "duration_hours": duration,
        "mode": mode,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    _save_config(config)
    return 0


def cmd_remove_task(args: argparse.Namespace) -> int:
    task_name = args.name or TASK_NAME
    result = _run_schtasks("/delete", "/tn", task_name, "/f")
    if result.returncode != 0:
        err = result.stderr.lower()
        if "not exist" in err or "cannot find" in err:
            print(f"[scheduler] Task '{task_name}' does not exist.")
            return 0
        print(f"[scheduler] Failed to remove task:\n{result.stderr}")
        return 1
    print(f"[scheduler] Removed task '{task_name}'")
    return 0


def cmd_list_tasks(args: argparse.Namespace) -> int:
    result = _run_schtasks("/query", "/fo", "CSV", "/v")
    if result.returncode != 0:
        print(f"[scheduler] Failed to query tasks:\n{result.stderr}")
        return 1

    lines = result.stdout.splitlines()
    if not lines:
        print("[scheduler] No scheduled tasks found.")
        return 0

    reader = csv.DictReader(lines)
    matched = []
    for row in reader:
        task_name = row.get("TaskName", "").strip()
        task_run = row.get("Task To Run", "").strip()
        if (
            "keepawake" in task_name.lower()
            or "orbitscribe" in task_name.lower()
            or "keep-awake" in task_run.lower()
        ):
            matched.append(row)

    if not matched:
        print("[scheduler] No keep-awake related tasks found.")
        return 0

    print(f"[scheduler] Found {len(matched)} keep-awake related task(s):\n")
    for row in matched:
        print(f"Name:      {row.get('TaskName', 'N/A')}")
        print(f"Status:    {row.get('Status', 'N/A')}")
        print(f"Next Run:  {row.get('Next Run Time', 'N/A')}")
        print(f"Schedule:  {row.get('Schedule Type', 'N/A')}")
        print(f"Task Run:  {row.get('Task To Run', 'N/A')}")
        print("-" * 50)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Keep-Awake Windows Scheduled Task Manager"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create_parser = sub.add_parser("create-task", help="Create a scheduled keep-awake task")
    create_parser.add_argument("--duration", type=float, required=True, help="Hours to keep awake")
    create_parser.add_argument("--daily", action="store_true", help="Run daily (default)")
    create_parser.add_argument("--boot", action="store_true", help="Run on user logon")
    create_parser.add_argument("--at", type=str, default="09:00", help="Start time for daily tasks (HH:MM). Default: 09:00")
    create_parser.add_argument("--mode", choices=["headless", "gui"], default=None, help="Mode: headless or gui")
    create_parser.add_argument("--name", type=str, default=None, help="Custom task name")
    create_parser.set_defaults(func=cmd_create_task)

    remove_parser = sub.add_parser("remove-task", help="Remove the scheduled keep-awake task")
    remove_parser.add_argument("--name", type=str, default=None, help="Custom task name")
    remove_parser.set_defaults(func=cmd_remove_task)

    list_parser = sub.add_parser("list-tasks", help="List keep-awake related scheduled tasks")
    list_parser.set_defaults(func=cmd_list_tasks)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
