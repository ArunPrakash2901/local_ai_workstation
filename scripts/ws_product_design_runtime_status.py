#!/usr/bin/env python3
"""Show Open Design managed runtime status through tools-dev."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_design_adapter import validate_design_tool
from product_design_managed_runtime import (
    execute_managed_runtime_status,
    render_managed_runtime_status,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show Open Design managed runtime status without starting design generation."
    )
    parser.add_argument("--tool", help="Design adapter tool id (open-design in this slice).")
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if not args.tool or not str(args.tool).strip():
        print("ERROR: --tool <tool> is required.", file=sys.stderr)
        return 2

    try:
        tool = validate_design_tool(str(args.tool).strip())
        result = execute_managed_runtime_status(root, tool)
        print(render_managed_runtime_status(result).rstrip())
        return 0 if result.get("status") in {"STATUS_OK", "REFUSED_STATUS_UNAVAILABLE"} else 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
