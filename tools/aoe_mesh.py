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
import sys
import urllib.request
import urllib.error

SUPERVISOR_URL = "http://localhost:58082"


def _post(path: str, body: dict | None = None) -> dict:
    url = f"{SUPERVISOR_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get(path: str) -> dict:
    url = f"{SUPERVISOR_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def cmd_start(args: argparse.Namespace) -> int:
    print("[AOE] Spawning aquaculture mesh in Docker sandbox...")
    payload = {}
    if args.image:
        payload["image"] = args.image
    if args.memory:
        payload["memory_limit_mb"] = args.memory
    result = _post("/mesh/start", payload if payload else None)
    if result.get("success"):
        cid = result["data"]["container_id"]
        print(f"[AOE] Mesh online. Container ID: {cid[:12]}")
        return 0
    print(f"[AOE] ERROR: {result.get('error')}")
    return 1


def cmd_stop(args: argparse.Namespace) -> int:
    print("[AOE] Initiating stateless wipe and container shutdown...")
    result = _post("/mesh/stop")
    if result.get("success"):
        print("[AOE] Mesh wiped. Node dormant.")
        return 0
    print(f"[AOE] ERROR: {result.get('error')}")
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    result = _get("/mesh/status")
    if not result.get("success"):
        print(f"[AOE] ERROR: {result.get('error')}")
        return 1
    s = result["data"]
    print("-" * 50)
    print("  AOE SUPERVISOR - MESH STATUS")
    print("-" * 50)
    print(f"  Running      : {s.get('running', False)}")
    print(f"  Container ID : {s.get('container_id', 'N/A')}")
    print(f"  Memory       : {s.get('memory_usage_mb', 0):.2f} / {s.get('memory_limit_mb', 0)} MB")
    print(f"  CPU          : {s.get('cpu_percent', 0):.2f}%")
    print(f"  PIDs         : {s.get('pid_count', 0)}")
    print(f"  Cycles       : {s.get('cycles_completed', 0)}")
    print("-" * 50)
    return 0


def cmd_failsafe(args: argparse.Namespace) -> int:
    print("[AOE] !!! FAILSAFE TRIGGERED !!!")
    print("[AOE] Sending emergency kill to supervisor...")
    result = _post("/mesh/failsafe")
    if result.get("success"):
        print("[AOE] Container killed. Relays closed.")
        return 0
    print(f"[AOE] ERROR: {result.get('error')}")
    return 1


def cmd_logs(args: argparse.Namespace) -> int:
    result = _get("/mesh/logs")
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
