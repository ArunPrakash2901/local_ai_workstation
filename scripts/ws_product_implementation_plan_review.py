#!/usr/bin/env python3
"""Deterministic no-write Product Lane implementation plan review CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_implementation_plan_review import (
    render_implementation_plan_review_report,
    review_implementation_plan_text,
    validate_implementation_plan_review_preconditions,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review deterministic Product Lane implementation plan (dry-run)."
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run implementation plan review without writing files.",
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
        print("ERROR: --dry-run is required. Review is currently dry-run only.", file=sys.stderr)
        return 2

    if not args.product_id or not str(args.product_id).strip():
        print("ERROR: --product <product_id> is required.", file=sys.stderr)
        return 2

    try:
        payload = validate_implementation_plan_review_preconditions(root, str(args.product_id).strip())
        review_result = review_implementation_plan_text(
            payload["product_record"],
            payload["impl_plan_text"],
            payload_extras=payload,
        )
        report = render_implementation_plan_review_report(
            payload["product_record"],
            review_result,
            impl_plan_path=payload["impl_plan_path"],
        )
        print(report.rstrip())
        return 0 if review_result["status"] in ("PASS", "WARN") else 1

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
