#!/usr/bin/env python3
"""Show one Phase 0 Product Lane product status."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from product_registry import get_product_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show product status from product.yaml.")
    parser.add_argument("product_id", help="Product id slug.")
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
        record = get_product_status(root, args.product_id)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

