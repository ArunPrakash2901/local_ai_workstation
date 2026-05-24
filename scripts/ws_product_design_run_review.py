#!/usr/bin/env python3
"""Preview/write Product Lane design run static review surface."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_design_adapter import validate_design_tool
from product_design_run_review import (
    build_design_run_review,
    render_design_run_review_preview,
    write_design_run_review_artifacts,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or write Product Lane design run static review artifacts."
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument("--tool", help="Design adapter tool id (open-design in this slice).")
    parser.add_argument("--dry-run", action="store_true", help="Preview review artifacts; no writes.")
    parser.add_argument("--confirm", action="store_true", help="Write static review artifacts.")
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
    if args.dry_run == args.confirm:
        print("ERROR: provide exactly one of --dry-run or --confirm.", file=sys.stderr)
        return 2

    try:
        tool = validate_design_tool(str(args.tool).strip())
        review_model = build_design_run_review(root, str(args.product_id).strip(), tool)
        if args.dry_run:
            print(render_design_run_review_preview(review_model).rstrip())
            return 0

        write_result = write_design_run_review_artifacts(review_model, confirm=True)
        print("PRODUCT DESIGN RUN REVIEW WRITE SUCCESS")
        print("======================================")
        print(f"Product: {args.product_id}")
        print(f"Tool: {tool}")
        print(f"Review Status: {write_result['review_status']}")
        print("")
        print("Files Written:")
        for rel in write_result["files_written"]:
            print(f"- {rel}")
        print("")
        print(f"Canonical source warning: {write_result['canonical_source_warning']}")
        print(f"No execution statement: {write_result['no_execution_statement']}")
        print(f"Open Design executed: {write_result['open_design_executed']}")
        print(f"Open Design installed: {write_result['open_design_installed']}")
        return 0
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


if __name__ == "__main__":
    raise SystemExit(main())

