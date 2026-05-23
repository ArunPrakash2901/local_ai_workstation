#!/usr/bin/env python3
"""Create or preview Exchange Lane Phase 0 packet files."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from exchange_registry import create_exchange_packet, render_exchange_preview, save_exchange


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or preview Exchange Lane packet files (Phase 0).")
    parser.add_argument("--target", help="Dispatch target id (Phase 0 metadata only).")
    parser.add_argument("--task-type", dest="task_type", help="Bounded task type label.")
    parser.add_argument("--summary", help="Bounded task summary.")
    parser.add_argument("--product", dest="product_id", default="", help="Optional related product id.")
    parser.add_argument("--source", default="operator", help="Packet source label. Default: operator.")
    parser.add_argument(
        "--safety-mode",
        default="REVIEW_ONLY",
        help="Exchange safety mode label. Default: REVIEW_ONLY.",
    )
    parser.add_argument("--exchange-id", dest="exchange_id", default="", help="Optional exchange id override.")
    parser.add_argument("--dry-run", action="store_true", help="Preview packet and planned files without writing.")
    parser.add_argument("--confirm", action="store_true", help="Write exchange packet files under exchange/<exchange_id>/.")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    if args.dry_run == args.confirm:
        print("ERROR: specify exactly one of --dry-run or --confirm.", file=sys.stderr)
        return 2
    if not args.target or not str(args.target).strip():
        print("ERROR: --target <target> is required.", file=sys.stderr)
        return 2
    if not args.task_type or not str(args.task_type).strip():
        print("ERROR: --task-type <task_type> is required.", file=sys.stderr)
        return 2
    if not args.summary or not str(args.summary).strip():
        print("ERROR: --summary \"<summary>\" is required.", file=sys.stderr)
        return 2

    try:
        packet = create_exchange_packet(
            target=str(args.target).strip(),
            task_type=str(args.task_type).strip(),
            summary=str(args.summary).strip(),
            product_id=str(args.product_id or "").strip(),
            source=str(args.source).strip() or "operator",
            safety_mode=str(args.safety_mode).strip() or "REVIEW_ONLY",
            exchange_id=(str(args.exchange_id).strip() or None),
        )
        if args.dry_run:
            print(render_exchange_preview(packet).rstrip())
            return 0
        result = save_exchange(packet, root, confirm=True)
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    saved = result["packet"]
    print("EXCHANGE PACKET CREATED")
    print("=======================")
    print("")
    print(f"exchange_id: {saved['exchange_id']}")
    print(f"target: {saved['target']}")
    print(f"task_type: {saved['task_type']}")
    print(f"status: {saved['status']}")
    print("")
    print("Files written:")
    for path in result["files_written"]:
        print(f"- {path}")
    print("")
    print("Safety:")
    print("- Packet creation only.")
    print("- No dispatch/execution in Phase 0.")
    print("- No models/providers/agents/browser/MCP used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

