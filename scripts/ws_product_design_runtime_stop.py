#!/usr/bin/env python3
"""Dry-run or confirm Open Design managed runtime stop."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_design_adapter import validate_design_tool
from product_design_managed_runtime import (
    build_managed_runtime_plan,
    execute_managed_runtime_stop,
    render_managed_runtime_plan,
    render_managed_runtime_result,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or stop Open Design managed runtime through pnpm tools-dev."
    )
    parser.add_argument("--tool", help="Design adapter tool id (open-design in this slice).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Preview only; no writes and no runtime stop.")
    group.add_argument("--confirm", action="store_true", help="Stop managed runtime and write local capture metadata.")
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

    try:
        tool = validate_design_tool(str(args.tool).strip())
        if args.dry_run:
            plan = build_managed_runtime_plan(root, tool)
            print(render_managed_runtime_plan(plan, action="stop dry-run").rstrip())
            return 0

        result = execute_managed_runtime_stop(root, tool, confirm=True)
        print(render_managed_runtime_result(result).rstrip())
        return 0 if result.get("return_code") == 0 else 1
    except PermissionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
