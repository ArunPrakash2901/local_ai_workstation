#!/usr/bin/env python3
"""Exchange Lane command surface (non-executing)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import audit_exchange_lane  # noqa: E402
import exchange_packet  # noqa: E402


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DEFAULT_ROOT.parents[0]

ROUTING_TARGETS = ["codex_cli", "gemini_cli", "ollama_local", "powershell_manual", "wsl_manual"]


def cmd_help(_args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    print(parser.format_help())
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    return audit_exchange_lane.main(["--root", str(Path(args.root).resolve())])


def cmd_packet_list(args: argparse.Namespace) -> int:
    return exchange_packet.main(["packet-list", "--root", str(Path(args.root).resolve())])


def cmd_packet_status(args: argparse.Namespace) -> int:
    return exchange_packet.main(
        ["packet-status", "--root", str(Path(args.root).resolve()), "--packet-id", args.packet_id]
    )


def cmd_adapter_list(_args: argparse.Namespace) -> int:
    adapters = list(ROUTING_TARGETS)
    runtime_profiles = REPO_ROOT / "runtime_lane" / "adapters"
    if runtime_profiles.exists():
        for path in sorted(runtime_profiles.glob("*_profile.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            adapter_id = data.get("adapter_id")
            if isinstance(adapter_id, str) and adapter_id and adapter_id not in adapters:
                adapters.append(adapter_id)
    print("exchange routing targets:")
    for item in adapters:
        print(f"- {item}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    packets = exchange_packet.list_packets(root)
    status_counts = Counter(str(p.get("packet_status", "UNKNOWN")) for p in packets)
    blocked = [p for p in packets if p.get("packet_status") == "BLOCKED"]
    result_packets = list((root / "result_packets").glob("*.json"))

    print("Exchange Lane Status")
    print("====================")
    print(f"root: {root}")
    print(f"packet_count: {len(packets)}")
    for key in sorted(status_counts):
        print(f"- {key}: {status_counts[key]}")
    print(f"result_packet_count: {len(result_packets)}")
    print(f"blocked_packet_count: {len(blocked)}")
    print(f"known_adapter_count: {len(ROUTING_TARGETS)}")
    if blocked:
        print("blocked packets:")
        for pkt in blocked:
            print(f"- {pkt.get('packet_id', '')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange Lane command interface (non-executing).")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("help", help="Show Exchange Lane help.")
    sub.add_parser("audit", help="Audit Exchange Lane metadata.")
    sub.add_parser("status", help="Show packet and result summary.")
    sub.add_parser("packet-list", help="List packets.")
    packet_status = sub.add_parser("packet-status", help="Show one packet.")
    packet_status.add_argument("--packet-id", required=True)
    sub.add_parser("adapter-list", help="List routing adapters.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "help"
    if command == "help":
        return cmd_help(args, parser)
    if command == "audit":
        return cmd_audit(args)
    if command == "status":
        return cmd_status(args)
    if command == "packet-list":
        return cmd_packet_list(args)
    if command == "packet-status":
        return cmd_packet_status(args)
    if command == "adapter-list":
        return cmd_adapter_list(args)
    print(parser.format_help())
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
