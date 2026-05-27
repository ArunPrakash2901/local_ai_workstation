#!/usr/bin/env python3
"""Dry-run Product Lane design render preview CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_design_adapter import (
    build_design_render_preview,
    render_design_render_preview,
    validate_design_tool,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or execute Product Lane design render sandbox (dry-run or confirm)."
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument("--tool", help="Design adapter tool id (open-design in this slice).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Preview only; no writes.")
    group.add_argument("--confirm", action="store_true", help="Attempt guarded render execution.")
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
        preview = build_design_render_preview(root, str(args.product_id).strip(), tool)
        
        if args.confirm:
            # We enforce missing command contract failure here for guarded execution
            from product_design_runtime_probe import probe_design_runtime
            probe = probe_design_runtime(root, tool)
            # Only RUNTIME_CANDIDATE_FOUND with a specific identified executable would be valid.
            # We currently have NO valid execution contract (tools-dev fails, od missing).
            raise ValueError("REFUSED_MISSING_RENDER_COMMAND_CONTRACT")
            
        print(render_design_render_preview(preview).rstrip())
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
