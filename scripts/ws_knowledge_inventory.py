#!/usr/bin/env python3
"""CLI wrapper for knowledge inventory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from knowledge_inventory import (
    collect_inventory,
    render_inventory_report,
    validate_knowledge_target,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Knowledge Lane Inventory")
    parser.add_argument("--target", required=True, help="Knowledge target (e.g. matfinog_youtube)")
    parser.add_argument("--dry-run", action="store_true", help="Preview inventory without writing files")
    parser.add_argument("--confirm", action="store_true", help="Execute inventory (not implemented)")

    args = parser.parse_args()
    root = Path(os.getcwd())

    if not validate_knowledge_target(args.target):
        print(f"Error: Unknown or invalid knowledge target: {args.target!r}")
        return 1

    if args.confirm:
        print("Error: Write-mode knowledge-inventory is not implemented in this slice. Use --dry-run.")
        return 1

    if not args.dry_run:
        print("Error: --dry-run is required for this command in this slice.")
        return 1

    try:
        inventory = collect_inventory(root, args.target)
        report = render_inventory_report(inventory)
        print(report)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    import os
    sys.exit(main())
