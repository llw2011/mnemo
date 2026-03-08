"""Mem0 adapter stub for downstream integration."""

from __future__ import annotations

from typing import Any


class Mem0Adapter:
    """Stub adapter for Mem0 operations."""

    def search(self, query: str) -> list[dict[str, Any]]:
        """Return empty search result placeholder."""

        _ = query
        return []

    def write(self, payload: dict[str, Any]) -> bool:
        """Pretend to write payload and return success."""

        _ = payload
        return True
