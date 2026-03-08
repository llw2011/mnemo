"""Incremental fact scanner with watermark + gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def scan_facts(workspace: Path, dry_run: bool = True) -> dict[str, Any]:
    """Scan facts incrementally from JSONL source using watermark."""

    source = workspace / "memory" / "layer2" / "active" / "facts.jsonl"
    watermark_file = workspace / "state" / "fact_scanner_watermark.json"
    last_line = 0
    if watermark_file.exists():
        try:
            last_line = int(json.loads(watermark_file.read_text(encoding="utf-8")).get("line", 0))
        except (json.JSONDecodeError, ValueError, TypeError):
            last_line = 0

    if not source.exists():
        return {"new_items": 0, "watermark": last_line, "accepted": 0}

    lines = source.read_text(encoding="utf-8").splitlines()
    new = lines[last_line:]
    accepted = [ln for ln in new if ln.strip().startswith("{")]

    if not dry_run:
        watermark_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = watermark_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"line": len(lines)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(watermark_file)

    return {"new_items": len(new), "watermark": len(lines), "accepted": len(accepted)}
