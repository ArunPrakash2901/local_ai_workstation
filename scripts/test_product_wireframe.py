#!/usr/bin/env python3
"""Temp-root tests for Product Lane Phase 2 Slice 4 wireframe dry-run preview."""

from __future__ import annotations

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
from product_scope_revision import confirm_scope_revision  # noqa: E402
from product_prd_revision import confirm_prd_revision  # noqa: E402
from product_scope_lock import compute_scope_lock_hash, lock_scope  # noqa: E402
import hashlib  # noqa: E402
from product_wireframe import (  # noqa: E402
    NON_UI_PRODUCT_MESSAGE,
    load_wireframe_inputs,
    render_wireframe_preview,
    confirm_wireframe,
)


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


def _make_scope_locked_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} wireframe sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    record["state"] = "INBOX"
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _make_prd_approved_product(root: Path, *, product_type: str) -> dict[str, object]:
    locked = _make_scope_locked_product(root, product_type=product_type)
    product_id = str(locked["product_id"])
    write_prd(root, product_id, confirm=True)

    pdir = root / "products" / product_id
    product_file = pdir / "product.yaml"
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    payload["prd_status"] = "APPROVED"
    payload["prd_reviewed_at"] = "2026-01-01T00:00:00Z"
    payload["prd_approved_at"] = "2026-01-01T00:00:00Z"
    payload["prd_review_notes"] = "deterministic test approval"
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return get_product_status(root, product_id)


def _make_active_revised_product(root: Path) -> dict[str, object]:
    record = _make_prd_approved_product(root, product_type="website")
    product_id = str(record["product_id"])
    pdir = root / "products" / product_id
    
    # 1. Scope Change
    product_file = pdir / "product.yaml"
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    payload["scope_change_pending"] = True
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    
    decisions_dir = pdir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    (decisions_dir / "scope_change_test.md").write_text(
        "- change_id: test\n- reason: testing\n- field: out_of_scope\n- proposed_value: revised out of scope",
        encoding="utf-8"
    )
    
    confirm_scope_revision(root, product_id, confirm=True)
    
    # 2. PRD Revision
    confirm_prd_revision(root, product_id, confirm=True)
    
    # 3. Approve Revised PRD
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    payload["prd_status"] = "APPROVED"
    payload["prd_approved_at"] = "2026-01-01T00:00:00Z"
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    
    return get_product_status(root, product_id)


def _run_wireframe_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_wireframe.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product Wireframe Validation")
    print("============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_wireframe_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        # 1 website preview renders.
        website = _make_prd_approved_product(temp_root, product_type="website")
        website_id = str(website["product_id"])
        website_payload = load_wireframe_inputs(temp_root, website_id)
        website_preview = render_wireframe_preview(
            website_payload["product_record"],
            website_payload["scope_text"],
            website_payload["prd_text"],
            payload_extras=website_payload,
        )
        expect("wireframe preview renders for website", "Wireframe Preview" in website_preview and "Home" in website_preview, failures)

        # 22 active_prd + active_scope_lock binding.
        revised = _make_active_revised_product(temp_root)
        revised_id = str(revised["product_id"])
        revised_payload = load_wireframe_inputs(temp_root, revised_id)
        revised_preview = render_wireframe_preview(
            revised_payload["product_record"],
            revised_payload["scope_text"],
            revised_payload["prd_text"],
            payload_extras=revised_payload,
        )
        
        expect("dry-run uses active_prd when present", revised_payload["prd_source"] == "active_prd", failures)
        expect("dry-run uses active_scope_lock when present", revised_payload["scope_source"] == "active_scope_lock", failures)
        expect("dry-run output includes active PRD path", "prd_path: prds/prd_v2.md" in revised_preview, failures)
        expect("dry-run output includes active scope lock path", "scope_path: scope_locks/scope_lock_v2.md" in revised_preview, failures)
        expect("dry-run hash status MATCH", "prd_hash_status: MATCH" in revised_preview and "scope_hash_status: MATCH" in revised_preview, failures)

        # 23 active_prd hash mismatch fails.
        mismatch_prd = _make_active_revised_product(temp_root)
        mismatch_id = str(mismatch_prd["product_id"])
        mismatch_file = temp_root / "products" / mismatch_id / "product.yaml"
        mismatch_payload = json.loads(mismatch_file.read_text(encoding="utf-8"))
        mismatch_payload["active_prd_hash"] = "wrong"
        mismatch_file.write_text(json.dumps(mismatch_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_wireframe_inputs(temp_root, mismatch_id)
            failures.append("FAIL: active_prd hash mismatch should be rejected")
        except ValueError as exc:
            expect("active_prd hash mismatch rejected", "PRD hash mismatch" in str(exc), failures)

        # 24 active_scope_lock hash mismatch fails.
        mismatch_scope = _make_active_revised_product(temp_root)
        mismatch_scope_id = str(mismatch_scope["product_id"])
        mismatch_scope_file = temp_root / "products" / mismatch_scope_id / "product.yaml"
        mismatch_scope_payload = json.loads(mismatch_scope_file.read_text(encoding="utf-8"))
        mismatch_scope_payload["active_scope_lock_hash"] = "wrong"
        mismatch_scope_file.write_text(json.dumps(mismatch_scope_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_wireframe_inputs(temp_root, mismatch_scope_id)
            failures.append("FAIL: active_scope_lock hash mismatch should be rejected")
        except ValueError as exc:
            expect("active_scope_lock hash mismatch rejected", "Scope lock hash mismatch" in str(exc), failures)

        # 25 missing active_prd fails.
        missing_active_prd = _make_active_revised_product(temp_root)
        missing_active_id = str(missing_active_prd["product_id"])
        (temp_root / "products" / missing_active_id / "prds" / "prd_v2.md").unlink()
        try:
            load_wireframe_inputs(temp_root, missing_active_id)
            failures.append("FAIL: missing active_prd file should be rejected")
        except FileNotFoundError:
            print("PASS: missing active_prd file rejected")

        # 26 missing active_scope_lock fails.
        missing_active_scope = _make_active_revised_product(temp_root)
        missing_active_scope_id = str(missing_active_scope["product_id"])
        (temp_root / "products" / missing_active_scope_id / "scope_locks" / "scope_lock_v2.md").unlink()
        try:
            load_wireframe_inputs(temp_root, missing_active_scope_id)
            failures.append("FAIL: missing active_scope_lock file should be rejected")
        except FileNotFoundError:
            print("PASS: missing active_scope_lock file rejected")

        # 27 stale PRD fails.
        stale_prd = _make_prd_approved_product(temp_root, product_type="website")
        stale_id = str(stale_prd["product_id"])
        stale_file = temp_root / "products" / stale_id / "product.yaml"
        stale_payload = json.loads(stale_file.read_text(encoding="utf-8"))
        stale_payload["prd_status"] = "STALE"
        stale_file.write_text(json.dumps(stale_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_wireframe_inputs(temp_root, stale_id)
            failures.append("FAIL: stale PRD should be rejected")
        except ValueError as exc:
            expect("stale PRD rejected", "stale or needs revision" in str(exc), failures)

        # 2 webapp preview renders.
        webapp = _make_prd_approved_product(temp_root, product_type="webapp")
        webapp_id = str(webapp["product_id"])
        webapp_payload = load_wireframe_inputs(temp_root, webapp_id)
        webapp_preview = render_wireframe_preview(
            webapp_payload["product_record"],
            webapp_payload["scope_text"],
            webapp_payload["prd_text"],
            payload_extras=webapp_payload,
        )
        expect("wireframe preview renders for webapp", "Main Workflow" in webapp_preview and "Landing / Entry" in webapp_preview, failures)

        # 3 dashboard preview renders.
        dashboard = _make_prd_approved_product(temp_root, product_type="dashboard")
        dashboard_id = str(dashboard["product_id"])
        dashboard_payload = load_wireframe_inputs(temp_root, dashboard_id)
        dashboard_preview = render_wireframe_preview(
            dashboard_payload["product_record"],
            dashboard_payload["scope_text"],
            dashboard_payload["prd_text"],
            payload_extras=dashboard_payload,
        )
        expect(
            "wireframe preview renders for dashboard",
            "Overview" in dashboard_preview and "Main Visualization Area" in dashboard_preview,
            failures,
        )

        # 4 non-UI rejected/clear message.
        non_ui = _make_prd_approved_product(temp_root, product_type="automation")
        try:
            load_wireframe_inputs(temp_root, str(non_ui["product_id"]))
            failures.append("FAIL: non-UI product type should be rejected")
        except ValueError as exc:
            expect(
                "non-UI product type returns clear non-applicable message",
                NON_UI_PRODUCT_MESSAGE in str(exc),
                failures,
            )

        # 5 command requires SCOPE_LOCKED.
        non_locked = _make_prd_approved_product(temp_root, product_type="website")
        non_locked_id = str(non_locked["product_id"])
        non_locked_file = temp_root / "products" / non_locked_id / "product.yaml"
        non_locked_payload = json.loads(non_locked_file.read_text(encoding="utf-8"))
        non_locked_payload["state"] = "SCOPE_READY"
        non_locked_file.write_text(json.dumps(non_locked_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_wireframe_inputs(temp_root, non_locked_id)
            failures.append("FAIL: non-SCOPE_LOCKED should be rejected")
        except ValueError:
            print("PASS: command requires SCOPE_LOCKED")

        # 6 command requires prd_status=APPROVED.
        non_approved = _make_prd_approved_product(temp_root, product_type="website")
        non_approved_id = str(non_approved["product_id"])
        non_approved_file = temp_root / "products" / non_approved_id / "product.yaml"
        non_approved_payload = json.loads(non_approved_file.read_text(encoding="utf-8"))
        non_approved_payload["prd_status"] = "DRAFTED"
        non_approved_file.write_text(json.dumps(non_approved_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_wireframe_inputs(temp_root, non_approved_id)
            failures.append("FAIL: prd_status not APPROVED should be rejected")
        except ValueError:
            print("PASS: command requires prd_status=APPROVED")

        # 7 command refuses missing prd.md.
        missing_prd = _make_prd_approved_product(temp_root, product_type="website")
        missing_prd_id = str(missing_prd["product_id"])
        (temp_root / "products" / missing_prd_id / "prd.md").unlink()
        try:
            load_wireframe_inputs(temp_root, missing_prd_id)
            failures.append("FAIL: missing prd.md should be rejected")
        except FileNotFoundError:
            print("PASS: missing prd.md rejected")

        # 8 command refuses missing scope_lock.md.
        missing_lock = _make_prd_approved_product(temp_root, product_type="website")
        missing_lock_id = str(missing_lock["product_id"])
        (temp_root / "products" / missing_lock_id / "scope_lock.md").unlink()
        try:
            load_wireframe_inputs(temp_root, missing_lock_id)
            failures.append("FAIL: missing scope_lock.md should be rejected")
        except FileNotFoundError:
            print("PASS: missing scope_lock.md rejected")

        # 9 command refuses missing scope_lock_hash.
        missing_hash = _make_prd_approved_product(temp_root, product_type="website")
        missing_hash_id = str(missing_hash["product_id"])
        missing_hash_file = temp_root / "products" / missing_hash_id / "product.yaml"
        missing_hash_payload = json.loads(missing_hash_file.read_text(encoding="utf-8"))
        missing_hash_payload["scope_lock_hash"] = None
        missing_hash_payload["active_scope_lock_hash"] = None
        missing_hash_file.write_text(json.dumps(missing_hash_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_wireframe_inputs(temp_root, missing_hash_id)
            failures.append("FAIL: missing scope_lock_hash should be rejected")
        except ValueError:
            print("PASS: missing scope_lock_hash rejected")

        # 10 preview includes DRY RUN / no files written.
        expect(
            "preview includes DRY RUN / no files written",
            "DRY RUN - no files written." in website_preview,
            failures,
        )

        # 11 preview includes generated_from section.
        expect(
            "preview includes generated_from section",
            "## Generated From" in website_preview and "- product.yaml" in website_preview and "- prd.md" in website_preview,
            failures,
        )

        # 12 preview includes page/screen map.
        expect(
            "preview includes page/screen map",
            "## Page/Screen Map" in website_preview,
            failures,
        )

        # 13 preview includes text/ASCII wireframe section.
        expect(
            "preview includes text/ASCII wireframe section",
            "## ASCII/Text Wireframes" in website_preview and "+------------------------------------------------------------+" in website_preview,
            failures,
        )

        # 14 preview uses TODO/UNKNOWN when uncertain.
        expect(
            "preview uses TODO/UNKNOWN or None for unresolved questions",
            "TODO/UNKNOWN" in website_preview or "Unresolved Design Questions" in website_preview,
            failures,
        )

        # 15/16/17/18/19 no-write guarantees.
        no_write = _make_prd_approved_product(temp_root, product_type="website")
        no_write_id = str(no_write["product_id"])
        no_write_dir = temp_root / "products" / no_write_id
        no_write_product_file = no_write_dir / "product.yaml"
        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        before_product_yaml = no_write_product_file.read_text(encoding="utf-8")

        no_write_payload = load_wireframe_inputs(temp_root, no_write_id)
        _ = render_wireframe_preview(
            no_write_payload["product_record"],
            no_write_payload["scope_text"],
            no_write_payload["prd_text"],
            payload_extras=no_write_payload,
        )

        after_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("preview writes no files", before_files == after_files, failures)
        expect(
            "no product.yaml update occurs",
            before_product_yaml == no_write_product_file.read_text(encoding="utf-8"),
            failures,
        )
        expect("no wireframes.md created", not (no_write_dir / "wireframes.md").exists(), failures)
        expect("no ux_spec.md created", not (no_write_dir / "ux_spec.md").exists(), failures)
        expect("no technical_plan.md created", not (no_write_dir / "technical_plan.md").exists(), failures)

        # 20 no model/provider/agent usage occurs.
        for script_name in ("product_wireframe.py", "ws_product_wireframe.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        # 21 command helper requires mode flag.
        no_mode_cli = _run_wireframe_script(["--product", website_id], temp_root)
        expect(
            "command helper requires mode flag",
            no_mode_cli.returncode != 0,
            failures,
            detail=f"rc={no_mode_cli.returncode}, stderr={no_mode_cli.stderr!r}",
        )
        with_dry_run = _run_wireframe_script(["--product", website_id, "--dry-run"], temp_root)
        expect(
            "command helper succeeds with --dry-run",
            with_dry_run.returncode == 0
            and "Wireframe Preview" in (with_dry_run.stdout or "")
            and "DRY RUN - no files written." in (with_dry_run.stdout or ""),
            failures,
            detail=f"rc={with_dry_run.returncode}, stderr={with_dry_run.stderr!r}",
        )

        # 28 confirm writes wireframe_v1.md.
        confirm_product = _make_prd_approved_product(temp_root, product_type="website")
        confirm_id = str(confirm_product["product_id"])
        confirm_dir = temp_root / "products" / confirm_id

        result = confirm_wireframe(temp_root, confirm_id, confirm=True)

        expect("confirm writes wireframe_v1.md", (confirm_dir / "wireframes" / "wireframe_v1.md").is_file(), failures)

        post_record = get_product_status(temp_root, confirm_id)
        expect("confirm updates active_wireframe", post_record.get("active_wireframe") == "wireframes/wireframe_v1.md", failures)
        expect("confirm updates active_wireframe_hash", bool(post_record.get("active_wireframe_hash")), failures)
        expect("confirm updates active_wireframe_revision to 1", post_record.get("active_wireframe_revision") == 1, failures)
        expect("confirm sets wireframe_status DRAFTED", post_record.get("wireframe_status") == "DRAFTED", failures)

        # 29 confirm refuses duplicate wireframe_v1.md.
        try:
            confirm_wireframe(temp_root, confirm_id, confirm=True)
            failures.append("FAIL: confirm refuses duplicate wireframe_v1.md")
        except FileExistsError:
            print("PASS: confirm refuses duplicate wireframe_v1.md")

        # 30 confirm refuses unapproved PRD.
        unapproved = _make_scope_locked_product(temp_root, product_type="website")
        unapproved_id = str(unapproved["product_id"])
        write_prd(temp_root, unapproved_id, confirm=True)
        try:
            confirm_wireframe(temp_root, unapproved_id, confirm=True)
            failures.append("FAIL: confirm refuses unapproved PRD")
        except ValueError as exc:
            expect("unapproved PRD rejected", "requires prd_status=APPROVED" in str(exc), failures)

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
