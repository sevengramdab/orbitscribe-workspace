"""Mesh Network Agent — handles inter-node topology gossip and peer discovery.

This agent maintains a registry of known peer nodes in the archipelago,
exchanges topology gossip, and routes encrypted payloads between nodes.
"""
import json
import asyncio
from typing import Dict, List, Optional
from dataclasses import asdict

from agents.aquaculture.types import NodeStatus, TelemetryPayload


class MeshNetworkAgent:
    """Manages inter-node communication and topology gossip."""

    def __init__(self):
        self.peers: Dict[str, Dict] = {}
        self.topology_version = 0

    async def discover_peers(self, timeout: float = 2.0) -> List[Dict]:
        """Broadcast a discovery request and collect peer responses."""
        # Stub: in a real deployment, this would use UDP multicast or BLE
        await asyncio.sleep(0.05)
        return list(self.peers.values())

    async def register_peer(self, node_id: str, endpoint: str, status: NodeStatus) -> Dict:
        """Register a newly discovered peer."""
        self.peers[node_id] = {
            "node_id": node_id,
            "endpoint": endpoint,
            "status": status.value,
            "last_seen": asyncio.get_event_loop().time(),
        }
        self.topology_version += 1
        return self.peers[node_id]

    async def gossip_topology(self) -> Dict:
        """Return current topology summary for gossip exchange."""
        return {
            "topology_version": self.topology_version,
            "peer_count": len(self.peers),
            "peers": list(self.peers.keys()),
        }

    async def route_to_peer(self, node_id: str, payload: Dict) -> Dict:
        """Route an encrypted payload to a specific peer."""
        if node_id not in self.peers:
            return {"success": False, "error": f"Peer {node_id} not in topology"}
        # Stub: in a real deployment, this would encrypt and send over socket
        await asyncio.sleep(0.05)
        return {"success": True, "node_id": node_id, "routed": payload}

    async def run(self, task: str, context: str = "", history: list = None) -> str:
        """Execute mesh network operation based on task."""
        if "discover" in task.lower():
            peers = await self.discover_peers()
            return json.dumps({"status": "ok", "peers_found": len(peers), "peers": peers})
        elif "gossip" in task.lower() or "topology" in task.lower():
            topo = await self.gossip_topology()
            return json.dumps({"status": "ok", "topology": topo})
        elif "route" in task.lower():
            return json.dumps({"status": "ok", "message": "Routing stub active. Use route_to_peer(node_id, payload) for actual routing."})
        else:
            return json.dumps({"status": "ok", "peer_count": len(self.peers), "topology_version": self.topology_version})
