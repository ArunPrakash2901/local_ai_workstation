#!/usr/bin/env python3
"""Temp-root tests for PURE_READ Product Lane PRD status."""

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
from product_prd_status import get_prd_status, render_prd_status  # noqa: E402
from product_registry import create_product, get_product_status, initialize_products_dir, save_product  # noqa: E402
from product_scope_change import confirm_scope_change  # noqa: E402
from product_scope_lock import lock_scope  # noqa: E402
from product_scope_revision import confirm_scope_revision  # noqa: E402


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
        title=f"{product_type} prd status sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    record["state"] = "INBOX"
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _make_prd_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    locked = _make_scope_locked_product(root, product_type=product_type)
    write_prd(root, str(locked["product_id"]), confirm=True)
    return get_product_status(root, str(locked["product_id"]))


def _make_revised_scope_prd_product(root: Path) -> dict[str, object]:
    product = _make_prd_product(root, product_type="website")
    product_id = str(product["product_id"])
    change_file = root / f"tmp_prd_status_scope_change_{uuid4().hex}.md"
    change_file.write_text(
        "\n".join(
            [
                "change_id: add-out-of-scope-for-status-test",
                "reason: status test",
                "field: out_of_scope",
                "proposed_value: >",
                "  Backend services and auth are out of scope.",
                "operator_note: test",
                "",
            ]
        ),
        encoding="utf-8",
    )
    confirm_scope_change(root, product_id, change_file, confirm=True)
    confirm_scope_revision(root, product_id, confirm=True)
    return get_product_status(root, product_id)


def _run_prd_status_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_prd_status.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product PRD Status Validation")
    print("=============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_prd_status_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        # 1 NOT_CREATED when prd.md missing.
        locked = _make_scope_locked_product(temp_root, product_type="website")
        locked_id = str(locked["product_id"])
        not_created = get_prd_status(temp_root, locked_id)
        expect("status returns NOT_CREATED when prd.md missing", not_created["prd_status_display"] == "NOT_CREATED", failures)

        # 2 DRAFTED when prd.md exists but prd_status missing.
        drafted = _make_prd_product(temp_root, product_type="webapp")
        drafted_id = str(drafted["product_id"])
        drafted_status = get_prd_status(temp_root, drafted_id)
        expect("status returns DRAFTED when prd.md exists and prd_status missing", drafted_status["prd_status_display"] == "DRAFTED", failures)

        # 3 APPROVED when product.yaml prd_status is APPROVED.
        approved = _make_prd_product(temp_root, product_type="dashboard")
        approved_id = str(approved["product_id"])
        pdir = temp_root / "products" / approved_id
        approval_dir = pdir / "decisions"
        approval_dir.mkdir(parents=True, exist_ok=True)
        (approval_dir / "prd_approval.md").write_text("# approval\n", encoding="utf-8")
        product_file = pdir / "product.yaml"
        payload = json.loads(product_file.read_text(encoding="utf-8"))
        payload["prd_status"] = "APPROVED"
        payload["prd_reviewed_at"] = "2026-01-01T00:00:00Z"
        payload["prd_approved_at"] = "2026-01-01T00:00:00Z"
        payload["prd_review_notes"] = "approved"
        product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        approved_status = get_prd_status(temp_root, approved_id)
        expect("status returns APPROVED when prd_status is APPROVED", approved_status["prd_status_display"] == "APPROVED", failures)

        # 4/5 timestamp fields surfaced.
        expect("status reports prd_created_at", bool(approved_status["prd_created_at"]), failures)
        expect("status reports prd_approved_at", approved_status["prd_approved_at"] == "2026-01-01T00:00:00Z", failures)

        # 6 approval artifact presence.
        expect("status reports approval artifact presence", approved_status["prd_approval_exists"] is True, failures)

        revised_scope = _make_revised_scope_prd_product(temp_root)
        revised_scope_id = str(revised_scope["product_id"])
        revised_scope_status = get_prd_status(temp_root, revised_scope_id)
        expect("status reports active_scope_lock", revised_scope_status.get("active_scope_lock") == "scope_locks/scope_lock_v2.md", failures)
        expect("status reports stale_artifacts", "prd.md" in list(revised_scope_status.get("stale_artifacts", [])), failures)
        expect(
            "status suggests product-prd-revision --dry-run when prd_status is NEEDS_REVISION",
            revised_scope_status.get("next_suggested_command") == f"ws product-prd-revision --product {revised_scope_id} --dry-run",
            failures,
            detail=str(revised_scope_status.get("next_suggested_command")),
        )

        # 7 missing product safe failure.
        try:
            get_prd_status(temp_root, "missing-product-id")
            failures.append("FAIL: missing product should raise")
        except FileNotFoundError:
            print("PASS: missing product raises FileNotFoundError")

        # 8/9/10 no writes, no product update, no decisions dir creation.
        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        no_write_product_file = temp_root / "products" / drafted_id / "product.yaml"
        before_product = no_write_product_file.read_text(encoding="utf-8")
        no_write_decisions_dir = temp_root / "products" / drafted_id / "decisions"
        _ = get_prd_status(temp_root, drafted_id)
        _ = render_prd_status(drafted_status)
        after_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("status writes no files", before_files == after_files, failures)
        expect("status does not update product.yaml", before_product == no_write_product_file.read_text(encoding="utf-8"), failures)
        expect("status does not create decisions dir", not no_write_decisions_dir.exists(), failures)

        # 11 no model/provider/agent usage tokens.
        for script_name in ("product_prd_status.py", "ws_product_prd_status.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        # 12 CLI requires --product according to chosen style.
        missing_arg = _run_prd_status_script([], temp_root)
        expect(
            "CLI requires --product",
            missing_arg.returncode != 0 and "--product" in ((missing_arg.stderr or "") + (missing_arg.stdout or "")),
            failures,
            detail=f"rc={missing_arg.returncode}, stderr={missing_arg.stderr!r}",
        )
        with_arg = _run_prd_status_script(["--product", drafted_id], temp_root)
        expect(
            "CLI works with --product",
            with_arg.returncode == 0
            and "Product PRD Status" in (with_arg.stdout or "")
            and "PURE_READ - no files written." in (with_arg.stdout or ""),
            failures,
            detail=f"rc={with_arg.returncode}, stderr={with_arg.stderr!r}",
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
