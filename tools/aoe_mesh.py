#!/usr/bin/env python3
"""AOE Mesh CLI — controls the Rust AOE supervisor and local mesh node.

Usage:
    python tools/aoe_mesh.py start
    python tools/aoe_mesh.py stop
    python tools/aoe_mesh.py status
    python tools/aoe_mesh.py failsafe
    python tools/aoe_mesh.py logs
    python tools/aoe_mesh.py relay-config --peer 192.168.4.10
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

SUPERVISOR_PORT = int(os.environ.get("AOE_PORT", "58082"))
SUPERVISOR_URL = f"http://localhost:{SUPERVISOR_PORT}"
MAX_RETRIES = 3
RETRY_DELAY = 1.0


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{SUPERVISOR_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if body:
        req.add_header("Content-Type", "application/json")

    last_err = ""
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read())
            except Exception:
                return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            last_err = str(e.reason)
        except Exception as e:
            last_err = str(e)
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY * (attempt + 1))
    return {"success": False, "error": f"Supervisor unreachable after {MAX_RETRIES} attempts: {last_err}"}


def cmd_start(args: argparse.Namespace) -> int:
    print("[AOE] Spawning aquaculture mesh in Docker sandbox...")
    payload = {}
    if args.image:
        payload["image"] = args.image
    if args.memory:
        payload["memory_limit_mb"] = args.memory
    result = _request("POST", "/mesh/start", payload if payload else None)
    if result.get("success"):
        cid = result["data"]["container_id"]
        print(f"[AOE] Mesh online. Container ID: {cid[:12]}")
        return 0
    print(f"[AOE] ERROR: {result.get('error')}")
    return 1


def cmd_stop(args: argparse.Namespace) -> int:
    print("[AOE] Initiating stateless wipe and container shutdown...")
    result = _request("POST", "/mesh/stop")
    if result.get("success"):
        print("[AOE] Mesh wiped. Node dormant.")
        return 0
    print(f"[AOE] ERROR: {result.get('error')}")
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    result = _request("GET", "/mesh/status")
    if not result.get("success"):
        print(f"[AOE] ERROR: {result.get('error')}")
        return 1
    s = result["data"]
    print("-" * 50)
    print("  AOE SUPERVISOR - MESH STATUS")
    print("-" * 50)
    print(f"  Running        : {s.get('running', False)}")
    print(f"  Container ID   : {s.get('container_id', 'N/A')}")
    print(f"  Memory         : {s.get('memory_usage_mb', 0):.2f} / {s.get('memory_limit_mb', 0)} MB")
    print(f"  CPU            : {s.get('cpu_percent', 0):.2f}%")
    print(f"  PIDs           : {s.get('pid_count', 0)}")
    print(f"  Cycles         : {s.get('cycles_completed', 0)}")
    print(f"  Docker avail   : {s.get('docker_available', False)}")
    if s.get('last_error'):
        print(f"  Last error     : {s['last_error']}")
    print("-" * 50)
    return 0


def cmd_failsafe(args: argparse.Namespace) -> int:
    print("[AOE] !!! FAILSAFE TRIGGERED !!!")
    print("[AOE] Sending emergency kill to supervisor...")
    result = _request("POST", "/mesh/failsafe")
    if result.get("success"):
        print("[AOE] Container killed. Relays closed.")
        return 0
    print(f"[AOE] ERROR: {result.get('error')}")
    return 1


def cmd_logs(args: argparse.Namespace) -> int:
    result = _request("GET", "/mesh/logs")
    if not result.get("success"):
        print(f"[AOE] ERROR: {result.get('error')}")
        return 1
    lines = result["data"]["lines"]
    print(f"[AOE] Last {len(lines)} log lines:")
    for line in lines:
        print(f"  {line}")
    return 0


def cmd_relay_config(args: argparse.Namespace) -> int:
    print("[AOE] Relay configuration:")
    print(f"  Supervisor   : {SUPERVISOR_URL}")
    if args.peer:
        print(f"  Peer added   : {args.peer}")
        print("[AOE] NOTE: Peer registration is stored in-memory.")
        print("          To persist peers, export AOE_PEERS=192.168.4.10,192.168.4.11")
    else:
        print("  No peers configured. Use --peer to add a relay node.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="aoe_mesh",
        description="Agent of Empires — Aquaculture Mesh Control CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Spawn mesh in Docker sandbox")
    p_start.add_argument("--image", default="", help="Override Docker image")
    p_start.add_argument("--memory", type=int, default=0, help="Memory limit in MB")

    sub.add_parser("stop", help="Kill container and wipe state")
    sub.add_parser("status", help="Show mesh telemetry and resource usage")
    sub.add_parser("failsafe", help="Emergency mechanical failsafe")
    sub.add_parser("logs", help="Fetch last 100 log lines")

    p_relay = sub.add_parser("relay-config", help="Configure local relay peers")
    p_relay.add_argument("--peer", default="", help="Peer address (e.g. 192.168.4.10)")

    args = parser.parse_args()

    dispatch = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "failsafe": cmd_failsafe,
        "logs": cmd_logs,
        "relay-config": cmd_relay_config,
    }

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
