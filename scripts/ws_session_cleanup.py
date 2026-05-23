#!/usr/bin/env python3
"""Preview runtime session cleanup candidates without deleting anything (dry-run only)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from session_registry import inspect_session_cleanup_candidates, render_session_cleanup_preview


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview runtime session cleanup candidates (no deletion).")
    parser.add_argument("--session", dest="session_id", default="", help="Optional session id to preview only one session.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; no deletion and no writes.")
    parser.add_argument("--confirm", action="store_true", help="Reserved for future cleanup execution slice.")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    if args.confirm:
        print("Write-mode session-cleanup is not implemented in this slice. Use --dry-run.")
        return 1
    if not args.dry_run:
        print("Write-mode session-cleanup is not implemented in this slice. Use --dry-run.")
        return 1

    try:
        report = inspect_session_cleanup_candidates(root)
        if args.session_id:
            sid = str(args.session_id).strip()
            report["cleanup_candidates"] = [x for x in report.get("cleanup_candidates", []) if x.get("session_id") == sid]
            report["keep"] = [x for x in report.get("keep", []) if x.get("session_id") == sid]
            report["warnings"] = [x for x in report.get("warnings", []) if x.get("session_id") == sid]
            report["inspected_count"] = (
                len(report.get("cleanup_candidates", []))
                + len(report.get("keep", []))
                + len(report.get("warnings", []))
            )
        print(render_session_cleanup_preview(report).rstrip())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
