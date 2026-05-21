#!/usr/bin/env python3
"""Preview or write deterministic Product Lane PRD content."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_prd import load_prd_inputs, render_prd_preview, write_prd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or write deterministic Product Lane PRD content from locked scope."
        )
    )
    parser.add_argument(
        "--product",
        dest="product_id",
        help="Existing product id slug.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deterministic PRD content without writing files.",
    )
    mode.add_argument(
        "--confirm",
        action="store_true",
        help="Write deterministic PRD content to prd.md.",
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
        product_id = str(args.product_id).strip()
        if args.dry_run:
            payload = load_prd_inputs(root, product_id)
            output = render_prd_preview(
                payload["product_record"],
                payload["scope_lock_text"],
            )
        else:
            result = write_prd(root, product_id, confirm=True)
            output = "\n".join(
                [
                    "Product PRD draft written.",
                    f"- files_written: {', '.join(str(path) for path in result['files_written'])}",
                    f"- product_id: `{result['product_id']}`",
                    f"- state_before: `{result['state_before']}`",
                    f"- state_after: `{result['state_after']}`",
                    f"- prd_path: `{result['prd_path']}`",
                    f"- product_file: `{result['product_file']}`",
                    f"- scope_lock_hash: `{result['scope_lock_hash']}`",
                    f"- prd_created_at: `{result['prd_created_at']}`",
                    "- No model/provider/agent calls.",
                    "- Next step: future PRD review / wireframes / technical planning remain later slices.",
                ]
            )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(output.rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
