#!/usr/bin/env python3
"""Show Product Lane design run sandbox status (PURE_READ)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_design_adapter import validate_design_tool
from product_design_run import get_design_run_status, render_design_run_status


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show Product Lane design run sandbox status (no writes, no execution)."
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument("--tool", help="Design adapter tool id (open-design in this slice).")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve()

    if not args.product_id or not str(args.product_id).strip():
        print("ERROR: --product <product_id> is required.", file=sys.stderr)
        return 2
    if not args.tool or not str(args.tool).strip():
        print("ERROR: --tool <tool> is required.", file=sys.stderr)
        return 2

    try:
        tool = validate_design_tool(str(args.tool).strip())
        status = get_design_run_status(root, str(args.product_id).strip(), tool)
        print(render_design_run_status(status).rstrip())
        return 0
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

