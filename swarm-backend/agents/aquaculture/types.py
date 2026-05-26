"""Canonical shared types for the aquaculture mesh DAG."""
from dataclasses import dataclass
from enum import Enum


class NodeStatus(str, Enum):
    ACTIVE = "ephemeral_active"
    DORMANT = "stateless_dormant"
    CRITICAL = "failsafe_engaged"


class ActionTarget(str, Enum):
    ALKALINE_PUMP = "alkaline_pump_open"
    INTAKE_VALVE = "intake_valve_open"
    STEADY_STATE = "steady_state_idle"
    FAILSAFE = "mechanical_failsafe_engaged"


@dataclass(frozen=True)
class TelemetryPayload:
    node_id: str
    fluid_volume_liters: float
    ph_level: float
    status: NodeStatus
