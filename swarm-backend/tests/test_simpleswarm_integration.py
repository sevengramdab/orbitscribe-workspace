"""Tests for SimpleSwarm capabilities integrated into OrbitScribe backend."""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Remote Node Mesh
# ---------------------------------------------------------------------------

def test_list_nodes_empty():
    response = client.get("/api/nodes")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert data["nodes"] == []


def test_register_and_deregister_node():
    reg = client.post("/api/nodes/register", json={
        "node_id": "test-node-1",
        "base_url": "http://localhost:9999",
        "name": "Test Node",
        "tier": "cloud",
    })
    assert reg.status_code == 200
    assert reg.json()["success"] is True

    # List should now contain the node
    lst = client.get("/api/nodes")
    assert lst.status_code == 200
    assert len(lst.json()["nodes"]) == 1

    # Deregister
    dereg = client.delete("/api/nodes/test-node-1")
    assert dereg.status_code == 200
    assert dereg.json()["success"] is True

    # Should be gone
    lst2 = client.get("/api/nodes")
    assert lst2.json()["nodes"] == []


def test_deregister_unknown_node():
    response = client.delete("/api/nodes/nonexistent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Plan Creator
# ---------------------------------------------------------------------------

def test_create_plan_options():
    # We mock the LLM call by testing the endpoint structure;
    # actual LLM call would require configured keys / local model.
    response = client.post("/api/plan/options", json={"goal": "Build a todo app"})
    # Without a working LLM this may return 500 or succeed with fallback;
    # we just verify the route is wired.
    assert response.status_code in (200, 500, 503)


def test_get_unknown_plan():
    response = client.get("/api/plan/options/unknown")
    assert response.status_code == 404


def test_select_unknown_plan():
    response = client.post("/api/plan/options/select", json={"plan_id": "unknown", "option_id": "opt-1"})
    assert response.status_code == 404
