#!/usr/bin/env python3
"""Import Exchange Lane result text and generate operator report skeleton."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from exchange_result_import import import_exchange_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import exchange result text into an exchange packet.")
    parser.add_argument("--exchange", dest="exchange_id", help="Exchange id.")
    parser.add_argument("--file", dest="result_file", help="Result markdown file to import.")
    parser.add_argument("--dry-run", action="store_true", help="Preview validation and planned writes without writing.")
    parser.add_argument("--confirm", action="store_true", help="Write imported result artifacts.")
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
    if not args.result_file or not str(args.result_file).strip():
        print("ERROR: --file <result_file> is required.", file=sys.stderr)
        return 2
    if args.dry_run == args.confirm:
        print("ERROR: specify exactly one of --dry-run or --confirm.", file=sys.stderr)
        return 2

    try:
        result = import_exchange_result(root, str(args.exchange_id).strip(), str(args.result_file).strip(), confirm=args.confirm)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(result["preview"].rstrip())
        return 0

    packet = result["packet"]
    parsed_summary = result["parsed_summary"]
    print("EXCHANGE RESULT IMPORTED")
    print("=======================")
    print("")
    print(f"exchange_id: {packet.get('exchange_id', '')}")
    print(f"status: {packet.get('status', '')}")
    print(f"validation_status: {parsed_summary['validation']['status']}")
    print("")
    print("Files written:")
    for path in result["files_written"]:
        print(f"- {path}")
    print("")
    print("Safety:")
    print("- Imported text treated as untrusted.")
    print("- No execution of result content.")
    print("- No model/provider/agent/browser/MCP calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
