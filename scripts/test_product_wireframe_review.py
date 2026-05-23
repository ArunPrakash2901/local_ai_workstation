#!/usr/bin/env python3
"""Temp-root tests for Product Lane wireframe review."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
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
from product_wireframe import confirm_wireframe  # noqa: E402
from product_wireframe_review import load_wireframe_review_inputs, review_wireframe_text  # noqa: E402


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
        qid = str(question["id"])
        lines.append(f"{qid}: answer for {qid}")
    return "\n".join(lines) + "\n"


def _make_wireframe_ready_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} wireframe review sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    write_prd(root, str(record["product_id"]), confirm=True)
    
    # Manually approve PRD in metadata for wireframe readiness
    product_file = root / "products" / str(record["product_id"]) / "product.yaml"
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    
    # Correctly populate PRD metadata
    prd_path = root / "products" / str(record["product_id"]) / "prd.md"
    prd_text = prd_path.read_text(encoding="utf-8")
    prd_hash = hashlib.sha256(prd_text.encode("utf-8")).hexdigest()
    
    # Correctly populate scope lock metadata
    scope_path = root / "products" / str(record["product_id"]) / "scope_lock.md"
    scope_hash = compute_scope_lock_hash(scope_path.read_text(encoding="utf-8"))
    
    payload["active_prd"] = "prd.md"
    payload["active_prd_hash"] = prd_hash
    payload["active_prd_revision"] = 1
    payload["active_scope_lock"] = "scope_lock.md"
    payload["active_scope_lock_hash"] = scope_hash
    payload["prd_status"] = "APPROVED"
    payload["prd_approved_at"] = "2026-01-01T00:00:00Z"
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    
    confirm_wireframe(root, str(record["product_id"]), confirm=True)
    
    # Remove TODO/UNKNOWN for "complete" test case and re-hash
    wf_path = root / "products" / str(record["product_id"]) / "wireframes" / "wireframe_v1.md"
    text = wf_path.read_text(encoding="utf-8")
    text = text.replace("TODO/UNKNOWN", "PENDING")
    wf_path.write_text(text, encoding="utf-8", newline="\n")
    
    new_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    product_file = root / "products" / str(record["product_id"]) / "product.yaml"
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    payload["active_wireframe_hash"] = new_hash
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return get_product_status(root, str(record["product_id"]))


def main() -> int:
    print("Product Wireframe Review Validation")
    print("===================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_wireframe_review_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        # 1 review passes for complete wireframe.
        ready = _make_wireframe_ready_product(temp_root)
        ready_id = str(ready["product_id"])
        payload = load_wireframe_review_inputs(temp_root, ready_id)
        result = review_wireframe_text(payload["product_record"], payload["wireframe_text"], payload_extras=payload)
        expect("review status PASS for complete wireframe", result["status"] == "PASS", failures)

        # 2 review fails if active_wireframe_hash mismatch.
        mismatch = _make_wireframe_ready_product(temp_root)
        mismatch_id = str(mismatch["product_id"])
        product_file = temp_root / "products" / mismatch_id / "product.yaml"
        payload_m = json.loads(product_file.read_text(encoding="utf-8"))
        payload_m["active_wireframe_hash"] = "wrong"
        product_file.write_text(json.dumps(payload_m, indent=2) + "\n", encoding="utf-8")
        
        payload_p = load_wireframe_review_inputs(temp_root, mismatch_id)
        result_m = review_wireframe_text(payload_p["product_record"], payload_p["wireframe_text"], payload_extras=payload_p)
        expect("review status FAIL for hash mismatch", result_m["status"] == "FAIL", failures)
        expect("hash mismatch found in fail_reasons", "active_wireframe hash mismatch" in result_m["fail_reasons"], failures)

        # 3 review fails if required sections missing.
        missing_sec = _make_wireframe_ready_product(temp_root)
        missing_sec_id = str(missing_sec["product_id"])
        wf_path = temp_root / "products" / missing_sec_id / "wireframes" / "wireframe_v1.md"
        text = wf_path.read_text(encoding="utf-8")
        # Remove Page/Screen Map section
        text = text.replace("## Page/Screen Map", "## Something Else")
        wf_path.write_text(text, encoding="utf-8")
        
        payload_s = load_wireframe_review_inputs(temp_root, missing_sec_id)
        result_s = review_wireframe_text(payload_s["product_record"], payload_s["wireframe_text"], payload_extras=payload_s)
        expect("review status FAIL for missing section", result_s["status"] == "FAIL", failures)
        expect("missing section found in fail_reasons", "Missing required sections: Page/Screen Map" in result_s["fail_reasons"], failures)

        # 4 review fails on critical TODO/UNKNOWN.
        todo_prod = _make_wireframe_ready_product(temp_root)
        todo_id = str(todo_prod["product_id"])
        wf_path_t = temp_root / "products" / todo_id / "wireframes" / "wireframe_v1.md"
        text_t = wf_path_t.read_text(encoding="utf-8")
        text_t = text_t.replace("ASCII/Text Wireframes", "ASCII/Text Wireframes TODO/UNKNOWN")
        wf_path_t.write_text(text_t, encoding="utf-8")
        
        payload_t = load_wireframe_review_inputs(temp_root, todo_id)
        result_t = review_wireframe_text(payload_t["product_record"], payload_t["wireframe_text"], payload_extras=payload_t)
        expect("review status FAIL for critical TODO", result_t["status"] == "FAIL", failures)

        # 5 no model/provider/agent usage.
        for script_name in ("product_wireframe_review.py", "ws_product_wireframe_review.py"):
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
