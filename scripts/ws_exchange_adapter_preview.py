#!/usr/bin/env python3
"""Preview Exchange Lane Codex adapter invocation without execution."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from exchange_adapter_preview import preview_exchange_adapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview exchange adapter invocation (no execution).")
    parser.add_argument("--exchange", dest="exchange_id", help="Exchange id to preview.")
    parser.add_argument("--target", help="Adapter target (codex_cli only in this slice).")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; no execution and no writes.")
    parser.add_argument("--confirm", action="store_true", help="Reserved for future adapter execution slice.")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    if not args.exchange_id or not str(args.exchange_id).strip():
        print("ERROR: --exchange <exchange_id> is required.", file=sys.stderr)
        return 2
    if not args.target or not str(args.target).strip():
        print("ERROR: --target <target> is required.", file=sys.stderr)
        return 2

    if args.confirm:
        print("Adapter execution is not implemented in this slice. Use --dry-run.")
        return 1

    if not args.dry_run:
        print("Adapter execution is not implemented in this slice. Use --dry-run.")
        return 1

    try:
        result = preview_exchange_adapter(root, str(args.exchange_id).strip(), str(args.target).strip())
        print(result["preview"].rstrip())
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
