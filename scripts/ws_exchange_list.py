#!/usr/bin/env python3
"""List Exchange Lane Phase 0 packet records."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from exchange_registry import list_exchanges


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List exchange packet directories from exchange/.")
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
        rows = list_exchanges(root)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not rows:
        print(f"No exchanges found under {root / 'exchange'}")
        return 0

    print("exchange_id | status | target | created_at | path | note")
    print("----------- | ------ | ------ | ---------- | ---- | ----")
    for row in rows:
        note = row.get("error", "") or ""
        print(
            f"{row.get('exchange_id','')} | {row.get('status','')} | {row.get('target','')} | "
            f"{row.get('created_at','')} | {row.get('path','')} | {note}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

