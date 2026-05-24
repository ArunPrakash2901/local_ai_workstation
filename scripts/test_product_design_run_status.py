#!/usr/bin/env python3
"""Temp-root tests for Product Lane design run status (PURE_READ)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from uuid import uuid4


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from product_design_run import get_design_run_status, prepare_design_run  # noqa: E402
from product_registry import create_product, initialize_products_dir, save_product  # noqa: E402
from product_scope_lock import compute_scope_lock_hash  # noqa: E402


def expect(name: str, condition: bool, failures: list[str], detail: str = "") -> None:
    if condition:
        print(f"PASS: {name}")
    else:
        message = f"FAIL: {name}"
        if detail:
            message = f"{message} - {detail}"
        failures.append(message)


def _pick_temp_parent(root: Path) -> Path:
    scratch = (root / "scratch").resolve()
    try:
        scratch.mkdir(parents=True, exist_ok=True)
        probe = scratch / f"_probe_{uuid4().hex}"
        probe.mkdir()
        probe.rmdir()
        return scratch
    except Exception:
        return Path(tempfile.gettempdir()).resolve()


def _wireframe_text() -> str:
    return "\n".join(
        [
            "# Wireframe v1",
            "",
            "## Page/Screen Map",
            "- Home",
            "",
            "## ASCII/Text Wireframes",
            "[Home]",
            "",
            "## Component Inventory",
            "- Header",
            "",
            "## Navigation Model",
            "- Primary nav",
            "",
            "## Content Hierarchy",
            "- Hero first",
            "",
            "## Responsive Notes",
            "- Mobile-first",
            "",
            "## Accessibility Notes",
            "- Keyboard support",
            "",
            "## Generated From",
            "- prds/prd_v2.md",
            "- scope_locks/scope_lock_v2.md",
            "- no model/provider/agent calls",
            "",
        ]
    ) + "\n"


def _make_product(root: Path) -> tuple[str, Path]:
    record = create_product(
        title=f"design-run-status-{uuid4().hex[:8]}",
        product_type="website",
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    product_id = str(record["product_id"])
    pdir = root / "products" / product_id

    scope_rel = "scope_locks/scope_lock_v2.md"
    prd_rel = "prds/prd_v2.md"
    wireframe_rel = "wireframes/wireframe_v1.md"

    scope_text = "# Scope Lock Revision v2\n\n## In Scope\n- Marketing website refresh.\n"
    prd_text = "# PRD v2\n\n## Objective\n- Improve conversion.\n"
    wireframe_text = _wireframe_text()

    (pdir / scope_rel).parent.mkdir(parents=True, exist_ok=True)
    (pdir / prd_rel).parent.mkdir(parents=True, exist_ok=True)
    (pdir / wireframe_rel).parent.mkdir(parents=True, exist_ok=True)
    (pdir / scope_rel).write_text(scope_text, encoding="utf-8", newline="\n")
    (pdir / prd_rel).write_text(prd_text, encoding="utf-8", newline="\n")
    (pdir / wireframe_rel).write_text(wireframe_text, encoding="utf-8", newline="\n")

    payload = json.loads((pdir / "product.yaml").read_text(encoding="utf-8"))
    payload["state"] = "SCOPE_LOCKED"
    payload["prd_status"] = "APPROVED"
    payload["active_scope_lock"] = scope_rel
    payload["active_scope_lock_hash"] = compute_scope_lock_hash(scope_text)
    payload["active_scope_revision"] = 2
    payload["active_prd"] = prd_rel
    payload["active_prd_hash"] = hashlib.sha256(prd_text.encode("utf-8")).hexdigest()
    payload["active_prd_revision"] = 2
    payload["active_wireframe"] = wireframe_rel
    payload["active_wireframe_hash"] = hashlib.sha256(wireframe_text.encode("utf-8")).hexdigest()
    payload["wireframe_status"] = "DRAFTED"
    (pdir / "product.yaml").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return product_id, pdir


def main() -> int:
    print("Product Design Run Status Validation")
    print("===================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_design_run_status_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)
        product_id, product_dir = _make_product(temp_root)

        before_files = sorted(
            path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file()
        )

        status_not_prepared = get_design_run_status(temp_root, product_id, "open-design")
        expect(
            "status reports NOT_PREPARED if no run exists",
            status_not_prepared["status"] == "NOT_PREPARED",
            failures,
            detail=str(status_not_prepared["status"]),
        )
        expect(
            "status writes no files",
            before_files
            == sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file()),
            failures,
        )

        _ = prepare_design_run(temp_root, product_id, "open-design", confirm=True)
        status_prepared = get_design_run_status(temp_root, product_id, "open-design")
        expect(
            "status reports PREPARED_NOT_EXECUTED when design_run.yaml exists",
            status_prepared["status"] == "PREPARED_NOT_EXECUTED",
            failures,
            detail=str(status_prepared["status"]),
        )
        expect(
            "status reports presence of design_input.yaml",
            status_prepared["design_input_yaml_present"] is True,
            failures,
        )
        expect(
            "status reports presence of design_prompt.md",
            status_prepared["design_prompt_md_present"] is True,
            failures,
        )
        expect(
            "status does not execute Open Design",
            status_prepared["open_design_executed"] is False and status_prepared["open_design_installed"] is False,
            failures,
        )

        after_files = sorted(
            path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file()
        )
        _ = get_design_run_status(temp_root, product_id, "open-design")
        expect(
            "status writes no files",
            after_files
            == sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file()),
            failures,
        )

        try:
            _ = get_design_run_status(temp_root, product_id, "unknown")
            failures.append("FAIL: status rejects unknown tool - expected exception")
        except ValueError:
            expect("status rejects unknown tool", True, failures)

        try:
            _ = get_design_run_status(temp_root, product_id, "../open-design")
            failures.append("FAIL: status rejects path traversal tool - expected exception")
        except ValueError:
            expect("status rejects path traversal tool", True, failures)

        for script_name in ("product_design_run.py", "ws_product_design_run_status.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            disallowed = ("pip install", "npm install", "openai.", "anthropic.", "requests.post(")
            expect(
                "status does not execute Open Design",
                all(token not in source for token in disallowed),
                failures,
                script_name,
            )

    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    print("")
    if failures:
        print("Result: FAIL")
        for failure in failures:
            print(failure)
        return 1
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

