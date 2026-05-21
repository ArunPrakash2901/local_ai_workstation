#!/usr/bin/env python3
"""Temp-root tests for Product Lane Phase 2 Slice 3A PRD review dry-run."""

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
from product_prd_review import (  # noqa: E402
    PRD_APPROVE_ACTION_FUTURE,
    detect_missing_prd_sections,
    load_prd_review_inputs,
    render_prd_review_report,
    review_prd_text,
)
from product_registry import create_product, get_product_status, initialize_products_dir, save_product  # noqa: E402
from product_scope_lock import lock_scope  # noqa: E402


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
        question_id = str(question["id"])
        lines.append(f"{question_id}: answer for {question_id}")
    return "\n".join(lines) + "\n"


def _make_locked_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} prd review sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    record["state"] = "INBOX"
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _make_prd_ready_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    locked = _make_locked_product(root, product_type=product_type)
    write_prd(root, str(locked["product_id"]), confirm=True)
    return get_product_status(root, str(locked["product_id"]))


def _run_prd_review_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_prd_review.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product PRD Review Validation")
    print("=============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_prd_review_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        ready = _make_prd_ready_product(temp_root, product_type="website")
        product_id = str(ready["product_id"])
        pdir = temp_root / "products" / product_id
        product_file = pdir / "product.yaml"
        prd_file = pdir / "prd.md"
        scope_lock_file = pdir / "scope_lock.md"

        # 1 review passes for complete deterministic prd.md.
        payload = load_prd_review_inputs(temp_root, product_id)
        review = review_prd_text(payload["product_record"], payload["scope_lock_text"], payload["prd_text"])
        complete_text = payload["prd_text"].replace(
            "## Out of Scope\n\n- TODO/UNKNOWN\n",
            "## Out of Scope\n\n- No backend/CMS/authentication in this PRD slice.\n",
            1,
        )
        complete_review = review_prd_text(payload["product_record"], payload["scope_lock_text"], complete_text)
        expect("review passes for complete deterministic prd.md", complete_review["status"] == "PASS", failures)

        # 2 review fails for missing prd.md.
        missing_prd = _make_locked_product(temp_root, product_type="webapp")
        missing_prd_id = str(missing_prd["product_id"])
        try:
            load_prd_review_inputs(temp_root, missing_prd_id)
            failures.append("FAIL: missing prd.md should be rejected")
        except FileNotFoundError:
            print("PASS: missing prd.md rejected")

        # 3 review fails for non-SCOPE_LOCKED product.
        inbox = create_product(title=f"inbox review {uuid4().hex[:8]}", product_type="dashboard")
        save_product(inbox, temp_root, confirm=True, allow_overwrite=False)
        try:
            load_prd_review_inputs(temp_root, str(inbox["product_id"]))
            failures.append("FAIL: non-SCOPE_LOCKED product should be rejected")
        except ValueError:
            print("PASS: non-SCOPE_LOCKED product rejected")

        # 4 review fails for missing scope_lock.md.
        missing_lock = _make_prd_ready_product(temp_root, product_type="automation")
        missing_lock_id = str(missing_lock["product_id"])
        (temp_root / "products" / missing_lock_id / "scope_lock.md").unlink()
        try:
            load_prd_review_inputs(temp_root, missing_lock_id)
            failures.append("FAIL: missing scope_lock.md should be rejected")
        except FileNotFoundError:
            print("PASS: missing scope_lock.md rejected")

        # 5 review fails for missing scope_lock_hash.
        missing_hash = _make_prd_ready_product(temp_root, product_type="video-script")
        missing_hash_id = str(missing_hash["product_id"])
        missing_hash_file = temp_root / "products" / missing_hash_id / "product.yaml"
        payload_hash = json.loads(missing_hash_file.read_text(encoding="utf-8"))
        payload_hash["scope_lock_hash"] = None
        missing_hash_file.write_text(json.dumps(payload_hash, indent=2) + "\n", encoding="utf-8")
        try:
            load_prd_review_inputs(temp_root, missing_hash_id)
            failures.append("FAIL: missing scope_lock_hash should be rejected")
        except ValueError:
            print("PASS: missing scope_lock_hash rejected")

        # 6 review detects missing required sections.
        modified = prd_file.read_text(encoding="utf-8").replace("## Goals", "## Goals Missing", 1)
        missing_sections = detect_missing_prd_sections(modified)
        expect(
            "review detects missing required sections",
            "Goals" in missing_sections,
            failures,
        )
        missing_section_review = review_prd_text(ready, scope_lock_file.read_text(encoding="utf-8"), modified)
        expect(
            "missing required sections produce FAIL status",
            missing_section_review["status"] == "FAIL",
            failures,
        )

        # 7 review detects TODO/UNKNOWN in critical sections as WARN.
        warn_text = prd_file.read_text(encoding="utf-8").replace(
            "## Goals\n\n- ",
            "## Goals\n\n- TODO/UNKNOWN\n- ",
            1,
        )
        warn_review = review_prd_text(ready, scope_lock_file.read_text(encoding="utf-8"), warn_text)
        expect(
            "critical TODO/UNKNOWN yields WARN",
            warn_review["status"] == "WARN" and "Goals" in warn_review["critical_todos"],
            failures,
        )

        # 8 review report includes no-write / no-model notice and next step.
        report = render_prd_review_report(ready, complete_review, prd_path=prd_file)
        expect(
            "review report includes no-write and no-model notices",
            "DRY RUN - no files written." in report and "No model/provider/agent calls." in report,
            failures,
        )
        expect(
            "review report includes future approve next step",
            PRD_APPROVE_ACTION_FUTURE in report,
            failures,
        )

        # 9/10/11 review writes no files and does not update product.yaml or create artifact.
        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        product_before = product_file.read_text(encoding="utf-8")
        _ = load_prd_review_inputs(temp_root, product_id)
        _ = review_prd_text(ready, scope_lock_file.read_text(encoding="utf-8"), prd_file.read_text(encoding="utf-8"))
        _ = render_prd_review_report(ready, review, prd_path=prd_file)
        after_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("review writes no files", before_files == after_files, failures)
        expect("review does not update product.yaml", product_before == product_file.read_text(encoding="utf-8"), failures)
        expect("review artifact is not created", not (pdir / "prd_review.md").exists(), failures)

        # 12 no model/provider/agent usage occurs.
        for script_name in ("product_prd_review.py", "ws_product_prd_review.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        # 13 command helper requires --dry-run.
        no_dry_run = _run_prd_review_script(["--product", product_id], temp_root)
        expect(
            "ws product-prd-review requires --dry-run",
            no_dry_run.returncode != 0 and "Use --dry-run." in (no_dry_run.stderr or ""),
            failures,
            detail=f"rc={no_dry_run.returncode}, stderr={no_dry_run.stderr!r}",
        )
        with_dry_run = _run_prd_review_script(["--product", product_id, "--dry-run"], temp_root)
        expect(
            "ws product-prd-review --dry-run succeeds",
            with_dry_run.returncode == 0
            and "# PRD Review Report:" in (with_dry_run.stdout or "")
            and "DRY RUN - no files written." in (with_dry_run.stdout or ""),
            failures,
            detail=f"rc={with_dry_run.returncode}, stderr={with_dry_run.stderr!r}",
        )

        # 14 unsupported product type rejected.
        unsupported = _make_prd_ready_product(temp_root, product_type="cover-letter")
        unsupported_id = str(unsupported["product_id"])
        unsupported_file = temp_root / "products" / unsupported_id / "product.yaml"
        unsupported_payload = json.loads(unsupported_file.read_text(encoding="utf-8"))
        unsupported_payload["product_type"] = "unsupported-type"
        unsupported_payload["type"] = "unsupported-type"
        unsupported_file.write_text(json.dumps(unsupported_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_prd_review_inputs(temp_root, unsupported_id)
            failures.append("FAIL: unsupported product type should be rejected")
        except ValueError:
            print("PASS: unsupported product type rejected")

        # 15 report includes future approval next step command.
        expect(
            "next step references future approval command",
            "ws product-prd-approve --confirm" in report,
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
