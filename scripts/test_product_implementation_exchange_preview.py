#!/usr/bin/env python3
"""Temp-root tests for Product Lane implementation exchange preview dry-run."""

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
from product_implementation_exchange_preview import render_implementation_exchange_preview  # noqa: E402
from product_implementation_plan import write_implementation_plan  # noqa: E402
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
        title=f"exchange-preview sample {uuid4().hex[:8]}",
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

    write_implementation_plan(root, str(record["product_id"]), confirm=True)

    return get_product_status(root, str(record["product_id"]))


def main() -> int:
    print("Product Implementation Exchange Preview Validation")
    print("=================================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_impl_exchange_preview_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)
        ready = _make_ready_product(temp_root)
        product_id = str(ready["product_id"])
        pdir = temp_root / "products" / product_id

        # Review implementation plan first (must pass for exchange preview)
        impl_path = pdir / "implementation_plans" / "implementation_plan_v1.md"
        text = impl_path.read_text(encoding="utf-8")
        fixed_text = text.replace("TODO/UNKNOWN", "COMPLETED")
        impl_path.write_text(fixed_text, encoding="utf-8", newline="\n")
        
        product_file = pdir / "product.yaml"
        product_record = json.loads(product_file.read_text(encoding="utf-8"))
        product_record["active_implementation_plan_hash"] = __import__("hashlib").sha256((fixed_text.rstrip("\n") + "\n").encode("utf-8")).hexdigest()
        product_file.write_text(json.dumps(product_record, indent=2) + "\n", encoding="utf-8")

        # Valid target test
        for target in ("codex_cli", "gemini_cli", "local_ollama"):
            preview = render_implementation_exchange_preview(temp_root, product_id, target)
            expect(f"exchange-preview PASS for target {target}", "Implementation Exchange Preview" in preview and "Ready for handoff: YES" in preview, failures)
            expect(f"exchange-preview includes target {target}", f"target: `{target}`" in preview, failures)
            expect(f"exchange-preview includes future command for {target}", f"ws exchange-new --target {target}" in preview, failures)

        # Unsupported target test
        try:
            render_implementation_exchange_preview(temp_root, product_id, "unsupported_target")
            failures.append("FAIL: exchange-preview should reject unsupported target")
        except ValueError as exc:
            expect("unsupported target error message", "unsupported target" in str(exc), failures)

        # Failed review test
        bad_text = fixed_text.replace("## Implementation Phases", "## Deleted Section")
        impl_path.write_text(bad_text, encoding="utf-8", newline="\n")
        product_record["active_implementation_plan_hash"] = __import__("hashlib").sha256((bad_text.rstrip("\n") + "\n").encode("utf-8")).hexdigest()
        product_file.write_text(json.dumps(product_record, indent=2) + "\n", encoding="utf-8")
        try:
            render_implementation_exchange_preview(temp_root, product_id, "codex_cli")
            failures.append("FAIL: exchange-preview should fail if implementation plan review not PASS")
        except ValueError as exc:
            expect("failed review error message", "requires implementation plan review PASS" in str(exc), failures)

        for script_name in ("product_implementation_exchange_preview.py", "ws_product_implementation_exchange_preview.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            # Surgical check for usage, avoiding false positives from target strings like 'gemini_cli'
            usage_tokens = ("import gemini", "import ollama", "import requests", "openai.", "anthropic.")
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in usage_tokens),
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
