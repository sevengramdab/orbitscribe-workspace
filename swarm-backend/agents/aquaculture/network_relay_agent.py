"""Network Relay Agent — encrypted local mesh broadcaster for actuator payloads."""
import json
import logging
from typing import Any
from cryptography.fernet import Fernet
from agents.base import Agent
from agents.aquaculture.types import ActionTarget

logger = logging.getLogger("NetworkRelay")


class NetworkRelayAgent(Agent):
    """Encrypts actuator commands and broadcasts them over the local mesh network.

    In a production deployment, peers are Raspberry Pi/Arduino relay nodes listening
    on a TLS-secured WebSocket or raw UDP socket. The payload is encrypted with
    Fernet (AES-128-CBC + HMAC) so that even if the serial or network line is
    tapped, the attacker sees only ciphertext.
    """

    def __init__(self, key: bytes | None = None):
        super().__init__(
            name="NetworkRelay",
            role="Encrypts and broadcasts actuator payloads over local mesh network",
            prompt_template="",
        )
        self._key: bytes = key or Fernet.generate_key()
        self._fernet: Fernet = Fernet(self._key)
        self._peers: list[str] = []

    @property
    def key(self) -> bytes:
        return self._key

    def add_peer(self, addr: str) -> None:
        """Register a local relay node (e.g. '192.168.4.10' or '/dev/ttyUSB0')."""
        self._peers.append(addr)

    async def broadcast(self, payload: dict) -> list[dict]:
        """Encrypt payload and return delivery stubs for each peer."""
        plaintext = json.dumps(payload, default=str).encode()
        ciphertext: bytes = self._fernet.encrypt(plaintext)
        deliveries = []
        for peer in self._peers:
            # Stub: in production this frame is pushed over a TLS WebSocket or
            # serial-over-UDP tunnel. We keep it stateless — no retries, no ACKs.
            logger.info(
                "[ENCRYPTED BROADCAST → %s] %s... (%d bytes)",
                peer,
                ciphertext[:24].hex(),
                len(ciphertext),
            )
            deliveries.append(
                {"peer": peer, "status": "transmitted", "cipher_len": len(ciphertext)}
            )
        return deliveries

    async def decrypt(self, ciphertext: bytes) -> dict:
        """Decrypt an inbound ciphertext frame. Used by peer relay nodes."""
        plaintext = self._fernet.decrypt(ciphertext)
        return json.loads(plaintext.decode())

    async def run(self, task: str = "", context: str = "", history: list = None) -> str:
        return json.dumps({"key": self._key.decode(), "peers": self._peers})
