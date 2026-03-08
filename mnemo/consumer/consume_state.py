"""Unified consume state I/O and migration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    """Return current UTC timestamp in ISO-Z format."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class UnifiedConsumeState:
    """Read/write unified consume state with migration helpers."""

    def __init__(self, workspace: Path) -> None:
        """Initialize with workspace path."""

        self.path = workspace / "state" / "unified_consume_state.json"

    def load(self) -> dict[str, Any]:
        """Load state file or return default structure."""

        if not self.path.exists():
            return {"version": "1.0", "blocks": {}, "updated_at": None}
        return json.loads(self.path.read_text(encoding="utf-8"))

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
        """Migrate legacy consumed/hash files into unified state format."""

        state = self.load()
        blocks = state.setdefault("blocks", {})

        preconscious = legacy_dir / "preconscious_consumed.json"
        if preconscious.exists():
            pdata = json.loads(preconscious.read_text(encoding="utf-8"))
            consumed: dict[str, Any] = {}
            for item_id, at in (pdata.get("delivered") or {}).items():
                consumed[item_id] = {"status": "injected", "at": at}
            for item_id, at in (pdata.get("pruned") or {}).items():
                consumed[item_id] = {"status": "pruned", "at": at}
            blocks.setdefault("preconscious", {})["consumed_ids"] = consumed

        p_hash = legacy_dir / "preconscious_inject_hash.json"
        if p_hash.exists():
            pdata = json.loads(p_hash.read_text(encoding="utf-8"))
            blocks.setdefault("preconscious", {}).update(
                {
                    "block_id": "preconscious",
                    "hash": pdata.get("last_hash"),
                    "injected_at": pdata.get("last_injected_at"),
                    "version": "1.0",
                }
            )

        s_hash = legacy_dir / "snapshot_inject_hash.json"
        if s_hash.exists():
            sdata = json.loads(s_hash.read_text(encoding="utf-8"))
            blocks.setdefault("snapshot", {}).update(
                {
                    "block_id": "snapshot",
                    "hash": sdata.get("last_hash"),
                    "injected_at": sdata.get("updated_at"),
                    "consumed_ids": blocks.get("snapshot", {}).get("consumed_ids", {}),
                    "version": "1.0",
                }
            )

        self.save(state)
        return state
