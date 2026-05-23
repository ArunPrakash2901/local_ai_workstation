#!/usr/bin/env python3
"""Temp-root tests for Product Lane technical plan preview and confirm."""

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
from product_tech_plan import confirm_tech_plan, render_tech_plan_preview, validate_tech_plan_preconditions  # noqa: E402
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


def _hydrate_prd_and_scope_metadata(root: Path, product_id: str) -> None:
    pdir = root / "products" / product_id
    prd_path = pdir / "prd.md"
    scope_path = pdir / "scope_lock.md"
    product_file = pdir / "product.yaml"
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    payload["active_prd"] = "prd.md"
    payload["active_prd_hash"] = hashlib.sha256(prd_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    payload["active_prd_revision"] = 1
    payload["active_scope_lock"] = "scope_lock.md"
    payload["active_scope_lock_hash"] = compute_scope_lock_hash(scope_path.read_text(encoding="utf-8"))
    payload["active_scope_revision"] = 1
    payload["prd_status"] = "APPROVED"
    payload["prd_approved_at"] = "2026-01-01T00:00:00Z"
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _make_tech_plan_ready_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} tech plan sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    write_prd(root, str(record["product_id"]), confirm=True)
    _hydrate_prd_and_scope_metadata(root, str(record["product_id"]))
    confirm_wireframe(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _run_ws_tech_plan(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_tech_plan.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product Technical Plan Validation")
    print("================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_tech_plan_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        ready = _make_tech_plan_ready_product(temp_root)
        product_id = str(ready["product_id"])
        pdir = temp_root / "products" / product_id
        scope_before = (pdir / "scope_lock.md").read_text(encoding="utf-8")
        prd_before = (pdir / "prd.md").read_text(encoding="utf-8")
        wireframe_before = (pdir / "wireframes" / "wireframe_v1.md").read_text(encoding="utf-8")

        dry_payload = validate_tech_plan_preconditions(temp_root, product_id, require_wireframe_review_pass=False)
        dry_output = render_tech_plan_preview(dry_payload)
        expect("tech-plan dry-run preconditions pass", "Technical Plan Preview" in dry_output, failures)

        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        confirm_result = confirm_tech_plan(temp_root, product_id, confirm=True)
        after_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        product_after = json.loads((pdir / "product.yaml").read_text(encoding="utf-8"))

        expect("confirm writes technical_plans/technical_plan_v1.md", (pdir / "technical_plans" / "technical_plan_v1.md").is_file(), failures)
        expect("confirm updates active_technical_plan metadata", product_after.get("active_technical_plan") == "technical_plans/technical_plan_v1.md", failures, detail=str(product_after.get("active_technical_plan")))
        expect("confirm updates active_technical_plan_hash", isinstance(product_after.get("active_technical_plan_hash"), str) and len(product_after["active_technical_plan_hash"]) == 64, failures)
        expect("confirm sets active_technical_plan_revision to 1", product_after.get("active_technical_plan_revision") == 1, failures)
        expect("confirm sets technical_plan_status DRAFTED", product_after.get("technical_plan_status") == "DRAFTED", failures)
        expect("confirm keeps state SCOPE_LOCKED", product_after.get("state") == "SCOPE_LOCKED", failures)
        expect("confirm keeps prd_status APPROVED", product_after.get("prd_status") == "APPROVED", failures)
        expect("confirm does not modify scope_lock.md", (pdir / "scope_lock.md").read_text(encoding="utf-8") == scope_before, failures)
        expect("confirm does not modify prd.md", (pdir / "prd.md").read_text(encoding="utf-8") == prd_before, failures)
        expect("confirm does not modify wireframe artifact", (pdir / "wireframes" / "wireframe_v1.md").read_text(encoding="utf-8") == wireframe_before, failures)
        expect("confirm writes remain under product directory", all(path.startswith(f"products/{product_id}/") for path in set(after_files) - set(before_files)), failures, detail=str(sorted(set(after_files) - set(before_files))))
        expect("confirm reports files written", bool(confirm_result.get("files_written")), failures)

        try:
            confirm_tech_plan(temp_root, product_id, confirm=True)
            failures.append("FAIL: confirm refuses duplicate technical plan")
        except FileExistsError:
            print("PASS: confirm refuses duplicate technical plan")

        unapproved = _make_tech_plan_ready_product(temp_root)
        unapproved_id = str(unapproved["product_id"])
        unapproved_file = temp_root / "products" / unapproved_id / "product.yaml"
        unapproved_payload = json.loads(unapproved_file.read_text(encoding="utf-8"))
        unapproved_payload["prd_status"] = "DRAFTED"
        unapproved_file.write_text(json.dumps(unapproved_payload, indent=2) + "\n", encoding="utf-8")
        try:
            confirm_tech_plan(temp_root, unapproved_id, confirm=True)
            failures.append("FAIL: confirm refuses unapproved inputs")
        except ValueError:
            print("PASS: confirm refuses unapproved inputs")

        stale_prd = _make_tech_plan_ready_product(temp_root)
        stale_prd_id = str(stale_prd["product_id"])
        stale_file = temp_root / "products" / stale_prd_id / "product.yaml"
        stale_payload = json.loads(stale_file.read_text(encoding="utf-8"))
        stale_payload["active_prd_hash"] = "0" * 64
        stale_file.write_text(json.dumps(stale_payload, indent=2) + "\n", encoding="utf-8")
        try:
            confirm_tech_plan(temp_root, stale_prd_id, confirm=True)
            failures.append("FAIL: confirm refuses hash-mismatched active_prd")
        except ValueError:
            print("PASS: confirm refuses hash-mismatched active_prd")

        stale_scope = _make_tech_plan_ready_product(temp_root)
        stale_scope_id = str(stale_scope["product_id"])
        scope_file = temp_root / "products" / stale_scope_id / "product.yaml"
        scope_payload = json.loads(scope_file.read_text(encoding="utf-8"))
        scope_payload["active_scope_lock_hash"] = "1" * 64
        scope_file.write_text(json.dumps(scope_payload, indent=2) + "\n", encoding="utf-8")
        try:
            confirm_tech_plan(temp_root, stale_scope_id, confirm=True)
            failures.append("FAIL: confirm refuses hash-mismatched active_scope_lock")
        except ValueError:
            print("PASS: confirm refuses hash-mismatched active_scope_lock")

        stale_wire = _make_tech_plan_ready_product(temp_root)
        stale_wire_id = str(stale_wire["product_id"])
        wire_file = temp_root / "products" / stale_wire_id / "product.yaml"
        wire_payload = json.loads(wire_file.read_text(encoding="utf-8"))
        wire_payload["active_wireframe_hash"] = "2" * 64
        wire_file.write_text(json.dumps(wire_payload, indent=2) + "\n", encoding="utf-8")
        try:
            confirm_tech_plan(temp_root, stale_wire_id, confirm=True)
            failures.append("FAIL: confirm refuses hash-mismatched active_wireframe")
        except ValueError:
            print("PASS: confirm refuses hash-mismatched active_wireframe")

        missing_wire = _make_tech_plan_ready_product(temp_root)
        missing_wire_id = str(missing_wire["product_id"])
        (temp_root / "products" / missing_wire_id / "wireframes" / "wireframe_v1.md").unlink()
        try:
            confirm_tech_plan(temp_root, missing_wire_id, confirm=True)
            failures.append("FAIL: confirm refuses missing inputs")
        except FileNotFoundError:
            print("PASS: confirm refuses missing inputs")

        for script_name in ("product_tech_plan.py", "ws_product_tech_plan.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        cli_no_mode = _run_ws_tech_plan(["--product", product_id], temp_root)
        expect(
            "CLI requires a mode flag",
            cli_no_mode.returncode != 0 and "one of the arguments --dry-run --confirm is required" in ((cli_no_mode.stderr or "") + (cli_no_mode.stdout or "")).lower(),
            failures,
            detail=f"rc={cli_no_mode.returncode}, stderr={cli_no_mode.stderr!r}",
        )
        cli_dry = _run_ws_tech_plan(["--product", product_id, "--dry-run"], temp_root)
        expect("CLI dry-run works", cli_dry.returncode == 0 and "Technical Plan Preview" in (cli_dry.stdout or ""), failures)
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
