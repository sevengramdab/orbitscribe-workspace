"""
gumroad_client.py
=================
Gumroad API v2 client for the Money Engine.

Provides real product listing, sales tracking, and revenue fetching.
Falls back to mock mode if no GUMROAD_ACCESS_TOKEN is configured.

Get your token from: https://gumroad.com/settings/advanced#api
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional

GUMROAD_API_BASE = "https://api.gumroad.com/v2"


class GumroadClient:
    """
    Lightweight Gumroad API client using only stdlib (urllib).
    """

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.environ.get("GUMROAD_ACCESS_TOKEN", "")
        self._cache: Dict[str, tuple] = {}  # endpoint -> (timestamp, data)
        self._cache_ttl = 30.0  # seconds

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def has_credentials(self) -> bool:
        return bool(self.access_token)

    def _auth_headers(self) -> Dict[str, str]:
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

    def _request(
        self,
        method: str,
        endpoint: str,
        body: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the Gumroad API."""
        url = f"{GUMROAD_API_BASE}{endpoint}"

        # Cache read
        if use_cache and method == "GET" and endpoint in self._cache:
            ts, data = self._cache[endpoint]
            if time.time() - ts < self._cache_ttl:
                return data

        headers = self._auth_headers()
        headers.setdefault("Accept", "application/json")

        data_bytes = None
        if body is not None:
            data_bytes = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data_bytes, method=method, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8") if exc.readable() else ""
            return {"success": False, "error": f"HTTP {exc.code}", "details": error_body}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

        # Cache write
        if use_cache and method == "GET":
            self._cache[endpoint] = (time.time(), data)

        return data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_products(self) -> List[Dict[str, Any]]:
        """Return all Gumroad products."""
        if not self.has_credentials():
            return self._mock_products()
        resp = self._request("GET", "/products", use_cache=True)
        return resp.get("products", [])

    def create_product(
        self,
        name: str,
        price: float,
        description: str = "",
        file_url: Optional[str] = None,
        custom_receipt: str = "",
    ) -> Dict[str, Any]:
        """Create a new digital product on Gumroad."""
        if not self.has_credentials():
            return {
                "success": True,
                "mock": True,
                "product": {"id": f"mock_{int(time.time())}", "name": name, "price": price},
                "message": "No GUMROAD_ACCESS_TOKEN set. Running in mock mode.",
            }

        payload: Dict[str, Any] = {
            "name": name,
            "price": price,
            "description": description,
            "custom_receipt": custom_receipt or "Thanks for your purchase!",
        }
        if file_url:
            payload["file_url"] = file_url

        return self._request("POST", "/products", body=payload)

    def get_sales(self, after_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return sales transactions."""
        if not self.has_credentials():
            return self._mock_sales()
        endpoint = "/sales"
        if after_date:
            endpoint += f"?after={after_date}"
        resp = self._request("GET", endpoint, use_cache=True)
        return resp.get("sales", [])

    def get_revenue_summary(self) -> Dict[str, float]:
        """Compute total revenue and units sold from live sales data."""
        sales = self.get_sales()
        total = 0.0
        for s in sales:
            price = s.get("price", 0)
            if isinstance(price, str):
                price = float(price)
            total += price
        return {"revenue": round(total, 2), "units": len(sales)}

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single product by ID."""
        if not self.has_credentials():
            return None
        resp = self._request("GET", f"/products/{product_id}", use_cache=True)
        return resp.get("product")

    # ------------------------------------------------------------------
    # Mock fallbacks
    # ------------------------------------------------------------------

    def _mock_products(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "mock_prod_1",
                "name": "Passive Income Guide",
                "price": 999,
                "url": "https://gumroad.com/l/mock",
                "published": True,
            },
            {
                "id": "mock_prod_2",
                "name": "Notion Workspace Template",
                "price": 1499,
                "url": "https://gumroad.com/l/mock2",
                "published": True,
            },
        ]

    def _mock_sales(self) -> List[Dict[str, Any]]:
        return [
            {"id": "sale_1", "product_name": "Passive Income Guide", "price": 9.99, "created_at": "2026-05-26"},
            {"id": "sale_2", "product_name": "Notion Workspace Template", "price": 14.99, "created_at": "2026-05-27"},
        ]


# Singleton accessor
def get_gumroad_client() -> GumroadClient:
    return GumroadClient()
