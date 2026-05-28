import sys
sys.path.insert(0, '.')

from money_engine.orchestrator import MoneyOrchestrator

orch = MoneyOrchestrator()
orch.set_autonomy("AUTOPILOT")

verticals = orch.start_swarm(one_shot=True)
print("Start swarm result:", verticals)
