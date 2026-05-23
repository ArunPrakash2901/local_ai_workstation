#!/usr/bin/env python3
"""Temp-root tests for Product Lane Phase 2 Slice 3B PRD approval."""

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
from product_prd_approval import PRD_APPROVE_ACTION, approve_prd  # noqa: E402
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


def _make_scope_locked_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} prd approval sample {uuid4().hex[:8]}",
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

def _make_prd_review_pass(root: Path, product_id: str) -> None:
    pdir = root / "products" / product_id
    prd_file = pdir / "prd.md"
    text = prd_file.read_text(encoding="utf-8")
    patched = text.replace("TODO/UNKNOWN", "Operator-provided value")
    prd_file.write_text(patched, encoding="utf-8", newline="\n")

    # Update hash in metadata
    new_hash = hashlib.sha256(patched.encode("utf-8")).hexdigest()
    product_file = pdir / "product.yaml"
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    payload["active_prd_hash"] = new_hash
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run_prd_approve_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_prd_approve.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product PRD Approval Validation")
    print("===============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_prd_approval_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        product = _make_prd_product(temp_root, product_type="website")
        product_id = str(product["product_id"])
        pdir = temp_root / "products" / product_id
        product_file = pdir / "product.yaml"
        prd_file = pdir / "prd.md"
        scope_lock_file = pdir / "scope_lock.md"
        approval_file = pdir / "decisions" / "prd_approval.md"

        _make_prd_review_pass(temp_root, product_id)

        prd_before = prd_file.read_text(encoding="utf-8")
        scope_before = scope_lock_file.read_text(encoding="utf-8")

        # 1/2/3/4/5 approval artifact and metadata updates.
        result = approve_prd(temp_root, product_id, confirm=True)
        expect("approve_prd writes decisions/prd_approval.md", approval_file.is_file(), failures)
        expect("approve_prd creates decisions directory", (pdir / "decisions").is_dir(), failures)
        updated = json.loads(product_file.read_text(encoding="utf-8"))
        expect("approve_prd sets prd_status=APPROVED", updated.get("prd_status") == "APPROVED", failures)
        expect(
            "approve_prd sets prd_reviewed_at and prd_approved_at",
            isinstance(updated.get("prd_reviewed_at"), str)
            and bool(updated.get("prd_reviewed_at"))
            and isinstance(updated.get("prd_approved_at"), str)
            and bool(updated.get("prd_approved_at")),
            failures,
        )
        expect("main product state remains SCOPE_LOCKED", updated.get("state") == "SCOPE_LOCKED", failures)
        expect("last_action updated", updated.get("last_action") == PRD_APPROVE_ACTION, failures)

        # 13/14 prd and scope lock content unchanged.
        expect("approval does not modify prd.md", prd_file.read_text(encoding="utf-8") == prd_before, failures)
        expect(
            "approval does not modify scope_lock.md",
            scope_lock_file.read_text(encoding="utf-8") == scope_before,
            failures,
        )

        # 12 duplicate approval refusal.
        try:
            approve_prd(temp_root, product_id, confirm=True)
            failures.append("FAIL: duplicate approval should be rejected")
        except FileExistsError:
            print("PASS: duplicate approval rejected")

        # 6 missing prd.md refused.
        missing_prd = _make_scope_locked_product(temp_root, product_type="webapp")
        missing_prd_id = str(missing_prd["product_id"])
        try:
            approve_prd(temp_root, missing_prd_id, confirm=True)
            failures.append("FAIL: missing prd.md should be rejected")
        except FileNotFoundError:
            print("PASS: missing prd.md rejected")

        # 7 missing scope_lock.md refused.
        missing_lock = _make_prd_product(temp_root, product_type="dashboard")
        missing_lock_id = str(missing_lock["product_id"])
        (temp_root / "products" / missing_lock_id / "scope_lock.md").unlink()
        try:
            approve_prd(temp_root, missing_lock_id, confirm=True)
            failures.append("FAIL: missing scope_lock.md should be rejected")
        except FileNotFoundError:
            print("PASS: missing scope_lock.md rejected")

        # 8 missing scope_lock_hash refused.
        missing_hash = _make_prd_product(temp_root, product_type="automation")
        missing_hash_id = str(missing_hash["product_id"])
        missing_hash_file = temp_root / "products" / missing_hash_id / "product.yaml"
        missing_hash_payload = json.loads(missing_hash_file.read_text(encoding="utf-8"))
        missing_hash_payload["scope_lock_hash"] = None
        missing_hash_file.write_text(json.dumps(missing_hash_payload, indent=2) + "\n", encoding="utf-8")
        try:
            approve_prd(temp_root, missing_hash_id, confirm=True)
            failures.append("FAIL: missing scope_lock_hash should be rejected")
        except ValueError:
            print("PASS: missing scope_lock_hash rejected")

        # 9 non-SCOPE_LOCKED refused.
        wrong_state = _make_prd_product(temp_root, product_type="video-script")
        wrong_state_id = str(wrong_state["product_id"])
        wrong_state_file = temp_root / "products" / wrong_state_id / "product.yaml"
        wrong_state_payload = json.loads(wrong_state_file.read_text(encoding="utf-8"))
        wrong_state_payload["state"] = "SCOPE_READY"
        wrong_state_file.write_text(json.dumps(wrong_state_payload, indent=2) + "\n", encoding="utf-8")
        try:
            approve_prd(temp_root, wrong_state_id, confirm=True)
            failures.append("FAIL: non-SCOPE_LOCKED product should be rejected")
        except ValueError:
            print("PASS: non-SCOPE_LOCKED product rejected")

        # 10 review WARN refused.
        warn_case = _make_prd_product(temp_root, product_type="website")
        warn_id = str(warn_case["product_id"])
        warn_prd = temp_root / "products" / warn_id / "prd.md"
        warn_text = warn_prd.read_text(encoding="utf-8").replace(
            "## Goals\n\n- ",
            "## Goals\n\n- TODO/UNKNOWN\n- ",
            1,
        )
        warn_prd.write_text(warn_text, encoding="utf-8", newline="\n")
        try:
            approve_prd(temp_root, warn_id, confirm=True)
            failures.append("FAIL: review WARN should be rejected")
        except ValueError:
            print("PASS: review WARN rejected")

        # 11 review FAIL refused.
        fail_case = _make_prd_product(temp_root, product_type="website")
        fail_id = str(fail_case["product_id"])
        fail_prd = temp_root / "products" / fail_id / "prd.md"
        fail_text = fail_prd.read_text(encoding="utf-8").replace("## Goals", "## Goals Missing", 1)
        fail_prd.write_text(fail_text, encoding="utf-8", newline="\n")
        try:
            approve_prd(temp_root, fail_id, confirm=True)
            failures.append("FAIL: review FAIL should be rejected")
        except ValueError:
            print("PASS: review FAIL rejected")

        # 15/16/17 no downstream artifacts.
        for forbidden in ("wireframes.md", "technical_plan.md", "build_plan.md"):
            expect(f"{forbidden} is not created", not (pdir / forbidden).exists(), failures)

        # 18 writes bounded under products/.
        files = sorted(
            path.relative_to(temp_root).as_posix()
            for path in temp_root.rglob("*")
            if path.is_file()
        )
        outside_products = [item for item in files if not item.startswith("products/")]
        expect(
            "approval writes remain under products/<product_id>/",
            not outside_products,
            failures,
            detail=f"outside={outside_products}",
        )

        # 19 command helper requires --confirm.
        cli_case = _make_prd_product(temp_root, product_type="website")
        cli_id = str(cli_case["product_id"])
        _make_prd_review_pass(temp_root, cli_id)
        no_confirm = _run_prd_approve_script(["--product", cli_id], temp_root)
        expect(
            "ws product-prd-approve requires --confirm",
            no_confirm.returncode != 0 and "--confirm" in ((no_confirm.stderr or "") + (no_confirm.stdout or "")),
            failures,
            detail=f"rc={no_confirm.returncode}, stderr={no_confirm.stderr!r}",
        )
        with_confirm = _run_prd_approve_script(["--product", cli_id, "--confirm"], temp_root)
        expect(
            "ws product-prd-approve --confirm succeeds",
            with_confirm.returncode == 0
            and "PRD APPROVED" in (with_confirm.stdout or "")
            and "PRD status: APPROVED" in (with_confirm.stdout or ""),
            failures,
            detail=f"rc={with_confirm.returncode}, stderr={with_confirm.stderr!r}",
        )

        # 20 no model/provider/agent usage tokens in scripts.
        for script_name in ("product_prd_approval.py", "ws_product_prd_approve.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        expect(
            "helper reports no model/provider/agent usage",
            result.get("used_model_provider_agent") is False,
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
