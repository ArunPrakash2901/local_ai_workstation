#!/usr/bin/env python3
"""Deterministic Product Lane PRD revision CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_prd_revision import confirm_prd_revision, load_prd_revision_inputs, render_prd_revision_dry_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic Product Lane PRD revision from active scope lock."
        )
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deterministic PRD revision output without writing files.",
    )
    mode_group.add_argument(
        "--confirm",
        action="store_true",
        help="Execute the deterministic PRD revision and update product metadata.",
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

    try:
        if args.dry_run:
            payload = load_prd_revision_inputs(root, str(args.product_id).strip())
            output = render_prd_revision_dry_run(payload)
            print(output.rstrip())
        elif args.confirm:
            result = confirm_prd_revision(root, str(args.product_id).strip(), confirm=True)
            print("PRD REVISION SUCCESS")
            print("====================")
            print(f"Product: {result['product_id']}")
            print(f"State: {result['state_before']} -> {result['state_after']}")
            print(f"Revised PRD Path: {result['prd_path']}")
            print(f"Revised PRD Hash: {result['active_prd_hash']}")
            print(f"Revised At: {result['prd_revised_at']}")
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
