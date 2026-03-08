"""Hash debounce helpers for unified injection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

DYNAMIC_KEYS = {"timestamp", "ts", "updated_at", "generated_at", "delivered_at", "injected_at"}


def canonicalize(obj: Any) -> Any:
    """Recursively canonicalize objects by removing dynamic fields and sorting keys."""

    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for key in sorted(obj.keys()):
            if key in DYNAMIC_KEYS:
                continue
            cleaned[key] = canonicalize(obj[key])
        return cleaned
    if isinstance(obj, list):
        return [canonicalize(x) for x in obj]
    return obj


def compute_hash(text: str) -> str:
    """Compute SHA256 hex digest for text."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class HashDebounceStore:
    """Persistent hash store keyed by block_id."""

    def __init__(self, workspace: Path) -> None:
        """Initialize with workspace root path."""

        self.path = workspace / "state" / "unified_inject_hash.json"

    def load(self) -> dict[str, Any]:
        """Load hash store; return empty default on missing file."""

        if not self.path.exists():
            return {"version": "1.0", "blocks": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def get_hash(self, block_id: str) -> str | None:
        """Get saved hash for a block."""

        store = self.load()
        return (store.get("blocks", {}).get(block_id) or {}).get("hash")

    def set_hash(self, block_id: str, digest: str, injected_at: str, item_ids: list[str] | None = None) -> None:
        """Set hash metadata for a block and persist atomically."""

        store = self.load()
        blocks = store.setdefault("blocks", {})
        blocks[block_id] = {
            "hash": digest,
            "injected_at": injected_at,
            "item_ids": item_ids or [],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.path)
