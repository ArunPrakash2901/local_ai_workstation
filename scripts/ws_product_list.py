#!/usr/bin/env python3
"""List Phase 0 Product Lane products."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_registry import list_products


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List products from products/ registry.")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    try:
        products = list_products(root)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not products:
        print(f"No products found under {root / 'products'}")
        return 0

    print("product_id | type | state | private | updated_at | label")
    print("---------- | ---- | ----- | ------- | ---------- | -----")
    for record in products:
        print(
            f"{record['product_id']} | {record['product_type']} | {record['state']} | "
            f"{record['private']} | {record['updated_at']} | {record['label']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

