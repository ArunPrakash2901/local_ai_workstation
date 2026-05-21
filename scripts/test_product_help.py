#!/usr/bin/env python3
"""No-write tests for Product Lane Phase 0 help output."""

from __future__ import annotations

import os
import sys
from pathlib import Path


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ws_product_help import render_product_help  # noqa: E402


def _expect(name: str, ok: bool, failures: list[str]) -> None:
    if ok:
        print(f"PASS: {name}")
    else:
        failures.append(f"FAIL: {name}")


def main() -> int:
    print("Product Help Validation")
    print("=======================")
    failures: list[str] = []

    out = render_product_help()
    _expect("mentions product-new", "ws product-new" in out, failures)
    _expect("mentions product-list", "ws product-list" in out, failures)
    _expect("mentions product-status", "ws product-status" in out, failures)
    _expect("mentions product-intake confirm", "ws product-intake --product" in out and "--confirm" in out, failures)
    _expect("mentions product-answer-import", "ws product-answer-import --product" in out and "--file" in out and "--confirm" in out, failures)
    _expect("mentions product-scope dry-run", "ws product-scope --product" in out and "--dry-run" in out, failures)
    _expect("mentions product-scope-change dry-run", "ws product-scope-change --product" in out and "--file <change_file>" in out and "--dry-run" in out, failures)
    _expect("mentions product-scope-change confirm", "ws product-scope-change --product" in out and "--file <change_file>" in out and "--confirm" in out, failures)
    _expect("mentions product-scope-revision dry-run", "ws product-scope-revision --product" in out and "--dry-run" in out, failures)
    _expect("mentions product-scope-revision confirm", "ws product-scope-revision --product" in out and "--confirm" in out, failures)
    _expect("mentions product-lock-scope", "ws product-lock-scope --product" in out and "--confirm" in out, failures)
    _expect("mentions product-prd dry-run", "ws product-prd --product" in out and "--dry-run" in out and "SCOPE_LOCKED" in out, failures)
    _expect("classifies product-new GUARDED_WRITE", "GUARDED_WRITE" in out, failures)
    _expect("dry-run before confirm guidance", "--dry-run" in out and "--confirm" in out, failures)
    _expect("mentions products/README.md", "products/README.md" in out, failures)

    # No-write invariant: help output must not imply creation is executed automatically.
    _expect("does not imply creating products", "creates products" not in out.lower(), failures)

    if failures:
        for msg in failures:
            print(msg)
        print("")
        print("Result: FAIL")
        return 1

    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
