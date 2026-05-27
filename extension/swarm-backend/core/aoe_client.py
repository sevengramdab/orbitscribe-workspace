"""Async HTTP client for the AOE supervisor.

Handles communication with the Rust AOE supervisor (or Python shim)
running on port 58082. Includes retry logic, health polling, and graceful
fallbacks when the supervisor is unavailable.
"""
import asyncio
import os
from typing import Optional

import httpx

SUPERVISOR_PORT = int(os.environ.get("AOE_PORT", "58082"))
SUPERVISOR_URL = f"http://127.0.0.1:{SUPERVISOR_PORT}"
DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 3
RETRY_DELAY = 1.0


class AOEClient:
    """Async client for the AOE supervisor HTTP API."""

    def __init__(self, base_url: str = SUPERVISOR_URL, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _client_ctx(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        json_body: Optional[dict] = None,
        retries: int = MAX_RETRIES,
    ) -> dict:
        url = f"{self.base_url}{path}"
        last_err = ""
        for attempt in range(retries):
            try:
                client = await self._client_ctx()
                if method.upper() == "GET":
                    resp = await client.get(url)
                else:
                    resp = await client.post(url, json=json_body)
                resp.raise_for_status()
                return resp.json()
            except httpx.ConnectError as e:
                last_err = f"Supervisor unreachable: {e}"
            except httpx.HTTPStatusError as e:
                # Some endpoints return 503 when Docker is down — still valid JSON
                try:
                    return e.response.json()
                except Exception:
                    last_err = f"HTTP {e.response.status_code}: {e.response.text}"
            except Exception as e:
                last_err = str(e)
            if attempt < retries - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        return {"success": False, "error": last_err}

    async def health(self) -> dict:
        """Get supervisor health. Returns dict with status, docker_available, version."""
        return await self._request("GET", "/health", retries=1)

    async def mesh_status(self) -> dict:
        return await self._request("GET", "/mesh/status")

    async def mesh_start(self, image: Optional[str] = None, memory_limit_mb: Optional[int] = None) -> dict:
        payload = {}
        if image:
            payload["image"] = image
        if memory_limit_mb:
            payload["memory_limit_mb"] = memory_limit_mb
        return await self._request("POST", "/mesh/start", json_body=payload or None)

    async def mesh_stop(self) -> dict:
        return await self._request("POST", "/mesh/stop")

    async def mesh_failsafe(self) -> dict:
        return await self._request("POST", "/mesh/failsafe")

    async def mesh_logs(self) -> dict:
        return await self._request("GET", "/mesh/logs")

    async def ensure_supervisor(self, max_wait: float = 15.0) -> bool:
        """Poll health until supervisor responds or timeout."""
        deadline = asyncio.get_event_loop().time() + max_wait
        while asyncio.get_event_loop().time() < deadline:
            result = await self.health()
            if isinstance(result, dict) and (result.get("status") in ("ok", "degraded") or result.get("docker_available") is not None):
                return True
            await asyncio.sleep(0.5)
        return False


# Singleton client for the application lifecycle
_default_client: Optional[AOEClient] = None


def get_aoe_client() -> AOEClient:
    global _default_client
    if _default_client is None:
        _default_client = AOEClient()
    return _default_client
