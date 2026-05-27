"""
Monetization Swarm Controller
CLI to start, stop, monitor, and control the 10-agent business swarm.

Usage:
    python tools/monetization_controller.py status
    python tools/monetization_controller.py start --autopilot
    python tools/monetization_controller.py stop
    python tools/monetization_controller.py cycle --agent dropshipping
    python tools/monetization_controller.py inject --agent stripe --action create_invoice
    python tools/monetization_controller.py pl
    python tools/monetization_controller.py vault
    python tools/monetization_controller.py tools
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from typing import Optional

BASE_URL = "http://127.0.0.1:58081"


def _request(method: str, path: str, data: Optional[dict] = None) -> dict:
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            return {"error": json.loads(text)}
        except Exception:
            return {"error": text}
    except Exception as e:
        return {"error": str(e)}


def _stream_sse(path: str, data: dict):
    """Stream SSE events and print them."""
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode()
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode().strip()
                if line.startswith("data: "):
                    try:
                        event = json.loads(line[6:])
                        _print_event(event)
                        if event.get("event") == "complete" or event.get("type") == "done":
                            break
                    except Exception:
                        print(line)
    except Exception as e:
        print(f"[ERROR] {e}")


def _print_event(event: dict):
    ev_type = event.get("event") or event.get("type", "unknown")
    if ev_type == "status":
        print(f"[STATUS] {event.get('message', '')}")
    elif ev_type == "agent_cycle_complete":
        print(f"  -> {event['agent']}: {event['result']}")
    elif ev_type == "swarm_status":
        data = event.get("data", {})
        profit = data.get("net_profit", 0)
        rev = data.get("total_revenue", 0)
        print(f"[P&L] Revenue: ${rev:.2f} | Profit: ${profit:.2f} | Agents: {len(data.get('agents', {}))}")
    elif ev_type == "complete":
        print("[COMPLETE] Swarm cycle finished.")
    elif ev_type == "done":
        pass
    else:
        msg = event.get("message") or event.get("chunk") or str(event)
        if msg and msg.strip():
            print(f"[{ev_type.upper()}] {msg}")


def cmd_status(args):
    resp = _request("GET", "/api/monetization/status")
    if "error" in resp:
        print(f"Error: {resp['error']}")
        return
    print("=" * 60)
    print("MONETIZATION SWARM STATUS")
    print("=" * 60)
    print(f"Running:       {resp['running']}")
    print(f"Autonomy:      {resp['autonomy_tier']}")
    print(f"Total Revenue: ${resp['total_revenue']:.2f}")
    print(f"Total Costs:   ${resp['total_costs']:.2f}")
    print(f"Net Profit:    ${resp['net_profit']:.2f}")
    print(f"Vault Collections: {resp['vault_summary']}")
    print("\nAgents:")
    for name, agent in resp.get("agents", {}).items():
        ledger = agent.get("ledger", {})
        print(f"  {name:20s} Rev: ${ledger.get('lifetime_revenue', 0):.2f}  Decisions: {ledger.get('decisions_made', 0)}")


def cmd_start(args):
    print("Starting monetization swarm...")
    payload = {
        "autonomy_tier": "AUTOPILOT" if args.autopilot else "OVERRIDE" if args.override else "DEFAULT",
        "interval_seconds": args.interval,
        "one_shot": args.one_shot,
    }
    if args.verticals:
        payload["verticals"] = args.verticals.split(",")
    _stream_sse("/api/monetization/start", payload)


def cmd_stop(args):
    resp = _request("POST", "/api/monetization/stop")
    print(json.dumps(resp, indent=2))


def cmd_cycle(args):
    agent = args.agent
    resp = _request("POST", f"/api/monetization/agent/{agent}/cycle")
    print(json.dumps(resp, indent=2))


def cmd_inject(args):
    payload = {
        "agent_name": args.agent,
        "decision_type": args.action,
        "payload": json.loads(args.payload) if args.payload else {},
    }
    resp = _request("POST", "/api/monetization/inject", payload)
    print(json.dumps(resp, indent=2))


def cmd_pl(args):
    resp = _request("GET", "/api/monetization/pl")
    if "error" in resp:
        print(f"Error: {resp['error']}")
        return
    print("=" * 60)
    print("PROFIT & LOSS")
    print("=" * 60)
    print(f"Total Revenue: ${resp['total_revenue']:.2f}")
    print(f"Total Costs:   ${resp['total_costs']:.2f}")
    print(f"Net Profit:    ${resp['net_profit']:.2f}")
    print("\nPer-Agent Breakdown:")
    for name, data in resp.get("agent_breakdown", {}).items():
        print(f"  {name:20s} Rev: ${data['revenue']:.2f}  Costs: ${data['costs']:.2f}  Decisions: {data['decisions']}/{data['executed']}")


def cmd_vault(args):
    resp = _request("GET", "/api/monetization/vault")
    print(json.dumps(resp, indent=2))


def cmd_tools(args):
    resp = _request("GET", "/api/monetization/tools")
    if "error" in resp:
        print(f"Error: {resp['error']}")
        return
    print("=" * 60)
    print("BUSINESS TOOLS")
    print("=" * 60)
    for tool in resp.get("tools", []):
        print(f"  [{tool['category']}] {tool['name']}: {tool['description']}")


def cmd_agents(args):
    resp = _request("GET", "/api/monetization/agents")
    print(json.dumps(resp, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Monetization Swarm Controller")
    sub = parser.add_subparsers(dest="command")

    p_status = sub.add_parser("status", help="Show swarm status")
    p_status.set_defaults(func=cmd_status)

    p_start = sub.add_parser("start", help="Start the swarm")
    p_start.add_argument("--autopilot", action="store_true", help="Full auto mode")
    p_start.add_argument("--override", action="store_true", help="Auto with pause on ambiguity")
    p_start.add_argument("--interval", type=int, default=300, help="Cycle interval in seconds")
    p_start.add_argument("--one-shot", action="store_true", help="Run one cycle and stop")
    p_start.add_argument("--verticals", type=str, help="Comma-separated agent names")
    p_start.set_defaults(func=cmd_start)

    p_stop = sub.add_parser("stop", help="Stop all agents")
    p_stop.set_defaults(func=cmd_stop)

    p_cycle = sub.add_parser("cycle", help="Force one agent cycle")
    p_cycle.add_argument("--agent", required=True, help="Agent name")
    p_cycle.set_defaults(func=cmd_cycle)

    p_inject = sub.add_parser("inject", help="Inject a manual decision")
    p_inject.add_argument("--agent", required=True, help="Agent name")
    p_inject.add_argument("--action", required=True, help="Decision type")
    p_inject.add_argument("--payload", help="JSON payload string")
    p_inject.set_defaults(func=cmd_inject)

    p_pl = sub.add_parser("pl", help="Profit & Loss report")
    p_pl.set_defaults(func=cmd_pl)

    p_vault = sub.add_parser("vault", help="Vault summary")
    p_vault.set_defaults(func=cmd_vault)

    p_tools = sub.add_parser("tools", help="List business tools")
    p_tools.set_defaults(func=cmd_tools)

    p_agents = sub.add_parser("agents", help="List business agents")
    p_agents.set_defaults(func=cmd_agents)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
