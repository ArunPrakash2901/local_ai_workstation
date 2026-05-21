#!/usr/bin/env python3
"""Preview Product Lane Phase 1 intake questions.

Phase 1 Slice 1 scope:
- supports --dry-run only
- static question bank only
- no writes, no model/provider/agent calls
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_intake_questions import (
    get_supported_product_types,
    render_questions,
    validate_question_bank,
)
from product_registry import get_product_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview Product Lane static intake questions (dry-run only)."
    )
    parser.add_argument(
        "--type",
        dest="product_type",
        choices=get_supported_product_types(),
        help="Product type for static question preview.",
    )
    parser.add_argument(
        "--product",
        dest="product_id",
        help="Optional product id; resolves product_type from products/<id>/product.yaml.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "text"),
        default="markdown",
        help="Output format for question preview.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Required in Phase 1 Slice 1. No-write preview only.",
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def _resolve_product_type(args: argparse.Namespace, root: Path) -> str:
    if not args.product_type and not args.product_id:
        raise ValueError("usage requires either --type <product_type> or --product <product_id>")

    resolved_type = args.product_type
    if args.product_id:
        record = get_product_status(root, args.product_id)
        from_record = str(record.get("product_type", "")).strip()
        if not from_record:
            raise ValueError(f"product {args.product_id!r} has no product_type")
        if resolved_type and resolved_type != from_record:
            raise ValueError(
                f"--type {resolved_type!r} does not match product {args.product_id!r} "
                f"type {from_record!r}"
            )
        resolved_type = from_record

    if not resolved_type:
        raise ValueError("could not resolve product type")
    return resolved_type


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    if not args.dry_run:
        print(
            "ERROR: write-mode product questions are not implemented in Phase 1 Slice 1.\n"
            "Use --dry-run.",
            file=sys.stderr,
        )
        return 2

    validation_errors = validate_question_bank()
    if validation_errors:
        print("ERROR: static question bank validation failed:", file=sys.stderr)
        for error in validation_errors:
            print(f"- {error}", file=sys.stderr)
        return 3

    try:
        product_type = _resolve_product_type(args, root)
        output = render_questions(product_type, format=args.format)
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

