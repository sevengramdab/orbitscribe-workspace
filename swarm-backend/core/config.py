"""Swarm backend configuration with API lockout modes."""

import os

API_MODE = os.environ.get("SWARM_API_MODE", "hybrid").lower()
HOST = os.environ.get("SWARM_HOST", "127.0.0.1")
PORT = int(os.environ.get("SWARM_PORT", "58081"))

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL", "http://127.0.0.1:1234")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "")

LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "llama3.1:8b")
CLOUD_MODEL = os.environ.get("CLOUD_MODEL", "gemini-2.0-flash")
ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", CLOUD_MODEL)

MAX_AGENTS = int(os.environ.get("MAX_AGENTS", "5"))
SWARM_TIMEOUT = int(os.environ.get("SWARM_TIMEOUT", "120"))

# LLM temperature: 0 = deterministic, 1 = very creative
TEMPERATURE = float(os.environ.get("SWARM_TEMPERATURE", "0.7"))

# Subagent spawning mode: cloud | local | hybrid
SUBAGENT_MODE = os.environ.get("SUBAGENT_MODE", "hybrid").lower()

# LIVE MONEY MODE — disables all mock/simulation fallbacks
LIVE_MODE = os.environ.get("LIVE_MODE", "false").lower() in ("true", "1", "yes", "on")

# Business API keys (used when LIVE_MODE=True)
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
PRINTIFY_API_KEY = os.environ.get("PRINTIFY_API_KEY", "")
PRINTIFY_SHOP_ID = os.environ.get("PRINTIFY_SHOP_ID", "")
ETSY_API_KEY = os.environ.get("ETSY_API_KEY", "")
ETSY_SHOP_ID = os.environ.get("ETSY_SHOP_ID", "")
SHOPIFY_SHOP_DOMAIN = os.environ.get("SHOPIFY_SHOP_DOMAIN", "")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
AMAZON_ASSOCIATES_TAG = os.environ.get("AMAZON_ASSOCIATES_TAG", "")
BINANCE_REF = os.environ.get("BINANCE_REF", "")
COINBASE_REF = os.environ.get("COINBASE_REF", "")
LEDGER_REF = os.environ.get("LEDGER_REF", "")
BYBIT_REF = os.environ.get("BYBIT_REF", "")
OKX_REF = os.environ.get("OKX_REF", "")
ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN_API_KEY", "")

# Default workspace root — auto-detect project root from backend location, fallback to cwd, then home
_script_dir = os.path.dirname(os.path.abspath(__file__))
# config.py is in swarm-backend/core/, so project root is two levels up
_detected_project_root = os.path.abspath(os.path.join(_script_dir, "..", ".."))
# Validate: project root should contain swarm-backend/ and extension/ or tools/
if not (os.path.isdir(os.path.join(_detected_project_root, "swarm-backend")) and
        (os.path.isdir(os.path.join(_detected_project_root, "extension")) or
         os.path.isdir(os.path.join(_detected_project_root, "tools")))):
    # Fall back to parent of cwd (backend is usually started from swarm-backend/)
    _detected_project_root = os.path.abspath(os.path.join(os.getcwd(), ".."))

_default_workspace = _detected_project_root
WORKSPACE_ROOT = os.environ.get("ORBITSCRIBE_WORKSPACE_ROOT", _default_workspace)

# Ensure workspace exists
os.makedirs(WORKSPACE_ROOT, exist_ok=True)

