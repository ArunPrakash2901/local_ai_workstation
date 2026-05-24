#!/usr/bin/env python3
"""Dry-run Product Lane design adapter preview CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_design_adapter import (
    build_design_adapter_preview,
    render_design_adapter_preview,
    validate_design_tool,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview Product Lane design adapter run inputs and sandbox boundary (dry-run only)."
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument("--tool", help="Design adapter tool id (open-design in this slice).")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; no writes.")
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
    if not args.dry_run:
        print("Write-mode product-design-adapter-preview is not implemented. Use --dry-run.")
        return 2

    try:
        tool = validate_design_tool(str(args.tool).strip())
        preview = build_design_adapter_preview(root, str(args.product_id).strip(), tool)
        print(render_design_adapter_preview(preview).rstrip())
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
