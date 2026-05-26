"""
discovery.py
============
Simple UDP broadcast discovery for OrbitScribe nodes on the local network.

ELI5: Like shouting "Any OrbitScribe nodes here?" in your local network
      and listening for replies.
"""
from __future__ import annotations

import json
import socket
import struct
import threading
import time
from typing import List, Dict, Any, Optional

DISCOVERY_PORT = 58082
DISCOVERY_MAGIC = b"ORBITSCRIBE_DISCOVER_V1"
BROADCAST_ADDR = "<broadcast>"


class DiscoveryService:
    """UDP broadcast discovery for mesh nodes."""

    def __init__(self, node_info: Dict[str, Any], port: int = DISCOVERY_PORT):
        self.node_info = node_info
        self.port = port
        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._discovered: List[Dict[str, Any]] = []

    def start(self) -> None:
        """Start listening for discovery broadcasts."""
        if self._running:
            return
        self._running = True
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self._socket.bind(("0.0.0.0", self.port))
        except OSError:
            # Port may be in use, try random
            self._socket.bind(("0.0.0.0", 0))
            self.port = self._socket.getsockname()[1]

        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the discovery listener."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def _listen(self) -> None:
        """Background thread: listen for discovery packets."""
        while self._running and self._socket:
            try:
                self._socket.settimeout(2.0)
                data, addr = self._socket.recvfrom(1024)
                if not data.startswith(DISCOVERY_MAGIC):
                    continue
                # It's a discovery request — reply with our info
                reply = json.dumps({"magic": DISCOVERY_MAGIC.decode(), "node": self.node_info}).encode("utf-8")
                self._socket.sendto(reply, addr)

                # If it also contains node info, record it as a peer
                try:
                    payload = json.loads(data[len(DISCOVERY_MAGIC):].decode("utf-8", errors="ignore"))
                    if payload.get("node"):
                        self._record_peer(payload["node"], addr[0])
                except Exception:
                    pass
            except socket.timeout:
                continue
            except Exception:
                break

    def _record_peer(self, node: Dict[str, Any], ip: str) -> None:
        """Record a discovered peer, avoiding duplicates."""
        node_id = node.get("node_id", "")
        if not node_id or node_id == self.node_info.get("node_id"):
            return
        for existing in self._discovered:
            if existing.get("node_id") == node_id:
                existing["last_seen"] = time.time()
                return
        node["ip"] = ip
        node["last_seen"] = time.time()
        self._discovered.append(node)

    def discover(self, timeout: float = 3.0) -> List[Dict[str, Any]]:
        """Broadcast a discovery request and collect responses."""
        self._discovered.clear()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        request = DISCOVERY_MAGIC + json.dumps({"node": self.node_info}).encode("utf-8")
        try:
            sock.sendto(request, (BROADCAST_ADDR, self.port))
        except Exception:
            pass

        start = time.time()
        while time.time() - start < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                if not data.startswith(DISCOVERY_MAGIC):
                    continue
                try:
                    payload = json.loads(data[len(DISCOVERY_MAGIC):].decode("utf-8", errors="ignore"))
                    if payload.get("node"):
                        self._record_peer(payload["node"], addr[0])
                except Exception:
                    pass
            except socket.timeout:
                break
            except Exception:
                break
        sock.close()
        return list(self._discovered)

    def get_discovered(self) -> List[Dict[str, Any]]:
        """Return previously discovered peers (from passive listening)."""
        # Filter out stale peers (> 5 min)
        cutoff = time.time() - 300
        self._discovered = [p for p in self._discovered if p.get("last_seen", 0) > cutoff]
        return list(self._discovered)


# Global singleton
_discovery_service: Optional[DiscoveryService] = None


def get_discovery_service(node_info: Dict[str, Any] | None = None) -> DiscoveryService:
    global _discovery_service
    if _discovery_service is None and node_info is not None:
        _discovery_service = DiscoveryService(node_info)
    return _discovery_service
