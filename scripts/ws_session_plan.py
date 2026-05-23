#!/usr/bin/env python3
"""ws session-plan --dry-run (Phase 2, no process start)."""

from __future__ import annotations

import argparse
from pathlib import Path

from session_registry import (
    ALLOWED_SAFETY_MODES,
    build_session_plan,
    render_session_plan_preview,
    save_session_plan,
    validate_session_id,
)


def _parse_modes(values: list[str] | None) -> list[str]:
    if not values:
        return []
    modes: list[str] = []
    for value in values:
        for part in value.split(","):
            candidate = part.strip()
            if not candidate:
                continue
            if candidate not in ALLOWED_SAFETY_MODES:
                raise ValueError(f"unsupported safety mode: {candidate}")
            if candidate not in modes:
                modes.append(candidate)
    return modes


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview runtime session plan without writes or process start.")
    parser.add_argument("--session", required=True, help="Session id")
    parser.add_argument("--runtime", required=True, help="Runtime type")
    parser.add_argument("--adapter", required=True, help="Adapter")
    parser.add_argument("--cwd", default="", help="Optional override CWD")
    parser.add_argument("--shell", default="", help="Optional override shell")
    parser.add_argument("--safety-mode", action="append", default=[], help="Allowed safety mode; repeat or comma-separate")
    parser.add_argument("--target", default="", help="Optional planned exchange target")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--confirm", action="store_true", help="Write planned session metadata")
    parser.add_argument("--root", default=".", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.dry_run == args.confirm:
        print("Error: provide exactly one mode flag: --dry-run or --confirm.")
        return 2

    if not validate_session_id(args.session):
        print(f"Error: invalid session id: {args.session!r}")
        return 2

    try:
        modes = _parse_modes(args.safety_mode)
        plan = build_session_plan(
            session_id=args.session,
            runtime_type=args.runtime,
            adapter=args.adapter,
            root=Path(args.root),
            cwd=args.cwd or None,
            shell=args.shell or None,
            safety_modes=modes or None,
            target=args.target or None,
        )
    except Exception as exc:
        print(f"Error: {exc}")
        return 2

    if args.dry_run:
        print(render_session_plan_preview(plan))
        return 0

    try:
        result = save_session_plan(Path(args.root), plan, confirm=True)
    except Exception as exc:
        print(f"Error: {exc}")
        return 2

    print("# Runtime Session Plan")
    print("")
    print("- CONFIRM / planned session metadata created")
    print("- No process started")
    print("- No adapter execution")
    print(f"- session_id: `{plan['session_id']}`")
    print(f"- runtime_type: `{plan['runtime_type']}`")
    print(f"- adapter: `{plan['adapter']}`")
    print("")
    print("## Files Written")
    for item in result.get("files_written", []):
        print(f"- {item}")
    print("")
    print("## Next Step")
    print("- Future `ws session-start --confirm` (not implemented in this slice).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
