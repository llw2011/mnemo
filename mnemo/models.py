"""Data models for Mnemo."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(slots=True)
class Block:
    """A normalized memory block for injection."""

    block_id: str
    priority: int = 0
    marker: str = "[UNIFIED_MEMORY_BLOCK_V1_DO_NOT_CAPTURE]"
    content: str = ""
    item_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConsumeRecord:
    """A consume-state record for one block."""

    block_id: str
    injected_at: str | None = None
    hash: str | None = None
    consumed_ids: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass(slots=True)
class InjectResult:
    """Result of a unified inject run."""

    mode: Literal["readonly", "dualwrite", "primary"]
    changed_blocks: list[str] = field(default_factory=list)
    skipped_blocks: list[str] = field(default_factory=list)
    wrote_memory: bool = False
    diff: str = ""

    def model_dump_json(self, indent: int = 2, ensure_ascii: bool = False) -> str:
        """Serialize model to JSON string."""

        return json.dumps(asdict(self), indent=indent, ensure_ascii=ensure_ascii)


@dataclass(slots=True)
class ScanItem:
    """Fact scanner item with score and metadata."""

    item_id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
