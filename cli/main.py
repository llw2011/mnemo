"""Mnemo CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_DEFAULT = str(ROOT.parent)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mnemo.consumer.consume_state import UnifiedConsumeState
from mnemo.injector.unified_inject import run_inject

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
logger = logging.getLogger(__name__)


def _write_stdout(payload: str) -> None:
    """Write text to stdout without using print."""

    sys.stdout.write(payload + "\n")


def _read_jsonl_count(path: Path) -> int:
    """Count valid data lines in a JSONL file."""

    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text and not text.startswith("#"):
            count += 1
    return count


def _run_external(command: list[str], cwd: Path) -> dict[str, Any]:
    """Run external command and return structured result."""

    proc = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    return {
        "command": command,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def cmd_inject(args: argparse.Namespace) -> int:
    """Handle `mnemo inject` command."""

    result = run_inject(Path(args.workspace), dry_run=args.dry_run, mode=args.mode)
    _write_stdout(result.model_dump_json(indent=2, ensure_ascii=False))
    if args.dry_run and result.diff:
        _write_stdout(result.diff)
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    """Handle `mnemo scan` command via tools/preconscious_scan.py."""

    workspace = Path(args.workspace)
    script = workspace / "tools" / "preconscious_scan.py"
    command = [sys.executable, str(script), "--workspace", str(workspace)]
    if args.dry_run:
        command.append("--dry-run")

    result = _run_external(command, cwd=workspace)
    _write_stdout(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["returncode"])


def cmd_status(args: argparse.Namespace) -> int:
    """Handle `mnemo status` command."""

    workspace = Path(args.workspace)
    consume_state = UnifiedConsumeState(workspace).load()
    buffer_count = _read_jsonl_count(workspace / "memory" / "preconscious" / "buffer.jsonl")
    urgent_count = _read_jsonl_count(workspace / "memory" / "urgent-lane" / "queue.jsonl")
    snapshot_count = len((workspace / "memory" / "layer1" / "snapshot.md").read_text(encoding="utf-8").splitlines()) if (workspace / "memory" / "layer1" / "snapshot.md").exists() else 0

    blocks = consume_state.get("blocks", {}) if isinstance(consume_state, dict) else {}
    last_injected_at = None
    if isinstance(blocks, dict):
        for block in blocks.values():
            if isinstance(block, dict):
                ts = block.get("injected_at")
                if isinstance(ts, str) and ts:
                    if last_injected_at is None or ts > last_injected_at:
                        last_injected_at = ts

    payload = {
        "counts": {
            "buffer": buffer_count,
            "urgent": urgent_count,
            "snapshot_lines": snapshot_count,
        },
        "last_injected_at": last_injected_at,
        "state_file": str(workspace / "state" / "unified_consume_state.json"),
    }
    _write_stdout(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    """Handle `mnemo rollback` command via tools/preconscious_rollback.sh."""

    workspace = Path(args.workspace)
    script = workspace / "tools" / "preconscious_rollback.sh"
    command = ["bash", str(script), str(workspace)]
    result = _run_external(command, cwd=workspace)
    _write_stdout(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["returncode"])


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for Mnemo commands."""

    parser = argparse.ArgumentParser(prog="mnemo", description="Mnemo unified memory toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inject = sub.add_parser("inject")
    p_inject.add_argument("--dry-run", action="store_true")
    p_inject.add_argument("--mode", choices=["readonly", "dualwrite", "primary"], default="primary")
    p_inject.add_argument("--workspace", default=WORKSPACE_DEFAULT)
    p_inject.set_defaults(func=cmd_inject)

    p_scan = sub.add_parser("scan")
    p_scan.add_argument("--dry-run", action="store_true")
    p_scan.add_argument("--workspace", default=WORKSPACE_DEFAULT)
    p_scan.set_defaults(func=cmd_scan)

    p_status = sub.add_parser("status")
    p_status.add_argument("--workspace", default=WORKSPACE_DEFAULT)
    p_status.set_defaults(func=cmd_status)

    p_rollback = sub.add_parser("rollback")
    p_rollback.add_argument("--workspace", default=WORKSPACE_DEFAULT)
    p_rollback.set_defaults(func=cmd_rollback)

    return parser


def main() -> int:
    """Run command-line interface."""

    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
