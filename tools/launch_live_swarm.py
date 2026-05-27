"""
Launch the Monetization Swarm in LIVE MODE.
Generates real deliverables to disk. Agents without API keys will error
and be skipped so the rest can keep printing money.

Usage:
    python tools/launch_live_swarm.py
    python tools/launch_live_swarm.py --one-shot
    python tools/launch_live_swarm.py --agents dropshipping,content_marketing,affiliate
"""

import os
import sys
import asyncio
import argparse

# Force LIVE_MODE before any imports
os.environ["LIVE_MODE"] = "true"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "swarm-backend"))

from agents.business import _load_all_agents, BUSINESS_AGENT_REGISTRY
from agents.business.swarm_orchestrator import MonetizationSwarmOrchestrator
from core.model_router import ModelRouter


def print_banner():
    print("=" * 70)
    print("  MONETIZATION SWARM — LIVE MODE")
    print("  No simulations. Real files. Real deliverables.")
    print("=" * 70)
    print()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--one-shot", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--agents", type=str, help="Comma-separated agent names")
    parser.add_argument("--interval", type=int, default=300, help="Cycle interval")
    args = parser.parse_args()

    print_banner()

    router = ModelRouter()
    orchestrator = MonetizationSwarmOrchestrator(model_router=router, autonomy_tier="AUTOPILOT")

    agents_to_run = args.agents.split(",") if args.agents else list(orchestrator.agents.keys())
    print(f"Agents ready: {agents_to_run}")
    print(f"Output dirs: products/, content/, leads/, revenue/")
    print()

    if args.one_shot:
        print("[LIVE] Running one-shot cycle...")
        results = await orchestrator.run_cycle_all()
        for name, result in results.items():
            if name not in agents_to_run:
                continue
            if isinstance(result, Exception):
                print(f"  [FAIL] {name}: {result}")
            else:
                print(f"  [OK]   {name}: cycle complete")
    else:
        print("[LIVE] Starting autonomous loops... Press Ctrl+C to stop.")
        await orchestrator.start_all(interval_seconds=args.interval)
        try:
            while True:
                await asyncio.sleep(30)
                status = orchestrator.get_swarm_status()
                print(f"[P&L] Revenue: ${status['total_revenue']:.2f} | Profit: ${status['net_profit']:.2f}")
        except KeyboardInterrupt:
            print("\n[LIVE] Stopping swarm...")
            await orchestrator.stop_all()

    print()
    print("=" * 70)
    print("  LIVE RUN COMPLETE")
    print("=" * 70)
    final = orchestrator.get_swarm_status()
    print(f"Total Revenue: ${final['total_revenue']:.2f}")
    print(f"Net Profit:    ${final['net_profit']:.2f}")
    print()
    print("Check your deliverables:")
    print("  products/     — apps, assets, POD designs")
    print("  content/      — blog posts, emails, affiliate articles")
    print("  leads/        — scraped leads + outreach drafts")
    print("  revenue/      — transaction records")


if __name__ == "__main__":
    asyncio.run(main())
