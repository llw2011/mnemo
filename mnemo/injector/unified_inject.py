"""Unified injector main logic for Plan B integration."""

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
from mnemo.injector.hash_debounce import HashDebounceStore, canonicalize, compute_hash
from mnemo.models import InjectResult

logger = logging.getLogger(__name__)

MNEMO_START = "<!-- MNEMO_START -->"
MNEMO_END = "<!-- MNEMO_END -->"
UNIFIED_MARKER = "[UNIFIED_MEMORY_BLOCK_V1_DO_NOT_CAPTURE]"


def utc_now() -> str:
    """Return current UTC timestamp."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    """Read UTF-8 text or empty string when missing."""

    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _atomic_write(path: Path, content: str) -> None:
    """Write file atomically via .tmp then rename."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL file into a list of dict rows."""

    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _item_id(row: dict[str, Any], fallback: str) -> str:
    """Resolve item id from row with fallback."""

    raw = row.get("id") or row.get("item_id") or fallback
    return str(raw)


def _item_text(row: dict[str, Any], item_id: str) -> str:
    """Build display text for one lane item."""

    score = row.get("score")
    content = str(row.get("content") or row.get("text") or "").strip()
    if score is None:
        return f"- ({item_id}) {content}" if content else f"- ({item_id})"
    try:
        score_text = f"{float(score):.3f}"
    except (TypeError, ValueError):
        score_text = str(score)
    if content:
        return f"- ({item_id}) [score={score_text}] {content}"
    return f"- ({item_id}) [score={score_text}]"


def _collect_lanes(workspace: Path) -> dict[str, Any]:
    """Collect lane data from urgent/main/snapshot sources."""

    urgent_rows = _read_jsonl(workspace / "memory" / "urgent-lane" / "queue.jsonl")
    pre_rows = _read_jsonl(workspace / "memory" / "preconscious" / "buffer.jsonl")
    snapshot = _read_text(workspace / "memory" / "layer1" / "snapshot.md").strip()

    seen_ids: set[str] = set()
    urgent_lines: list[str] = []
    pre_lines: list[str] = []
    urgent_ids: list[str] = []
    pre_ids: list[str] = []

    for index, row in enumerate(urgent_rows, start=1):
        item_id = _item_id(row, f"urgent_{index}")
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        urgent_ids.append(item_id)
        urgent_lines.append(_item_text(row, item_id))

    for index, row in enumerate(pre_rows, start=1):
        item_id = _item_id(row, f"preconscious_{index}")
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        pre_ids.append(item_id)
        pre_lines.append(_item_text(row, item_id))

    if not urgent_lines:
        urgent_lines.append("- （暂无紧急条目）")
    if not pre_lines:
        pre_lines.append("- （暂无预意识条目）")
    if not snapshot:
        snapshot = "（暂无 snapshot）"

    return {
        "urgent_lines": urgent_lines,
        "pre_lines": pre_lines,
        "snapshot": snapshot,
        "urgent_ids": urgent_ids,
        "pre_ids": pre_ids,
    }


def _render_unified_block(collected: dict[str, Any], injected_at: str) -> str:
    """Render unified MNEMO block content by lane priority."""

    lines: list[str] = [
        UNIFIED_MARKER,
        f"generated_at: {injected_at}",
        "## URGENT_LANE",
        *collected["urgent_lines"],
        "",
        "## PRECONSCIOUS_LANE",
        *collected["pre_lines"],
        "",
        "## SNAPSHOT_LANE",
        collected["snapshot"],
    ]
    return "\n".join(lines).strip()


def _replace_or_append_unified_section(memory_content: str, section: str) -> str:
    """Replace existing MNEMO section or append a new one."""

    block = f"{MNEMO_START}\n{section}\n{MNEMO_END}"
    if MNEMO_START in memory_content and MNEMO_END in memory_content:
        pattern = re.compile(re.escape(MNEMO_START) + r".*?" + re.escape(MNEMO_END), re.DOTALL)
        return pattern.sub(block, memory_content)

    separator = "\n" if not memory_content or memory_content.endswith("\n") else "\n\n"
    if not memory_content:
        return block + "\n"
    return f"{memory_content}{separator}{block}\n"


def run_inject(workspace: Path, dry_run: bool = False, mode: str = "primary") -> InjectResult:
    """Run unified injection with hash debounce and consume-state writeback."""

    config = load_config(workspace)
    effective_mode = mode or config.inject.mode

    memory_path = workspace / "MEMORY.md"
    content_before = _read_text(memory_path)
    injected_at = utc_now()
    collected = _collect_lanes(workspace)
    section = _render_unified_block(collected, injected_at)

    hash_store = HashDebounceStore(workspace)
    consume_state = UnifiedConsumeState(workspace)

    normalized = canonicalize({"block_id": "mnemo", "content": section})
    digest = compute_hash(json.dumps(normalized, ensure_ascii=False, sort_keys=True))
    old_hash = hash_store.get_hash("mnemo")

    if old_hash == digest:
        logger.info("inject skipped by hash debounce")
        return InjectResult(
            mode=effective_mode,
            changed_blocks=[],
            skipped_blocks=["mnemo"],
            wrote_memory=False,
            diff="",
        )

    content_after = _replace_or_append_unified_section(content_before, section)
    diff = "\n".join(
        difflib.unified_diff(
            content_before.splitlines(),
            content_after.splitlines(),
            fromfile="MEMORY.md(before)",
            tofile="MEMORY.md(after)",
            lineterm="",
        )
    )

    should_write_primary = (not dry_run) and effective_mode in {"primary", "dualwrite"}
    wrote_memory = False
    if should_write_primary and content_after != content_before:
        _atomic_write(memory_path, content_after)
        wrote_memory = True

    if (not dry_run) and effective_mode == "dualwrite":
        _atomic_write(workspace / "MEMORY.shadow.md", content_after)

    if (not dry_run) and effective_mode != "readonly":
        item_ids = collected["urgent_ids"] + collected["pre_ids"]
        hash_store.set_hash("mnemo", digest, injected_at, item_ids=item_ids)
        consumed_ids = {
            item_id: {"status": "injected", "at": injected_at}
            for item_id in item_ids
        }
        consume_state.update_block("mnemo", injected_at, digest, consumed_ids=consumed_ids)

    logger.info("inject finished mode=%s wrote_memory=%s", effective_mode, wrote_memory)
    return InjectResult(
        mode=effective_mode,
        changed_blocks=["mnemo"],
        skipped_blocks=[],
        wrote_memory=wrote_memory,
        diff=diff,
    )
