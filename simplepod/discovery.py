"""UDP peer discovery for SimplePod."""
import json
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable

from config import DISCOVERY_PORT, DISCOVERY_INTERVAL, DISCOVERY_TIMEOUT, NODE_ID, NODE_NAME, NODE_ROLE, API_PORT


@dataclass
class Peer:
    node_id: str
    name: str
    role: str
    ip: str
    api_port: int
    last_seen: float = field(default_factory=time.time)

    def api_url(self) -> str:
        return f"http://{self.ip}:{self.api_port}"


class DiscoveryService:
    """UDP broadcast discovery. Finds peers on the local network."""

    def __init__(self, on_peer_found: Optional[Callable[[Peer], None]] = None):
        self.peers: Dict[str, Peer] = {}
        self._on_peer_found = on_peer_found
        self._sock: Optional[socket.socket] = None
        self._running = False
        self._listen_thread: Optional[threading.Thread] = None
        self._broadcast_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind(("0.0.0.0", DISCOVERY_PORT))
        except OSError:
            # Port might be in use, try ephemeral
            self._sock.bind(("0.0.0.0", 0))

        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()

        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._broadcast_thread.start()

        # Prune stale peers periodically
        self._prune_thread = threading.Thread(target=self._prune_loop, daemon=True)
        self._prune_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _listen_loop(self) -> None:
        while self._running:
            try:
                self._sock.settimeout(2.0)
                data, addr = self._sock.recvfrom(4096)
                msg = json.loads(data.decode("utf-8"))
                if msg.get("type") == "simplepod_hello":
                    peer = Peer(
                        node_id=msg["node_id"],
                        name=msg["name"],
                        role=msg["role"],
                        ip=addr[0],
                        api_port=msg["api_port"],
                    )
                    # Don't add ourselves
                    if peer.node_id == NODE_ID:
                        continue
                    with self._lock:
                        is_new = peer.node_id not in self.peers
                        self.peers[peer.node_id] = peer
                    if is_new and self._on_peer_found:
                        self._on_peer_found(peer)
            except socket.timeout:
                continue
            except Exception:
                continue

    def _broadcast_loop(self) -> None:
        while self._running:
            try:
                msg = json.dumps({
                    "type": "simplepod_hello",
                    "node_id": NODE_ID,
                    "name": NODE_NAME,
                    "role": NODE_ROLE,
                    "api_port": API_PORT,
                }).encode("utf-8")
                self._sock.sendto(msg, ("<broadcast>", DISCOVERY_PORT))
            except Exception:
                pass
            time.sleep(DISCOVERY_INTERVAL)

    def _prune_loop(self) -> None:
        while self._running:
            time.sleep(DISCOVERY_INTERVAL)
            now = time.time()
            with self._lock:
                stale = [nid for nid, p in self.peers.items() if now - p.last_seen > DISCOVERY_TIMEOUT]
                for nid in stale:
                    del self.peers[nid]

    def get_peers(self) -> List[Peer]:
        with self._lock:
            return list(self.peers.values())

    def get_peer(self, node_id: str) -> Optional[Peer]:
        with self._lock:
            return self.peers.get(node_id)
