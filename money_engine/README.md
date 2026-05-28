# Money Engine

Autonomous money-making system that controls mouse, keyboard, and browser to perform real revenue-generating tasks.

## Architecture

```
money_engine/
├── __init__.py              # Package exports
├── browser_controller.py    # Chrome automation + screenshots
├── vision_helper.py         # Lightweight image analysis
├── base_agent.py            # Abstract base for all agents
├── orchestrator.py          # Coordinates 10 agents
├── kimi_bridge.py           # Manual approval bridge
├── agents/
│   ├── content_agent.py
│   ├── affiliate_agent.py
│   ├── dropshipping_agent.py
│   ├── saas_agent.py
│   ├── marketplace_agent.py
│   ├── leadgen_agent.py
│   ├── ads_agent.py
│   ├── licensing_agent.py
│   ├── subscription_agent.py
│   └── consulting_agent.py
```

## How It Works

1. **Decision**: Each agent decides its next action (generate content, post to Medium, research products, etc.)
2. **Approval** (DEFAULT/OVERRIDE mode): The `KimiBridge` writes a pending decision file. Kimi (or a human) reviews and approves/rejects.
3. **Execution**: The agent uses `BrowserController` (pyautogui) to control Chrome, fill forms, click buttons, take screenshots.
4. **Asset Generation**: Agents call the swarm-backend `business_tools` registry to create ebooks, blog posts, apps, email sequences, etc.
5. **P&L Tracking**: Revenue and costs are tracked per-agent and globally.

## Autonomy Tiers

| Tier | Behavior |
|------|----------|
| **DEFAULT** | Every decision requires Kimi approval via the bridge |
| **OVERRIDE** | Decisions auto-run unless Kimi rejects within 60s |
| **AUTOPILOT** | Fully autonomous — Kimi is notified but not blocking |

## Quick Start

### Python API
```python
from money_engine import MoneyOrchestrator, KimiBridge

orch = MoneyOrchestrator()
bridge = KimiBridge(orch)

# Start all 10 agents on autopilot
orch.set_autonomy("AUTOPILOT")
orch.start_swarm()

# Check status
print(orch.get_status())

# Stop everything
orch.stop_all()
```

### CLI
```bash
# Start all agents in autopilot mode
python tools/start_money_engine.py start --autopilot

# Start only specific verticals
python tools/start_money_engine.py start --verticals content,affiliate,saas

# One-shot cycle (run once and stop)
python tools/start_money_engine.py start --one-shot

# Check P&L
python tools/start_money_engine.py pl

# List pending decisions needing approval
python tools/start_money_engine.py pending

# Approve a decision
python tools/start_money_engine.py approve --decision-id <id>
```

### PowerShell Launcher
```powershell
# Start backend + money engine together
.\tools\launch_money_engine.ps1 -Autopilot

# One-shot with specific verticals
.\tools\launch_money_engine.ps1 -Verticals content,affiliate -OneShot
```

### FastAPI Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/money-engine/status` | Full status + P&L |
| POST | `/api/money-engine/start` | Start swarm |
| POST | `/api/money-engine/stop` | Stop all agents |
| POST | `/api/money-engine/inject` | Manual decision injection |
| GET | `/api/money-engine/pending` | Pending approvals |
| POST | `/api/money-engine/approve` | Approve a decision |
| POST | `/api/money-engine/reject` | Reject a decision |
| POST | `/api/money-engine/autonomy` | Set autonomy tier |

## Kimi Control Flow

When running in `DEFAULT` or `OVERRIDE` mode:

1. Agent makes a decision
2. `KimiBridge` writes `tools/saved_sessions/money_engine/pending_<id>.json`
3. Kimi reads the file, sees the action + screenshot
4. Kimi calls `bridge.approve(decision_id)` or `bridge.reject(decision_id)`
5. Agent proceeds or skips

In `AUTOPILOT` mode, steps 2-4 are skipped and the agent executes immediately.

## Safety

- `pyautogui.FAILSAFE = True` — move mouse to top-left corner to emergency-stop
- All browser actions use percentage coordinates relative to Chrome window
- Screenshots are taken before and after critical actions for audit trail
- Agents save state to `tools/saved_sessions/money_engine/` after every cycle
