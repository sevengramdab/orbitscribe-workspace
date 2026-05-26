"""Tests for the aquaculture mesh DAG system."""
import pytest
import json
import secrets
from dataclasses import asdict
from graphlib import TopologicalSorter

# Import reference types from node_bootstrap
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from node_bootstrap import NodeStatus, ActionTarget, TelemetryPayload

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.aquaculture.telemetry_agent import TelemetryAgent
from agents.aquaculture.dag_router_agent import DAGRouterAgent
from agents.aquaculture.ph_evaluator_agent import PhEvaluatorAgent
from agents.aquaculture.volume_evaluator_agent import VolumeEvaluatorAgent
from agents.aquaculture.actuator_dispatch_agent import ActuatorDispatchAgent
from agents.aquaculture.failsafe_agent import FailsafeAgent
from agents.aquaculture.network_relay_agent import NetworkRelayAgent


@pytest.mark.asyncio
async def test_telemetry_payload_generation():
    agent = TelemetryAgent()
    payload = await agent.fetch_telemetry()
    assert payload.status == NodeStatus.ACTIVE
    assert 800.0 <= payload.fluid_volume_liters <= 1200.0
    assert 6.0 <= payload.ph_level <= 8.0
    assert payload.node_id.startswith("alpha_node_")


@pytest.mark.asyncio
async def test_telemetry_agent_runnable():
    agent = TelemetryAgent()
    result = await agent.run("fetch")
    data = json.loads(result)
    assert "node_id" in data
    assert "fluid_volume_liters" in data
    assert "ph_level" in data


@pytest.mark.asyncio
async def test_dag_router_topological_order():
    agent = DAGRouterAgent()
    graph = TopologicalSorter()
    graph.add("evaluate_ph")
    graph.add("evaluate_volume", "evaluate_ph")
    graph.add("dispatch_actuator", "evaluate_volume")
    order = tuple(graph.static_order())
    assert order.index("evaluate_ph") < order.index("evaluate_volume")
    assert order.index("evaluate_volume") < order.index("dispatch_actuator")


@pytest.mark.asyncio
async def test_dag_router_ph_trigger():
    agent = DAGRouterAgent()
    payload = TelemetryPayload(
        node_id="test", fluid_volume_liters=1000.0, ph_level=6.2, status=NodeStatus.ACTIVE
    )
    result = await agent.execute_routing(payload)
    assert result == ActionTarget.ALKALINE_PUMP


@pytest.mark.asyncio
async def test_dag_router_volume_trigger():
    agent = DAGRouterAgent()
    payload = TelemetryPayload(
        node_id="test", fluid_volume_liters=850.0, ph_level=7.0, status=NodeStatus.ACTIVE
    )
    result = await agent.execute_routing(payload)
    assert result == ActionTarget.INTAKE_VALVE


@pytest.mark.asyncio
async def test_dag_router_steady_state():
    agent = DAGRouterAgent()
    payload = TelemetryPayload(
        node_id="test", fluid_volume_liters=1000.0, ph_level=7.0, status=NodeStatus.ACTIVE
    )
    result = await agent.execute_routing(payload)
    assert result == ActionTarget.STEADY_STATE


@pytest.mark.asyncio
async def test_dag_router_failsafe_on_exception():
    agent = DAGRouterAgent()
    # Passing None instead of payload should trigger exception handling
    result = await agent.execute_routing(None)
    assert result == ActionTarget.FAILSAFE


@pytest.mark.asyncio
async def test_ph_evaluator():
    agent = PhEvaluatorAgent()
    low = TelemetryPayload("t", 1000.0, 6.2, NodeStatus.ACTIVE)
    ok = TelemetryPayload("t", 1000.0, 7.0, NodeStatus.ACTIVE)
    assert await agent.evaluate(low) == ActionTarget.ALKALINE_PUMP
    assert await agent.evaluate(ok) == ActionTarget.STEADY_STATE


@pytest.mark.asyncio
async def test_volume_evaluator():
    agent = VolumeEvaluatorAgent()
    low = TelemetryPayload("t", 850.0, 7.0, NodeStatus.ACTIVE)
    ok = TelemetryPayload("t", 1000.0, 7.0, NodeStatus.ACTIVE)
    assert await agent.evaluate(low) == ActionTarget.INTAKE_VALVE
    assert await agent.evaluate(ok) == ActionTarget.STEADY_STATE


@pytest.mark.asyncio
async def test_actuator_dispatch():
    agent = ActuatorDispatchAgent()
    result = await agent.dispatch(ActionTarget.ALKALINE_PUMP)
    assert result["action"] == ActionTarget.ALKALINE_PUMP.value
    assert result["relay_closed"] is False
    result_fail = await agent.dispatch(ActionTarget.FAILSAFE)
    assert result_fail["relay_closed"] is True


@pytest.mark.asyncio
async def test_failsafe_trigger():
    agent = FailsafeAgent()
    assert await agent.check(ValueError("boom")) == ActionTarget.FAILSAFE
    assert await agent.check(None) == ActionTarget.STEADY_STATE


@pytest.mark.asyncio
async def test_network_relay_encrypt_decrypt():
    agent = NetworkRelayAgent()
    payload = {"action": ActionTarget.ALKALINE_PUMP.value, "node_id": "test_node"}
    deliveries = await agent.broadcast(payload)
    assert len(deliveries) == 0  # no peers configured yet
    # Add a peer and broadcast again
    agent.add_peer("192.168.4.10")
    deliveries = await agent.broadcast(payload)
    assert len(deliveries) == 1
    assert deliveries[0]["peer"] == "192.168.4.10"
    assert deliveries[0]["status"] == "transmitted"
    # Verify decrypt round-trip
    plaintext = json.dumps(payload, default=str).encode()
    ciphertext = agent._fernet.encrypt(plaintext)
    recovered = await agent.decrypt(ciphertext)
    assert recovered["action"] == ActionTarget.ALKALINE_PUMP.value
    assert recovered["node_id"] == "test_node"


def test_node_status_enum():
    assert NodeStatus.ACTIVE == "ephemeral_active"
    assert NodeStatus.DORMANT == "stateless_dormant"
    assert NodeStatus.CRITICAL == "failsafe_engaged"


def test_action_target_enum():
    assert ActionTarget.ALKALINE_PUMP == "alkaline_pump_open"
    assert ActionTarget.INTAKE_VALVE == "intake_valve_open"
    assert ActionTarget.STEADY_STATE == "steady_state_idle"
    assert ActionTarget.FAILSAFE == "mechanical_failsafe_engaged"
