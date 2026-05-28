#!/usr/bin/env python3
"""
start_money_engine.py
=====================
CLI launcher for the autonomous money-making engine.

Usage:
    python tools/start_money_engine.py status
    python tools/start_money_engine.py start --autopilot
    python tools/start_money_engine.py start --verticals content,affiliate
    python tools/start_money_engine.py stop
    python tools/start_money_engine.py cycle --agent content
    python tools/start_money_engine.py inject --agent content_abc123 --action generate_blog
    python tools/start_money_engine.py pending
    python tools/start_money_engine.py approve --decision-id abc123
    python tools/start_money_engine.py pl
    python tools/start_money_engine.py dashboard
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


def cmd_status(args):
    resp = _request("GET", "/api/money-engine/status")
    print("=" * 60)
    print("MONEY ENGINE STATUS")
    print("=" * 60)
    print(json.dumps(resp, indent=2))


def cmd_start(args):
    print("Starting Money Engine...")
    payload = {
        "autonomy_tier": "AUTOPILOT" if args.autopilot else "OVERRIDE" if args.override else "DEFAULT",
        "interval_seconds": args.interval,
        "one_shot": args.one_shot,
    }
    if args.verticals:
        payload["verticals"] = args.verticals.split(",")
    resp = _request("POST", "/api/money-engine/start", payload)
    print(json.dumps(resp, indent=2))


def cmd_stop(args):
    resp = _request("POST", "/api/money-engine/stop")
    print(json.dumps(resp, indent=2))


def cmd_stop_agent(args):
    resp = _request("POST", f"/api/money-engine/agent/{args.agent_id}/stop")
    print(json.dumps(resp, indent=2))


def cmd_inject(args):
    payload = {
        "agent_id": args.agent,
        "action": args.action,
        "params": json.loads(args.payload) if args.payload else {},
        "reasoning": args.reasoning,
    }
    resp = _request("POST", "/api/money-engine/inject", payload)
    print(json.dumps(resp, indent=2))


def cmd_pending(args):
    resp = _request("GET", "/api/money-engine/pending")
    pending = resp.get("pending", [])
    if not pending:
        print("No pending decisions.")
        return
    for p in pending:
        print(f"[{p.get('decision_id')}] {p.get('vertical')} | {p.get('action')} | {p.get('reasoning')}")


def cmd_approve(args):
    payload = {"decision_id": args.decision_id, "approved": True, "modified_params": {}}
    resp = _request("POST", "/api/money-engine/approve", payload)
    print(json.dumps(resp, indent=2))


def cmd_reject(args):
    payload = {"decision_id": args.decision_id, "approved": False}
    resp = _request("POST", "/api/money-engine/reject", payload)
    print(json.dumps(resp, indent=2))


def cmd_autonomy(args):
    payload = {"tier": args.tier}
    resp = _request("POST", "/api/money-engine/autonomy", payload)
    print(json.dumps(resp, indent=2))


def cmd_pl(args):
    resp = _request("GET", "/api/money-engine/status")
    print("=" * 60)
    print("PROFIT & LOSS")
    print("=" * 60)
    print(f"Total Revenue: ${resp.get('total_revenue', 0):.2f}")
    print(f"Total Costs:   ${resp.get('total_costs', 0):.2f}")
    print(f"Net Profit:    ${resp.get('net_profit', 0):.2f}")
    print("\nAgents:")
    for aid, data in resp.get("agents", {}).items():
        print(f"  {aid}: rev=${data.get('revenue', 0):.2f} costs=${data.get('costs', 0):.2f} status={data.get('status')}")


def cmd_dashboard(args):
    import webbrowser
    url = f"{BASE_URL}/monetization"
    print(f"Opening dashboard: {url}")
    webbrowser.open(url)


def cmd_list(args):
    resp = _request("GET", "/api/money-engine/agents")
    print("Registered verticals:")
    for v in resp.get("verticals", []):
        print(f"  - {v}")


def main():
    parser = argparse.ArgumentParser(description="Money Engine Controller")
    sub = parser.add_subparsers(dest="command")

    p_status = sub.add_parser("status", help="Show engine status")
    p_status.set_defaults(func=cmd_status)

    p_start = sub.add_parser("start", help="Start the engine")
    p_start.add_argument("--autopilot", action="store_true", help="Full auto mode")
    p_start.add_argument("--override", action="store_true", help="Auto with pause on ambiguity")
    p_start.add_argument("--interval", type=int, default=300, help="Cycle interval")
    p_start.add_argument("--one-shot", action="store_true", help="Run one cycle and stop")
    p_start.add_argument("--verticals", type=str, help="Comma-separated verticals")
    p_start.set_defaults(func=cmd_start)

    p_stop = sub.add_parser("stop", help="Stop all agents")
    p_stop.set_defaults(func=cmd_stop)

    p_stop_agent = sub.add_parser("stop-agent", help="Stop one agent")
    p_stop_agent.add_argument("--agent-id", required=True)
    p_stop_agent.set_defaults(func=cmd_stop_agent)

    p_inject = sub.add_parser("inject", help="Inject a manual decision")
    p_inject.add_argument("--agent", required=True)
    p_inject.add_argument("--action", required=True)
    p_inject.add_argument("--payload", default="{}")
    p_inject.add_argument("--reasoning", default="manual")
    p_inject.set_defaults(func=cmd_inject)

    p_pending = sub.add_parser("pending", help="List pending decisions")
    p_pending.set_defaults(func=cmd_pending)

    p_approve = sub.add_parser("approve", help="Approve a pending decision")
    p_approve.add_argument("--decision-id", required=True)
    p_approve.set_defaults(func=cmd_approve)

    p_reject = sub.add_parser("reject", help="Reject a pending decision")
    p_reject.add_argument("--decision-id", required=True)
    p_reject.set_defaults(func=cmd_reject)

    p_autonomy = sub.add_parser("autonomy", help="Set autonomy tier")
    p_autonomy.add_argument("--tier", required=True, choices=["DEFAULT", "OVERRIDE", "AUTOPILOT"])
    p_autonomy.set_defaults(func=cmd_autonomy)

    p_pl = sub.add_parser("pl", help="Profit & Loss report")
    p_pl.set_defaults(func=cmd_pl)

    p_list = sub.add_parser("list", help="List registered verticals")
    p_list.set_defaults(func=cmd_list)

    p_dash = sub.add_parser("dashboard", help="Open monetization dashboard")
    p_dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
