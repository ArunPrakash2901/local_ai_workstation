#!/usr/bin/env python3
"""Temp-root tests for Product Lane technical plan review dry-run."""

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
from product_intake_artifacts import start_intake  # noqa: E402
from product_intake_questions import get_question_bank  # noqa: E402
from product_prd import write_prd  # noqa: E402
from product_registry import create_product, get_product_status, initialize_products_dir, save_product  # noqa: E402
from product_scope_lock import compute_scope_lock_hash, lock_scope  # noqa: E402
from product_tech_plan import confirm_tech_plan  # noqa: E402
from product_tech_plan_review import (  # noqa: E402
    review_tech_plan_text,
    validate_tech_plan_review_preconditions,
)
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
        title=f"tech-plan-review sample {uuid4().hex[:8]}",
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

    # Normalize required sections so baseline review case is PASS.
    tech_path = pdir / "technical_plans" / "technical_plan_v1.md"
    tech_text = tech_path.read_text(encoding="utf-8").replace("TODO/UNKNOWN", "PENDING")
    tech_path.write_text(tech_text, encoding="utf-8", newline="\n")
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    payload["active_technical_plan_hash"] = __import__("hashlib").sha256((tech_text.rstrip("\n") + "\n").encode("utf-8")).hexdigest()
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return get_product_status(root, str(record["product_id"]))


def main() -> int:
    print("Product Technical Plan Review Validation")
    print("========================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_tech_plan_review_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        ready = _make_ready_product(temp_root)
        product_id = str(ready["product_id"])
        pdir = temp_root / "products" / product_id

        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        payload = validate_tech_plan_review_preconditions(temp_root, product_id)
        review = review_tech_plan_text(payload["product_record"], payload["tech_plan_text"], payload_extras=payload)
        after_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("review passes complete tech plan", review["status"] == "PASS", failures, detail=str(review))
        expect("review dry-run writes no files", before_files == after_files, failures)

        missing = _make_ready_product(temp_root)
        missing_id = str(missing["product_id"])
        missing_dir = temp_root / "products" / missing_id
        (missing_dir / "technical_plans" / "technical_plan_v1.md").unlink()
        try:
            validate_tech_plan_review_preconditions(temp_root, missing_id)
            failures.append("FAIL: review fails missing technical plan")
        except FileNotFoundError:
            print("PASS: review fails missing technical plan")

        mismatched = _make_ready_product(temp_root)
        mismatched_id = str(mismatched["product_id"])
        mismatched_file = temp_root / "products" / mismatched_id / "product.yaml"
        mismatched_payload = json.loads(mismatched_file.read_text(encoding="utf-8"))
        mismatched_payload["active_technical_plan_hash"] = "0" * 64
        mismatched_file.write_text(json.dumps(mismatched_payload, indent=2) + "\n", encoding="utf-8")
        try:
            validate_tech_plan_review_preconditions(temp_root, mismatched_id)
            failures.append("FAIL: review fails hash mismatched technical plan")
        except ValueError:
            print("PASS: review fails hash mismatched technical plan")

        incomplete = _make_ready_product(temp_root)
        incomplete_id = str(incomplete["product_id"])
        tech_path = temp_root / "products" / incomplete_id / "technical_plans" / "technical_plan_v1.md"
        text = tech_path.read_text(encoding="utf-8").replace("## Deployment Assumptions", "## Deployment")
        tech_path.write_text(text, encoding="utf-8", newline="\n")
        product_file = temp_root / "products" / incomplete_id / "product.yaml"
        payload_i = json.loads(product_file.read_text(encoding="utf-8"))
        payload_i["active_technical_plan_hash"] = __import__("hashlib").sha256((text.rstrip("\n") + "\n").encode("utf-8")).hexdigest()
        product_file.write_text(json.dumps(payload_i, indent=2) + "\n", encoding="utf-8")
        review_payload = validate_tech_plan_review_preconditions(temp_root, incomplete_id)
        review_incomplete = review_tech_plan_text(review_payload["product_record"], review_payload["tech_plan_text"], payload_extras=review_payload)
        expect("review fails incomplete technical plan", review_incomplete["status"] == "FAIL", failures, detail=str(review_incomplete))

        for script_name in ("product_tech_plan_review.py", "ws_product_tech_plan_review.py"):
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
