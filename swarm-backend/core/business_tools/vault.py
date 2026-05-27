"""
Unified Business Vault
All business agents persist their data here: products, leads, transactions,
campaigns, assets, pricing history, etc.
"""

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional


VAULT_PATH = os.path.join("tools", "saved_sessions", "unified_business_vault.json")
_lock = threading.RLock()


class UnifiedVault:
    """Thread-safe JSON vault for all business data."""

    def __init__(self, path: str = VAULT_PATH):
        self.path = path
        self._data: Dict[str, Any] = {"created_at": datetime.utcnow().isoformat(), "collections": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str)

    # ── Generic CRUD ──────────────────────────────────────────────────────

    def insert(self, collection: str, doc: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        with _lock:
            if collection not in self._data["collections"]:
                self._data["collections"][collection] = {}
            _id = doc_id or str(datetime.utcnow().timestamp())
            doc["_id"] = _id
            doc["_updated_at"] = datetime.utcnow().isoformat()
            self._data["collections"][collection][_id] = doc
            self._save()
            return _id

    def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        with _lock:
            return self._data.get("collections", {}).get(collection, {}).get(doc_id)

    def find(self, collection: str, filter_fn=None, limit: int = 100) -> List[Dict[str, Any]]:
        with _lock:
            docs = list(self._data.get("collections", {}).get(collection, {}).values())
            if filter_fn:
                docs = [d for d in docs if filter_fn(d)]
            return docs[:limit]

    def update(self, collection: str, doc_id: str, updates: Dict[str, Any]) -> bool:
        with _lock:
            coll = self._data.get("collections", {}).get(collection, {})
            if doc_id not in coll:
                return False
            coll[doc_id].update(updates)
            coll[doc_id]["_updated_at"] = datetime.utcnow().isoformat()
            self._save()
            return True

    def delete(self, collection: str, doc_id: str) -> bool:
        with _lock:
            coll = self._data.get("collections", {}).get(collection, {})
            if doc_id in coll:
                del coll[doc_id]
                self._save()
                return True
            return False

    def count(self, collection: str) -> int:
        with _lock:
            return len(self._data.get("collections", {}).get(collection, {}))

    def collections(self) -> List[str]:
        with _lock:
            return list(self._data.get("collections", {}).keys())

    def summary(self) -> Dict[str, int]:
        with _lock:
            return {c: len(v) for c, v in self._data.get("collections", {}).items()}

    def export_collection(self, collection: str) -> List[Dict[str, Any]]:
        with _lock:
            return list(self._data.get("collections", {}).get(collection, {}).values())

    def import_collection(self, collection: str, docs: List[Dict[str, Any]]):
        with _lock:
            if collection not in self._data["collections"]:
                self._data["collections"][collection] = {}
            for doc in docs:
                _id = doc.get("_id") or str(datetime.utcnow().timestamp())
                doc["_id"] = _id
                self._data["collections"][collection][_id] = doc
            self._save()


# Global vault instance
vault = UnifiedVault()
