"""HTTP client for talking to a SimplePod peer."""
import base64
import time
from typing import Optional, Dict, Any

import requests

from config import API_TOKEN


class PeerClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._headers = {"X-Token": API_TOKEN}

    def _request(self, method: str, path: str, json_data=None, extra_timeout=0) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_err = ""
        for attempt in range(3):
            try:
                if method == "GET":
                    r = requests.get(url, headers=self._headers, timeout=self.timeout + extra_timeout)
                else:
                    r = requests.post(url, headers=self._headers, json=json_data, timeout=self.timeout + extra_timeout)
                r.raise_for_status()
                return r.json()
            except requests.exceptions.ConnectionError as e:
                last_err = str(e)
            except requests.exceptions.Timeout:
                last_err = "Timeout"
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
        raise requests.exceptions.ConnectionError(f"Peer unreachable after 3 attempts: {last_err}")

    def ping(self) -> Dict[str, Any]:
        return self._request("POST", "/ping")

    def exec(self, command: str, cwd: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
        return self._request("POST", "/exec", {"command": command, "cwd": cwd, "timeout": timeout}, extra_timeout=timeout)

    def status(self) -> Dict[str, Any]:
        return self._request("POST", "/status")

    def setup(self, script: str, description: str = "") -> Dict[str, Any]:
        return self._request("POST", "/setup", {"script": script, "description": description}, extra_timeout=90)

    def sync_file(self, filename: str, content_bytes: bytes) -> Dict[str, Any]:
        return self._request("POST", "/sync", {
            "filename": filename,
            "content": base64.b64encode(content_bytes).decode()
        })

    def is_alive(self) -> bool:
        try:
            self.ping()
            return True
        except Exception:
            return False

    def health(self) -> Dict[str, Any]:
        start = time.time()
        result = self._request("GET", "/health")
        result["latency_ms"] = round((time.time() - start) * 1000, 1)
        return result

    def screenshot(self) -> Dict[str, Any]:
        return self._request("POST", "/screenshot")

    def list_files(self, path: str = ".") -> Dict[str, Any]:
        return self._request("POST", "/files/list", {"path": path})

    def download_file(self, path: str) -> Dict[str, Any]:
        result = self._request("POST", "/files/download", {"path": path})
        if "content_b64" in result:
            result["content_bytes"] = base64.b64decode(result["content_b64"])
        return result

    def delete_file(self, path: str) -> Dict[str, Any]:
        return self._request("POST", "/files/delete", {"path": path})
