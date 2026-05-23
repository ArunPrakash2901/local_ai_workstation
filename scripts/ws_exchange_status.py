#!/usr/bin/env python3
"""Show Exchange Lane Phase 0 packet status."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from exchange_registry import get_exchange_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show one exchange packet status from exchange.yaml.")
    parser.add_argument("exchange_id", nargs="?", help="Exchange id slug.")
    parser.add_argument("--exchange", dest="exchange_flag", help="Exchange id slug.")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    exchange_id = str(args.exchange_flag or args.exchange_id or "").strip()
    if not exchange_id:
        print("ERROR: provide exchange id as positional <exchange_id> or --exchange <exchange_id>.", file=sys.stderr)
        return 2

    try:
        packet = get_exchange_status(root, exchange_id)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(packet, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

