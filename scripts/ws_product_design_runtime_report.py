#!/usr/bin/env python3
"""Dry-run Product Lane Open Design runtime report CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_design_adapter import validate_design_tool
from product_design_runtime_probe import (
    probe_design_runtime,
    render_design_runtime_report,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show a read-only Open Design runtime visibility report (dry-run only)."
    )
    parser.add_argument("--tool", help="Design adapter tool id (open-design in this slice).")
    parser.add_argument("--dry-run", action="store_true", help="Report only; no writes and no execution.")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve()

    if not args.tool or not str(args.tool).strip():
        print("ERROR: --tool <tool> is required.", file=sys.stderr)
        return 2
    if not args.dry_run:
        print("ERROR: --dry-run is required. Runtime report is preview-only.", file=sys.stderr)
        return 2

    try:
        tool = validate_design_tool(str(args.tool).strip())
        probe = probe_design_runtime(root, tool)
        print(render_design_runtime_report(probe).rstrip())
        return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
