"""Block builder and marker normalization."""

from __future__ import annotations

from mnemo.models import Block

UNIFIED_MARKER = "[UNIFIED_MEMORY_BLOCK_V1_DO_NOT_CAPTURE]"


def block_tags(block_id: str) -> tuple[str, str]:
    """Return unified start/end tags for a block id."""

    return (f"<!-- UNIFIED_BLOCK:{block_id}:START -->", f"<!-- UNIFIED_BLOCK:{block_id}:END -->")


def render_block(block: Block) -> str:
    """Render one block with normalized marker and tags."""

    start, end = block_tags(block.block_id)
    body = f"{UNIFIED_MARKER}\n{block.content.strip()}"
    return f"{start}\n{body}\n{end}"


def build_block(block_id: str, content: str, priority: int = 0, item_ids: list[str] | None = None) -> Block:
    """Build a normalized block object."""

    return Block(block_id=block_id, priority=priority, marker=UNIFIED_MARKER, content=content, item_ids=item_ids or [])
