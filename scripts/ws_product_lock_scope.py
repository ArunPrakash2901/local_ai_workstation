#!/usr/bin/env python3
"""Lock Product Lane scope (guarded write)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_scope_lock import lock_scope


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Lock scope for a SCOPE_READY product by writing immutable scope_lock.md "
            "and recording scope lock metadata in product.yaml."
        )
    )
    parser.add_argument(
        "--product",
        dest="product_id",
        required=True,
        help="Existing product id slug.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for write-mode scope lock.",
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

    if not args.confirm:
        print(
            "ERROR: ws product-lock-scope requires --confirm for writes.\n"
            "Review ws product-scope --product <product_id> --dry-run before locking.",
            file=sys.stderr,
        )
        return 2

    try:
        result = lock_scope(root, str(args.product_id).strip(), confirm=True)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except PermissionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print("SCOPE LOCKED")
    print(f"Product: {result['product_id']}")
    print(f"State: {result['state_before']} -> {result['state_after']}")
    print(f"Locked at: {result['scope_locked_at']}")
    print(f"Scope lock hash: {result['scope_lock_hash']}")
    print("Files written:")
    print(f"- {result['scope_lock_path']}")
    print(f"- {result['product_file']}")
    if result["action_log_updated"]:
        print(f"Action log updated: {result['action_log_path']}")
    else:
        print("Action log updated: skipped (action_log.md not found)")
    print("Models/providers/agents used: no")
    print("Next suggested command: future ws product-prd --dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
