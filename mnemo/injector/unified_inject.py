"""Unified injector main logic."""

from __future__ import annotations

import difflib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mnemo.config import load_config
from mnemo.consumer.consume_state import UnifiedConsumeState
from mnemo.injector.block_builder import build_block, render_block
from mnemo.injector.hash_debounce import HashDebounceStore, canonicalize, compute_hash
from mnemo.models import InjectResult

logger = logging.getLogger(__name__)


def utc_now() -> str:
    """Return current UTC timestamp."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    """Read UTF-8 text or empty string when missing."""

    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _atomic_write(path: Path, content: str) -> None:
    """Write file atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _replace_or_append(content: str, block_id: str, rendered: str) -> str:
    """Replace existing block by marker or append at end."""

    start = f"<!-- UNIFIED_BLOCK:{block_id}:START -->"
    end = f"<!-- UNIFIED_BLOCK:{block_id}:END -->"
    if start in content and end in content:
        pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
        return pattern.sub(rendered, content)
    sep = "\n" if content.endswith("\n") or not content else "\n\n"
    return f"{content}{sep}{rendered}\n" if content else f"{rendered}\n"


def _collect_sources(workspace: Path) -> dict[str, str]:
    """Collect source content for urgent, preconscious, snapshot blocks."""

    snapshot = _read_text(workspace / "memory" / "layer1" / "snapshot.md").strip() or "（暂无 snapshot）"

    urgent_rows = _read_text(workspace / "memory" / "urgent-lane" / "queue.jsonl").splitlines()
    urgent_ids: list[str] = []
    for line in urgent_rows:
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and obj.get("id"):
                urgent_ids.append(str(obj["id"]))
        except json.JSONDecodeError:
            continue
    urgent = "\n".join([f"- {x}" for x in urgent_ids[:3]]) if urgent_ids else "- （暂无紧急条目）"

    pre_rows = _read_text(workspace / "memory" / "preconscious" / "buffer.jsonl").splitlines()
    pre_ids: list[str] = []
    for line in pre_rows:
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and obj.get("id"):
                pre_ids.append(str(obj["id"]))
        except json.JSONDecodeError:
            continue
    pre = "\n".join([f"- {x}" for x in pre_ids[:8]]) if pre_ids else "- （暂无预意识条目）"

    return {"urgent": urgent, "preconscious": pre, "snapshot": snapshot}


def run_inject(workspace: Path, dry_run: bool = False, mode: str = "primary") -> InjectResult:
    """Run unified inject with mode control and hash debounce."""

    config = load_config(workspace)
    priority = config.priority or ["urgent", "preconscious", "snapshot"]
    memory_path = workspace / "MEMORY.md"
    content_before = _read_text(memory_path)
    content_after = content_before

    hash_store = HashDebounceStore(workspace)
    consume_state = UnifiedConsumeState(workspace)
    sources = _collect_sources(workspace)

    changed_blocks: list[str] = []
    skipped_blocks: list[str] = []

    for idx, block_id in enumerate(priority):
        body = sources.get(block_id, "")
        block = build_block(block_id=block_id, content=body, priority=idx)
        rendered = render_block(block)
        normalized = canonicalize({"block_id": block_id, "text": rendered})
        digest = compute_hash(json.dumps(normalized, ensure_ascii=False, sort_keys=True))

        old_hash = hash_store.get_hash(block_id)
        if old_hash == digest:
            skipped_blocks.append(block_id)
            continue

        changed_blocks.append(block_id)
        content_after = _replace_or_append(content_after, block_id, rendered)
        if (not dry_run) and mode != "readonly":
            hash_store.set_hash(block_id, digest, utc_now(), item_ids=block.item_ids)
            consume_state.update_block(block_id, utc_now(), digest, consumed_ids={})

    diff = "\n".join(
        difflib.unified_diff(
            content_before.splitlines(),
            content_after.splitlines(),
            fromfile="MEMORY.md(before)",
            tofile="MEMORY.md(after)",
            lineterm="",
        )
    )

    should_write = (not dry_run) and mode in {"primary", "dualwrite"} and content_after != content_before
    if should_write:
        _atomic_write(memory_path, content_after)
    if (not dry_run) and mode == "dualwrite":
        _atomic_write(workspace / "MEMORY.shadow.md", content_after)

    logger.info("inject finished mode=%s changed=%s skipped=%s", mode, changed_blocks, skipped_blocks)
    return InjectResult(
        mode=mode, changed_blocks=changed_blocks, skipped_blocks=skipped_blocks, wrote_memory=should_write, diff=diff
    )
