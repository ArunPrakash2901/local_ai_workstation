#!/usr/bin/env python3
"""Deterministic Product Lane technical plan CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_tech_plan import confirm_tech_plan, render_tech_plan_preview, validate_tech_plan_preconditions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic Product Lane technical plan generation and preview."
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview technical plan output without writing files.",
    )
    mode_group.add_argument(
        "--confirm",
        action="store_true",
        help="Write deterministic technical plan artifact and update metadata.",
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    if not args.product_id or not str(args.product_id).strip():
        print("ERROR: --product <product_id> is required.", file=sys.stderr)
        return 2

    product_id = str(args.product_id).strip()
    try:
        if args.dry_run:
            payload = validate_tech_plan_preconditions(root, product_id, require_wireframe_review_pass=False)
            output = render_tech_plan_preview(payload)
            print(output.rstrip())
        else:
            result = confirm_tech_plan(root, product_id, confirm=True)
            print("TECHNICAL PLAN SUCCESS")
            print("======================")
            print(f"Product: {result['product_id']}")
            print(f"Technical Plan Path: {result['technical_plan_path']}")
            print(f"Technical Plan Hash: {result['active_technical_plan_hash']}")
            print(f"Created At: {result['technical_plan_created_at']}")
            print("")
            print("Files Written:")
            for fw in result["files_written"]:
                print(f"- {fw}")
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
