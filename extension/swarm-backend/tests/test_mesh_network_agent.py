"""Tests for the MeshNetwork agent and mesh tools."""
import pytest
import json
import asyncio

from agents.aquaculture.mesh_network_agent import MeshNetworkAgent
from agents.aquaculture.types import NodeStatus
from core.tool_executor import execute_tool


@pytest.mark.asyncio
async def test_mesh_network_agent_init():
    agent = MeshNetworkAgent()
    assert agent.peers == {}
    assert agent.topology_version == 0


@pytest.mark.asyncio
async def test_register_and_discover_peer():
    agent = MeshNetworkAgent()
    peer = await agent.register_peer("node-beta", "http://192.168.1.50:58081", NodeStatus.ACTIVE)
    assert peer["node_id"] == "node-beta"
    assert peer["status"] == "ephemeral_active"

    peers = await agent.discover_peers()
    assert len(peers) == 1
    assert peers[0]["node_id"] == "node-beta"


@pytest.mark.asyncio
async def test_gossip_topology():
    agent = MeshNetworkAgent()
    await agent.register_peer("node-a", "http://10.0.0.1", NodeStatus.ACTIVE)
    await agent.register_peer("node-b", "http://10.0.0.2", NodeStatus.DORMANT)

    topo = await agent.gossip_topology()
    assert topo["peer_count"] == 2
    assert topo["topology_version"] == 2
    assert "node-a" in topo["peers"]
    assert "node-b" in topo["peers"]


@pytest.mark.asyncio
async def test_route_to_peer():
    agent = MeshNetworkAgent()
    await agent.register_peer("node-gamma", "http://10.0.0.3", NodeStatus.ACTIVE)

    result = await agent.route_to_peer("node-gamma", {"action": "pump_on"})
    assert result["success"] is True
    assert result["node_id"] == "node-gamma"

    result_unknown = await agent.route_to_peer("node-delta", {"action": "pump_on"})
    assert result_unknown["success"] is False


@pytest.mark.asyncio
async def test_mesh_network_agent_run():
    agent = MeshNetworkAgent()
    await agent.register_peer("p1", "http://1.1.1.1", NodeStatus.ACTIVE)

    resp = await agent.run("discover peers")
    data = json.loads(resp)
    assert data["status"] == "ok"
    assert data["peers_found"] == 1

    resp = await agent.run("show topology")
    data = json.loads(resp)
    assert data["status"] == "ok"
    assert data["topology"]["peer_count"] == 1


def test_tool_mesh_status():
    result = execute_tool("mesh_status", {"cycles": 1})
    assert result["status"] == "ok"
    data = result["data"]
    assert data["cycles"] == 1
    assert len(data["results"]) == 1
    r = data["results"][0]
    assert "ph_level" in r
    assert "fluid_volume_liters" in r
    assert "route_action" in r
    assert "peers_discovered" in r
    assert data["summary"]["all_ph_ok"] in (True, False)


def test_tool_mesh_broadcast():
    result = execute_tool("mesh_broadcast", {"message": "test broadcast"})
    assert result["status"] == "ok"
    assert result["data"]["message"] == "test broadcast"


def test_tool_mesh_broadcast_missing_message():
    result = execute_tool("mesh_broadcast", {})
    assert result["status"] == "error"
    assert "message" in result["error"]
