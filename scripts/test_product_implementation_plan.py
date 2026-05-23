#!/usr/bin/env python3
"""Temp-root tests for Product Lane implementation plan dry-run gate."""

from __future__ import annotations

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

from product_answer_import import import_answers  # noqa: E402
from product_implementation_plan import (  # noqa: E402
    load_implementation_plan_inputs,
    render_implementation_plan_preview,
    write_implementation_plan,
)
from product_intake_artifacts import start_intake  # noqa: E402
from product_intake_questions import get_question_bank  # noqa: E402
from product_prd import write_prd  # noqa: E402
from product_registry import create_product, get_product_status, initialize_products_dir, save_product  # noqa: E402
from product_scope_lock import compute_scope_lock_hash, lock_scope  # noqa: E402
from product_tech_plan import confirm_tech_plan  # noqa: E402
from product_wireframe import confirm_wireframe  # noqa: E402


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


def _answers_text(product_type: str) -> str:
    lines: list[str] = []
    for question in get_question_bank(product_type):
        lines.append(f"{question['id']}: answer for {question['id']}")
    return "\n".join(lines) + "\n"


def _make_ready_product(root: Path) -> dict[str, object]:
    record = create_product(
        title=f"implementation-plan sample {uuid4().hex[:8]}",
        product_type="website",
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text("website"), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    write_prd(root, str(record["product_id"]), confirm=True)

    pdir = root / "products" / str(record["product_id"])
    product_file = pdir / "product.yaml"
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    payload["active_prd"] = "prd.md"
    payload["active_prd_hash"] = __import__("hashlib").sha256((pdir / "prd.md").read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    payload["active_prd_revision"] = 1
    payload["active_scope_lock"] = "scope_lock.md"
    payload["active_scope_lock_hash"] = compute_scope_lock_hash((pdir / "scope_lock.md").read_text(encoding="utf-8"))
    payload["active_scope_revision"] = 1
    payload["prd_status"] = "APPROVED"
    payload["prd_approved_at"] = "2026-01-01T00:00:00Z"
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    confirm_wireframe(root, str(record["product_id"]), confirm=True)
    confirm_tech_plan(root, str(record["product_id"]), confirm=True)

    # Normalize required sections so baseline technical plan review passes.
    tech_path = pdir / "technical_plans" / "technical_plan_v1.md"
    tech_text = tech_path.read_text(encoding="utf-8").replace("TODO/UNKNOWN", "PENDING")
    tech_path.write_text(tech_text, encoding="utf-8", newline="\n")
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    payload["active_technical_plan_hash"] = __import__("hashlib").sha256((tech_text.rstrip("\n") + "\n").encode("utf-8")).hexdigest()
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return get_product_status(root, str(record["product_id"]))


def main() -> int:
    print("Product Implementation Plan Validation")
    print("=====================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_implementation_plan_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)
        ready = _make_ready_product(temp_root)
        product_id = str(ready["product_id"])
        pdir = temp_root / "products" / product_id

        # Dry-run validation
        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        payload = load_implementation_plan_inputs(temp_root, product_id)
        preview = render_implementation_plan_preview(payload)
        after_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("implementation-plan dry-run passes only after valid tech plan review", "Implementation Plan Preview" in preview and "technical_plan_review_status: `PASS`" in preview, failures)
        expect("implementation-plan dry-run writes no files", before_files == after_files, failures)
        expect("implementation-plan dry-run proposes v1 path", "implementation_plans/implementation_plan_v1.md" in preview, failures)

        # Confirm (Write) validation
        result = write_implementation_plan(temp_root, product_id, confirm=True)
        expect("implementation-plan confirm returns success", "CREATED:" in result and "UPDATED: product.yaml" in result, failures)
        plan_path = pdir / "implementation_plans" / "implementation_plan_v1.md"
        expect("implementation-plan v1 exists", plan_path.is_file(), failures)
        
        updated_ready = get_product_status(temp_root, product_id)
        expect("product metadata: active_implementation_plan set", updated_ready.get("active_implementation_plan") == "implementation_plans/implementation_plan_v1.md", failures)
        expect("product metadata: active_implementation_plan_hash set", bool(updated_ready.get("active_implementation_plan_hash")), failures)
        expect("product metadata: implementation_plan_status is DRAFTED", updated_ready.get("implementation_plan_status") == "DRAFTED", failures)
        
        # Duplicate refusal
        try:
            write_implementation_plan(temp_root, product_id, confirm=True)
            failures.append("FAIL: implementation-plan confirm should refuse duplicate")
        except FileExistsError:
            print("PASS: implementation-plan confirm refuses duplicate")

        missing = _make_ready_product(temp_root)
        missing_id = str(missing["product_id"])
        missing_file = temp_root / "products" / missing_id / "product.yaml"
        payload_m = json.loads(missing_file.read_text(encoding="utf-8"))
        payload_m["active_technical_plan"] = ""
        payload_m["active_technical_plan_hash"] = ""
        missing_file.write_text(json.dumps(payload_m, indent=2) + "\n", encoding="utf-8")
        try:
            load_implementation_plan_inputs(temp_root, missing_id)
            failures.append("FAIL: implementation-plan gate fails without active technical plan")
        except ValueError:
            print("PASS: implementation-plan gate fails without active technical plan")

        bad_review = _make_ready_product(temp_root)
        bad_review_id = str(bad_review["product_id"])
        tech_path = temp_root / "products" / bad_review_id / "technical_plans" / "technical_plan_v1.md"
        text = tech_path.read_text(encoding="utf-8").replace("## Architecture Overview", "## Architecture Overview\n\n- TODO/UNKNOWN")
        tech_path.write_text(text, encoding="utf-8", newline="\n")
        bad_file = temp_root / "products" / bad_review_id / "product.yaml"
        bad_payload = json.loads(bad_file.read_text(encoding="utf-8"))
        bad_payload["active_technical_plan_hash"] = __import__("hashlib").sha256((text.rstrip("\n") + "\n").encode("utf-8")).hexdigest()
        bad_file.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_implementation_plan_inputs(temp_root, bad_review_id)
            failures.append("FAIL: implementation-plan gate fails when technical plan review not PASS")
        except ValueError:
            print("PASS: implementation-plan gate fails when technical plan review not PASS")

        for script_name in ("product_implementation_plan.py", "ws_product_implementation_plan.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
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
