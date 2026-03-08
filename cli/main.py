"""Mnemo CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mnemo.consumer.consume_state import UnifiedConsumeState
from mnemo.injector.unified_inject import run_inject
from mnemo.scanner.fact_scanner import scan_facts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")


def cmd_inject(args: argparse.Namespace) -> int:
    """Handle `mnemo inject` command."""

    result = run_inject(Path(args.workspace), dry_run=args.dry_run, mode=args.mode)
    print(result.model_dump_json(indent=2, ensure_ascii=False))
    if args.dry_run and result.diff:
        print(result.diff)
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    """Handle `mnemo scan` command."""

    out = scan_facts(Path(args.workspace), dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle `mnemo status` command."""

    state = UnifiedConsumeState(Path(args.workspace)).load()
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    """Handle `mnemo rollback` command."""

    ws = Path(args.workspace)
    shadow = ws / "MEMORY.shadow.md"
    memory = ws / "MEMORY.md"
    if shadow.exists():
        data = shadow.read_text(encoding="utf-8")
        tmp = memory.with_suffix(".md.tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(memory)
        print("rollback_done")
    else:
        print("no_shadow_file")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for Mnemo commands."""

    parser = argparse.ArgumentParser(prog="mnemo", description="Mnemo unified memory toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inject = sub.add_parser("inject")
    p_inject.add_argument("--dry-run", action="store_true")
    p_inject.add_argument("--mode", choices=["readonly", "dualwrite", "primary"], default="primary")
    p_inject.add_argument("--workspace", default=str(Path(__file__).resolve().parent.parent))
    p_inject.set_defaults(func=cmd_inject)

    p_scan = sub.add_parser("scan")
    p_scan.add_argument("--dry-run", action="store_true")
    p_scan.add_argument("--workspace", default=str(Path(__file__).resolve().parent.parent))
    p_scan.set_defaults(func=cmd_scan)

    p_status = sub.add_parser("status")
    p_status.add_argument("--workspace", default=str(Path(__file__).resolve().parent.parent))
    p_status.set_defaults(func=cmd_status)

    p_rollback = sub.add_parser("rollback")
    p_rollback.add_argument("--workspace", default=str(Path(__file__).resolve().parent.parent))
    p_rollback.set_defaults(func=cmd_rollback)

    return parser


def main() -> int:
    """Run command-line interface."""

    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
