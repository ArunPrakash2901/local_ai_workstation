#!/usr/bin/env python3
"""Create a Phase 0 Product Lane product record."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from product_registry import (
    ALLOWED_PRODUCT_TYPES,
    create_product,
    product_dir,
    save_product,
)


def _bool_flag(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("expected true/false")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a product registry record under products/<product_id>/."
    )
    parser.add_argument("--title", required=True, help="Human-readable product label.")
    parser.add_argument(
        "--type",
        dest="product_type",
        required=True,
        choices=sorted(ALLOWED_PRODUCT_TYPES),
        help="Phase 0 product type.",
    )
    parser.add_argument("--id", dest="product_id", help="Optional explicit product id slug.")
    parser.add_argument("--owner", default="operator", help="Owner label. Default: operator.")
    parser.add_argument(
        "--private",
        type=_bool_flag,
        default=None,
        help="Optional private override (true/false).",
    )
    parser.add_argument(
        "--quick-prototype",
        action="store_true",
        help="Mark product as quick prototype.",
    )
    parser.add_argument("--has-ui", action="store_true")
    parser.add_argument("--has-code", action="store_true")
    parser.add_argument("--has-content", action="store_true")
    parser.add_argument("--tag", action="append", default=[], help="Repeatable tag.")
    parser.add_argument("--notes", default="", help="Optional notes.")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicitly confirm writing product registry files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview record and target paths without writing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    try:
        record = create_product(
            title=args.title,
            product_type=args.product_type,
            product_id=args.product_id,
            owner=args.owner,
            private=args.private,
            quick_prototype=args.quick_prototype,
            has_ui=args.has_ui,
            has_code=args.has_code,
            has_content=args.has_content,
            tags=args.tag,
            notes=args.notes,
        )
        target_dir = product_dir(root, record["product_id"])
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print("DRY-RUN product-new preview")
        print(f"Root: {root}")
        print(f"Target: {target_dir}")
        print(json.dumps(record, indent=2))
        return 0

    if not args.confirm:
        print(
            "ERROR: ws product-new requires explicit confirmation.\n"
            "Re-run with --confirm (or --dry-run to preview only).",
            file=sys.stderr,
        )
        return 2

    try:
        product_file = save_product(record, root, confirm=True, allow_overwrite=False)
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Created product: {record['product_id']}")
    print(f"Record: {product_file}")
    print(f"Action log: {product_file.parent / 'action_log.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

