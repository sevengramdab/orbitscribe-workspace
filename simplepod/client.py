"""HTTP client for talking to a SimplePod peer."""
import base64
import time
from typing import Optional, Dict, Any

import requests

from config import API_TOKEN


class PeerClient:
    """Client for sending control commands to a remote SimplePod peer."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._headers = {"X-Token": API_TOKEN}

    def ping(self) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/ping", headers=self._headers, timeout=self.timeout)
        return r.json()

    def exec(self, command: str, cwd: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/exec",
            headers=self._headers,
            json={"command": command, "cwd": cwd, "timeout": timeout},
            timeout=max(timeout + 5, int(self.timeout)),
        )
        return r.json()

    def status(self) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/status", headers=self._headers, timeout=self.timeout)
        return r.json()

    def setup(self, script: str, description: str = "") -> Dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/setup",
            headers=self._headers,
            json={"script": script, "description": description},
            timeout=120,
        )
        return r.json()

    def sync_file(self, filename: str, content_bytes: bytes) -> Dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/sync",
            headers=self._headers,
            json={"filename": filename, "content": base64.b64encode(content_bytes).decode()},
            timeout=self.timeout,
        )
        return r.json()

    def is_alive(self) -> bool:
        try:
            self.ping()
            return True
        except Exception:
            return False
