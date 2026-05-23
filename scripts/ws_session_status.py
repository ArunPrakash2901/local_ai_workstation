#!/usr/bin/env python3
"""Show one runtime session manifest status (PURE_READ)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from session_registry import get_session_status, render_session_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show one runtime session status from session.yaml.")
    parser.add_argument("session_id", nargs="?", help="Session id slug.")
    parser.add_argument("--session", dest="session_flag", help="Session id slug.")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    session_id = str(args.session_flag or args.session_id or "").strip()
    if not session_id:
        print("ERROR: provide session id as positional <session_id> or --session <session_id>.", file=sys.stderr)
        return 2
    try:
        manifest = get_session_status(root, session_id)
        print(render_session_status(manifest).rstrip())
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
