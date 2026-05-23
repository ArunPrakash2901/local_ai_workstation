#!/usr/bin/env python3
"""List runtime session manifests (PURE_READ)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from session_registry import list_sessions, render_session_list


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List runtime session manifests from runtime/sessions.")
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
        rows = list_sessions(root)
        print(render_session_list(rows).rstrip())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
