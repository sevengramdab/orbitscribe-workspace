"""
mode_guard.py
=============
Strict SIMULATION vs LIVE mode gating for the OrbitScribe monetization swarm.

Prevents accidental live transactions when keys are missing or mode is SIM.
All business agents MUST call check_gate() before executing real financial actions.

Usage:
    from core.mode_guard import mode_guard
    mode_guard.check_gate("saas_micro_app", action="create_invoice")
    # Raises ModeGuardError if not in LIVE mode or missing API keys
"""
from __future__ import annotations

import os
import json
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Optional

MODE_STATE_PATH = Path(__file__).parent.parent.parent / "tools" / "saved_sessions" / "mode_guard_state.json"

REQUIRED_LIVE_KEYS: Dict[str, List[str]] = {
    "affiliate": ["AMAZON_ASSOCIATES_TAG"],
    "content_marketing": ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"],
    "print_on_demand": ["PRINTIFY_API_KEY", "PRINTIFY_SHOP_ID", "ETSY_API_KEY", "ETSY_SHOP_ID"],
    "dropshipping": ["SPOCKET_API_KEY", "ALIEXPRESS_API_KEY", "OBERLO_API_KEY"],
    "saas_micro_app": ["STRIPE_API_KEY", "STRIPE_SECRET_KEY"],
}


class Mode(Enum):
    SIMULATION = "SIMULATION"
    LIVE = "LIVE"


class ModeGuardError(Exception):
    """Raised when a live action is attempted in SIMULATION mode or with missing credentials."""
    pass


class ModeGuard:
    """Central authority for SIMULATION vs LIVE mode."""

    def __init__(self):
        self._mode: Mode = Mode.SIMULATION
        self._live_ready: Dict[str, bool] = {}
        self._load_state()
        self._validate_live_readiness()

    # ── Persistence ──────────────────────────────────────────────────────

    def _load_state(self):
        if MODE_STATE_PATH.exists():
            try:
                data = json.loads(MODE_STATE_PATH.read_text(encoding="utf-8"))
                raw = data.get("mode", "SIMULATION")
                self._mode = Mode(raw) if raw in (m.value for m in Mode) else Mode.SIMULATION
            except Exception:
                self._mode = Mode.SIMULATION
        else:
            # Default to SIMULATION — never default to LIVE
            self._mode = Mode.SIMULATION
            self._save_state()

    def _save_state(self):
        MODE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        MODE_STATE_PATH.write_text(
            json.dumps({
                "mode": self._mode.value,
                "live_ready": self._live_ready,
                "validated_at": __import__("time").time(),
            }, indent=2),
            encoding="utf-8",
        )

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def is_live(self) -> bool:
        return self._mode == Mode.LIVE

    @property
    def is_simulation(self) -> bool:
        return self._mode == Mode.SIMULATION

    def get_status(self) -> dict:
        """Full status for dashboards and agents."""
        env = os.environ
        verticals = {}
        for vertical, keys in REQUIRED_LIVE_KEYS.items():
            key_status = {}
            for k in keys:
                val = env.get(k, "")
                key_status[k] = bool(val) and not val.startswith(("sk_test_", "your-", "..."))
            present = sum(key_status.values())
            total = len(key_status)
            if present == total:
                status = "green"
            elif present > 0:
                status = "yellow"
            else:
                status = "red"
            verticals[vertical] = {
                "ready": status == "green",
                "status": status,
                "keys": key_status,
            }
        return {
            "mode": self._mode.value,
            "is_live": self.is_live,
            "live_ready": {v: d["ready"] for v, d in verticals.items()},
            "verticals": verticals,
            "all_systems_ready": self.is_live and all(d["ready"] for d in verticals.values()),
            "warnings": self._get_warnings(),
        }

    def set_mode(self, mode: Mode | str, force: bool = False) -> dict:
        """
        Switch mode. Requires validation in LIVE mode.
        Returns status dict with success/error info.
        """
        if isinstance(mode, str):
            mode = Mode(mode.upper())

        if mode == Mode.LIVE:
            self._validate_live_readiness()
            missing = [k for k, v in self._live_ready.items() if not v]
            if missing and not force:
                return {
                    "success": False,
                    "error": f"Cannot enter LIVE mode. Missing credentials for: {', '.join(missing)}",
                    "missing_systems": missing,
                }

        self._mode = mode
        self._save_state()
        return {
            "success": True,
            "mode": self._mode.value,
            "message": f"Mode set to {self._mode.value}",
        }

    def check_gate(self, system: str, action: str = "") -> None:
        """
        Mandatory gate check before any live financial action.
        Raises ModeGuardError if blocked.
        """
        if self._mode == Mode.SIMULATION:
            raise ModeGuardError(
                f"[BLOCKED] Action '{action}' on system '{system}' is blocked: "
                f"Swarm is in SIMULATION mode. No real money is moved. "
                f"To go live, set mode to LIVE and provide all API keys."
            )

        ready = self._live_ready.get(system)
        if ready is False:
            raise ModeGuardError(
                f"[BLOCKED] Action '{action}' on system '{system}' is blocked: "
                f"LIVE mode is active but credentials for '{system}' are missing or invalid."
            )

    def simulate_only(self, system: str, action: str = "") -> bool:
        """
        Returns True if this call should be simulated (not live).
        Use this for soft-gating where you want to fall back to simulation.
        """
        try:
            self.check_gate(system, action)
            return False
        except ModeGuardError:
            return True

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_live_readiness(self):
        """Scan environment for required API keys per vertical."""
        env = os.environ
        for vertical, keys in REQUIRED_LIVE_KEYS.items():
            self._live_ready[vertical] = all(
                bool(env.get(k)) and not env.get(k, "").startswith(("sk_test_", "your-", "..."))
                for k in keys
            )

    def _get_warnings(self) -> List[str]:
        warnings = []
        if self._mode == Mode.LIVE:
            for vertical, ready in self._live_ready.items():
                if not ready:
                    warnings.append(f"Vertical '{vertical}' is not configured for LIVE mode.")
        return warnings


# Global singleton
mode_guard = ModeGuard()
