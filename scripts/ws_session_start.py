#!/usr/bin/env python3
"""Preview runtime session start without starting any process (dry-run only)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from session_registry import build_session_start_preview, render_session_start_preview


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview runtime session start (no process start).")
    parser.add_argument("--session", dest="session_id", help="Session id to preview.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; no writes and no process start.")
    parser.add_argument("--confirm", action="store_true", help="Reserved for future start execution slice.")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    if not args.session_id or not str(args.session_id).strip():
        print("ERROR: --session <session_id> is required.", file=sys.stderr)
        return 2

    if args.confirm:
        print("Write-mode session-start is not implemented in this slice. Use --dry-run.")
        return 1

    if not args.dry_run:
        print("Write-mode session-start is not implemented in this slice. Use --dry-run.")
        return 1

    try:
        preview = build_session_start_preview(root, str(args.session_id).strip())
        print(render_session_start_preview(preview).rstrip())
        if preview.get("preview_status") == "FAIL":
            return 2
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
