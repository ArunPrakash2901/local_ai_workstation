#!/usr/bin/env python3
"""Prepare Product Lane design run sandbox packet (no tool execution)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_design_adapter import validate_design_tool
from product_design_run import prepare_design_run


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare sandboxed Product Lane design run packet (confirm only, no tool execution)."
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument("--tool", help="Design adapter tool id (open-design in this slice).")
    parser.add_argument("--confirm", action="store_true", help="Write sandbox packet files.")
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
    if not args.confirm:
        print("ERROR: --confirm is required. This command writes sandbox packet files.", file=sys.stderr)
        return 2

    try:
        tool = validate_design_tool(str(args.tool).strip())
        result = prepare_design_run(root, str(args.product_id).strip(), tool, confirm=True)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print("DESIGN RUN PREPARE SUCCESS")
    print("==========================")
    print(f"Product: {result['product_id']}")
    print(f"Tool: {result['tool']}")
    print(f"Run ID: {result['run_id']}")
    print(f"Status: {result['status']}")
    print(f"Execution Mode: {result['execution_mode']}")
    print(f"Allowed Write Root: {result['allowed_write_root']}")
    print("")
    print("Files Written:")
    for path in result["files_written"]:
        print(f"- {path}")
    print("")
    print(f"Open Design executed: {result['open_design_executed']}")
    print(f"Open Design installed: {result['open_design_installed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

