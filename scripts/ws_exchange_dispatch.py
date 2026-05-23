#!/usr/bin/env python3
"""Preview Exchange Lane dispatch readiness without execution."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from exchange_dispatch import (
    _load_command_manifest,
    load_exchange_for_dispatch,
    render_dispatch_preview,
    validate_exchange_dispatch_ready,
)
from exchange_codex_adapter import render_codex_dispatch_result, run_codex_adapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview exchange dispatch readiness (no execution).")
    parser.add_argument("--exchange", dest="exchange_id", help="Exchange id to validate.")
    parser.add_argument("--target", help="Adapter target for confirm mode (codex_cli only in this slice).")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; no execution and no writes.")
    parser.add_argument("--confirm", action="store_true", help="Reserved for future slice.")
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

    if args.confirm:
        if not args.target or not str(args.target).strip():
            print("ERROR: --target <target> is required for --confirm.", file=sys.stderr)
            return 2
        target = str(args.target).strip()
        if target != "codex_cli":
            print("ERROR: only --target codex_cli is supported for exchange-dispatch --confirm in this slice.", file=sys.stderr)
            return 2
        try:
            result = run_codex_adapter(root, str(args.exchange_id).strip(), target)
            print(render_codex_dispatch_result(result).rstrip())
            return 0 if result.get("ok") else 1
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    if not args.dry_run:
        print("Write-mode exchange-dispatch is not implemented in this slice. Use --dry-run.")
        return 1

    try:
        packet = load_exchange_for_dispatch(root, str(args.exchange_id).strip())
        manifest = _load_command_manifest(root)
        validation = validate_exchange_dispatch_ready(packet, manifest)
        print(render_dispatch_preview(packet, validation).rstrip())
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
