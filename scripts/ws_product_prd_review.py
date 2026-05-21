#!/usr/bin/env python3
"""Preview deterministic Product Lane PRD review report (dry-run only)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_prd_review import (
    load_prd_review_inputs,
    render_prd_review_report,
    review_prd_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preview deterministic Product Lane PRD review from product.yaml, "
            "scope_lock.md, and prd.md (Phase 2 Slice 3A dry-run only)."
        )
    )
    parser.add_argument(
        "--product",
        dest="product_id",
        help="Existing product id slug.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Required in Phase 2 Slice 3A. Write-mode is not implemented.",
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

    if not args.dry_run:
        print(
            "ERROR: Write-mode product-prd-review is not implemented in Phase 2 Slice 3A.\n"
            "Use --dry-run.",
            file=sys.stderr,
        )
        return 2

    if not args.product_id or not str(args.product_id).strip():
        print("ERROR: --product <product_id> is required.", file=sys.stderr)
        return 2

    try:
        payload = load_prd_review_inputs(root, str(args.product_id).strip())
        review_result = review_prd_text(
            payload["product_record"],
            payload["scope_lock_text"],
            payload["prd_text"],
        )
        output = render_prd_review_report(
            payload["product_record"],
            review_result,
            prd_path=payload["prd_path"],
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
    return 3 if review_result.get("status") == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

