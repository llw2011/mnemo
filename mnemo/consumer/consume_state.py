"""Unified consume state I/O and migration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    """Return current UTC timestamp in ISO-Z format."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    """Read JSON object with safe fallback."""

    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
    if not isinstance(data, dict):
        return default
    return data


class UnifiedConsumeState:
    """Read/write unified consume state with migration helpers."""

    def __init__(self, workspace: Path) -> None:
        """Initialize with workspace path."""

        self.path = workspace / "state" / "unified_consume_state.json"

    def load(self) -> dict[str, Any]:
        """Load state file or return default structure."""

        return _read_json(self.path, {"version": "1.0", "blocks": {}, "updated_at": None})

    def save(self, state: dict[str, Any]) -> None:
        """Persist state atomically."""

        state["updated_at"] = utc_now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def update_block(self, block_id: str, injected_at: str, digest: str, consumed_ids: dict[str, Any] | None = None) -> None:
        """Update one block record and save."""

        state = self.load()
        blocks = state.setdefault("blocks", {})
        blocks[block_id] = {
            "block_id": block_id,
            "injected_at": injected_at,
            "hash": digest,
            "consumed_ids": consumed_ids or {},
            "version": "1.0",
        }
        self.save(state)

    def migrate_from_legacy(self, legacy_dir: Path) -> dict[str, Any]:
        """Migrate v1 legacy files into unified consume state.

        Legacy files:
        - preconscious_consumed.json
        - preconscious_inject_hash.json
        - snapshot_inject_hash.json
        """

        state = self.load()
        state["version"] = "1.0"
        blocks = state.setdefault("blocks", {})

        preconscious_consumed = _read_json(legacy_dir / "preconscious_consumed.json", {})
        preconscious_hash = _read_json(legacy_dir / "preconscious_inject_hash.json", {})
        snapshot_hash = _read_json(legacy_dir / "snapshot_inject_hash.json", {})

        pre_block = blocks.setdefault(
            "preconscious",
            {
                "block_id": "preconscious",
                "injected_at": None,
                "hash": None,
                "consumed_ids": {},
                "version": "1.0",
            },
        )

        consumed_ids: dict[str, dict[str, str | None]] = {}
        delivered = preconscious_consumed.get("delivered", {})
        if isinstance(delivered, dict):
            for item_id, at in delivered.items():
                consumed_ids[str(item_id)] = {"status": "injected", "at": str(at) if at is not None else None}

        pruned = preconscious_consumed.get("pruned", {})
        if isinstance(pruned, dict):
            for item_id, at in pruned.items():
                consumed_ids[str(item_id)] = {"status": "pruned", "at": str(at) if at is not None else None}

        pre_block["consumed_ids"] = consumed_ids
        if preconscious_hash.get("last_hash") is not None:
            pre_block["hash"] = preconscious_hash.get("last_hash")
        if preconscious_hash.get("last_injected_at") is not None:
            pre_block["injected_at"] = preconscious_hash.get("last_injected_at")
        pre_block["version"] = "1.0"

        snapshot_block = blocks.setdefault(
            "snapshot",
            {
                "block_id": "snapshot",
                "injected_at": None,
                "hash": None,
                "consumed_ids": {},
                "version": "1.0",
            },
        )
        if snapshot_hash.get("last_hash") is not None:
            snapshot_block["hash"] = snapshot_hash.get("last_hash")
        if snapshot_hash.get("updated_at") is not None:
            snapshot_block["injected_at"] = snapshot_hash.get("updated_at")
        snapshot_block["version"] = "1.0"

        self.save(state)
        return state
