#!/usr/bin/env python3
"""One-shot migration tool from v1 legacy state to unified state."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mnemo.consumer.consume_state import UnifiedConsumeState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
logger = logging.getLogger(__name__)


LEGACY_FILES = [
    "preconscious_consumed.json",
    "preconscious_inject_hash.json",
    "snapshot_inject_hash.json",
]


def _atomic_write(path: Path, content: str) -> None:
    """Write file atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _backup_legacy_files(legacy_dir: Path) -> list[str]:
    """Backup legacy files to *.bak.migrate."""

    backed_up: list[str] = []
    for name in LEGACY_FILES:
        src = legacy_dir / name
        if not src.exists():
            continue
        dst = legacy_dir / f"{name}.bak.migrate"
        shutil.copy2(src, dst)
        backed_up.append(str(dst))
    return backed_up


def _validate_state(state: dict[str, Any]) -> list[str]:
    """Validate migrated state and return issues."""

    issues: list[str] = []
    if state.get("version") != "1.0":
        issues.append("version is not 1.0")
    blocks = state.get("blocks")
    if not isinstance(blocks, dict):
        issues.append("blocks missing or invalid")
        return issues
    for block_id in ("preconscious", "snapshot"):
        if block_id not in blocks:
            issues.append(f"missing block: {block_id}")
    return issues


def run_migration(workspace: Path) -> dict[str, Any]:
    """Execute backup, migration, validation, and report generation."""

    legacy_dir = workspace / "memory" / "state"
    consume = UnifiedConsumeState(workspace)

    backed_up = _backup_legacy_files(legacy_dir)
    migrated = consume.migrate_from_legacy(legacy_dir)
    issues = _validate_state(migrated)

    report = {
        "workspace": str(workspace),
        "legacy_dir": str(legacy_dir),
        "backed_up_files": backed_up,
        "state_file": str(workspace / "state" / "unified_consume_state.json"),
        "validation_ok": len(issues) == 0,
        "issues": issues,
        "migrated_blocks": sorted(list((migrated.get("blocks") or {}).keys())),
    }
    _atomic_write(workspace / "state" / "migration_report.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""

    parser = argparse.ArgumentParser(description="Migrate v1 legacy state into unified_consume_state.json")
    parser.add_argument("--workspace", default=str(ROOT.parent))
    return parser


def main() -> int:
    """Main entrypoint."""

    args = build_parser().parse_args()
    report = run_migration(Path(args.workspace))
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0 if report.get("validation_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
