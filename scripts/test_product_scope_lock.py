#!/usr/bin/env python3
"""Temp-root tests for Product Lane Phase 1 Slice 5 scope lock."""

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

from product_answer_import import ANSWERS_FILENAME, import_answers  # noqa: E402
from product_intake_artifacts import INTAKE_FILENAME, QUESTIONS_FILENAME, start_intake  # noqa: E402
from product_intake_questions import get_blocking_questions, get_privacy_questions, get_required_questions  # noqa: E402
from product_registry import create_product, get_product_status, initialize_products_dir, save_product  # noqa: E402
from product_scope_lock import (  # noqa: E402
    SCOPE_LOCK_FILENAME,
    compute_scope_lock_hash,
    lock_scope,
    render_scope_lock,
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


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_answers_text(product_type: str, *, include_privacy: bool = True) -> str:
    required = get_required_questions(product_type)
    blocking = get_blocking_questions(product_type)
    privacy = get_privacy_questions(product_type) if include_privacy else []
    lines: list[str] = []
    for question in required + blocking + privacy:
        question_id = str(question["id"])
        lines.append(f"{question_id}: answer for {question_id}")
    return "\n".join(lines) + "\n"


def _make_product(root: Path, *, product_type: str = "website", state: str = "INBOX") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} lock sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    record["state"] = state
    save_product(record, root, confirm=True, allow_overwrite=False)
    return record


def _product_dir(root: Path, product_id: str) -> Path:
    return root / "products" / product_id


def _product_file(root: Path, product_id: str) -> Path:
    return _product_dir(root, product_id) / "product.yaml"


def _answers_file(root: Path, product_id: str) -> Path:
    return _product_dir(root, product_id) / ANSWERS_FILENAME


def _complete_scope_ready_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = _make_product(root, product_type=product_type, state="INBOX")
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    answers_text = _render_answers_text(product_type, include_privacy=True)
    import_answers(persisted, root, answers_text, confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _run_lock_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_lock_scope.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product Scope Lock Validation")
    print("=============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_scope_lock_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        # Baseline lock flow.
        ready = _complete_scope_ready_product(temp_root, product_type="website")
        product_id = str(ready["product_id"])
        pdir = _product_dir(temp_root, product_id)
        product_file = _product_file(temp_root, product_id)
        intake_before = (pdir / INTAKE_FILENAME).read_text(encoding="utf-8")
        questions_before = (pdir / QUESTIONS_FILENAME).read_text(encoding="utf-8")
        answers_before = _answers_file(temp_root, product_id).read_text(encoding="utf-8")

        # 5 stable hash for same rendered content.
        lock_text_a = render_scope_lock(
            ready,
            get_required_questions("website") + get_blocking_questions("website") + get_privacy_questions("website"),
            {},
            locked_at="2026-01-01T00:00:00Z",
        )
        lock_text_b = render_scope_lock(
            ready,
            get_required_questions("website") + get_blocking_questions("website") + get_privacy_questions("website"),
            {},
            locked_at="2026-01-01T00:00:00Z",
        )
        expect(
            "scope lock hash is stable for same rendered content",
            compute_scope_lock_hash(lock_text_a) == compute_scope_lock_hash(lock_text_b),
            failures,
        )

        result = lock_scope(temp_root, product_id, confirm=True)
        scope_lock_path = pdir / SCOPE_LOCK_FILENAME

        # 1 lock writes scope_lock.md
        expect("lock_scope writes scope_lock.md", scope_lock_path.is_file(), failures)

        # 2 state transition
        updated = _read_json(product_file)
        expect("state updates to SCOPE_LOCKED", updated.get("state") == "SCOPE_LOCKED", failures)

        # 3 scope_locked_at
        expect(
            "scope_locked_at recorded",
            isinstance(updated.get("scope_locked_at"), str) and bool(updated.get("scope_locked_at")),
            failures,
        )

        # 4 scope_lock_hash
        lock_hash = updated.get("scope_lock_hash")
        expect(
            "scope_lock_hash recorded",
            isinstance(lock_hash, str) and len(str(lock_hash)) == 64,
            failures,
        )
        expect(
            "result hash matches product.yaml hash",
            result.get("scope_lock_hash") == lock_hash,
            failures,
        )

        # 6 confirmation statement
        scope_text = scope_lock_path.read_text(encoding="utf-8")
        expect(
            "scope_lock.md includes operator confirmation statement",
            "I confirm this scope is the basis for downstream planning." in scope_text,
            failures,
        )

        # 7 generated_from section
        expect(
            "scope_lock.md includes generated_from",
            "## Generated From" in scope_text
            and "product.yaml" in scope_text
            and "intake.md" in scope_text
            and "questions.md" in scope_text
            and "answers.md" in scope_text,
            failures,
        )

        # 14 lock does not modify intake/questions/answers.
        expect(
            "lock does not modify intake.md",
            intake_before == (pdir / INTAKE_FILENAME).read_text(encoding="utf-8"),
            failures,
        )
        expect(
            "lock does not modify questions.md",
            questions_before == (pdir / QUESTIONS_FILENAME).read_text(encoding="utf-8"),
            failures,
        )
        expect(
            "lock does not modify answers.md",
            answers_before == _answers_file(temp_root, product_id).read_text(encoding="utf-8"),
            failures,
        )

        # 15 no downstream artifacts created.
        for forbidden in ("prd.md", "wireframes.md", "technical_plan.md", "build_plan.md"):
            expect(
                f"{forbidden} is not created",
                not (pdir / forbidden).exists(),
                failures,
            )

        # 8 missing product rejected
        try:
            lock_scope(temp_root, "missing-product", confirm=True)
            failures.append("FAIL: lock_scope should refuse missing product")
        except FileNotFoundError:
            print("PASS: lock_scope refuses missing product")

        # 9 non-SCOPE_READY rejected
        inbox_record = _make_product(temp_root, product_type="webapp", state="INBOX")
        start_intake(inbox_record, temp_root, confirm=True)
        try:
            lock_scope(temp_root, str(inbox_record["product_id"]), confirm=True)
            failures.append("FAIL: lock_scope should refuse non-SCOPE_READY state")
        except ValueError:
            print("PASS: lock_scope refuses non-SCOPE_READY state")

        # 10 missing answers.md rejected
        missing_answers = _complete_scope_ready_product(temp_root, product_type="dashboard")
        missing_id = str(missing_answers["product_id"])
        _answers_file(temp_root, missing_id).unlink()
        try:
            lock_scope(temp_root, missing_id, confirm=True)
            failures.append("FAIL: lock_scope should refuse missing answers.md")
        except FileNotFoundError:
            print("PASS: lock_scope refuses missing answers.md")

        # 11 unresolved required/blocking/privacy rejected
        unresolved = _complete_scope_ready_product(temp_root, product_type="automation")
        unresolved_id = str(unresolved["product_id"])
        answers_path = _answers_file(temp_root, unresolved_id)
        answers_text = answers_path.read_text(encoding="utf-8")
        required_id = str(get_required_questions("automation")[0]["id"])
        answers_text = answers_text.replace(f"Answer: answer for {required_id}", "Answer: (unanswered)", 1)
        answers_path.write_text(answers_text, encoding="utf-8")
        try:
            lock_scope(temp_root, unresolved_id, confirm=True)
            failures.append("FAIL: lock_scope should refuse unresolved required/blocking/privacy answers")
        except ValueError:
            print("PASS: lock_scope refuses unresolved required/blocking/privacy answers")

        # 12 existing scope lock rejected
        existing = _complete_scope_ready_product(temp_root, product_type="video-script")
        existing_id = str(existing["product_id"])
        existing_dir = _product_dir(temp_root, existing_id)
        (existing_dir / SCOPE_LOCK_FILENAME).write_text("pre-existing lock\n", encoding="utf-8")
        try:
            lock_scope(temp_root, existing_id, confirm=True)
            failures.append("FAIL: lock_scope should refuse existing scope_lock.md")
        except FileExistsError:
            print("PASS: lock_scope refuses existing scope_lock.md")

        # 13 writes stay within products/<product_id>.
        files = sorted(
            path.relative_to(temp_root).as_posix()
            for path in temp_root.rglob("*")
            if path.is_file()
        )
        outside_products = [item for item in files if not item.startswith("products/")]
        expect(
            "writes remain under products/<product_id>",
            not outside_products,
            failures,
            detail=f"outside={outside_products}",
        )

        # 16 command helper requires --confirm.
        cli_ready = _complete_scope_ready_product(temp_root, product_type="cover-letter")
        cli_ready_id = str(cli_ready["product_id"])
        no_confirm = _run_lock_script(["--product", cli_ready_id], temp_root)
        expect(
            "ws product-lock-scope requires --confirm",
            no_confirm.returncode != 0 and "--confirm" in (no_confirm.stderr or ""),
            failures,
            detail=f"rc={no_confirm.returncode}, stderr={no_confirm.stderr!r}",
        )

        # 17 no model/provider/agent usage.
        expect(
            "lock result reports no model/provider/agent usage",
            result.get("used_model_provider_agent") is False,
            failures,
        )
        banned_tokens = ("ollama", "gemini", "codex", "requests")
        for script_name in ("product_scope_lock.py", "ws_product_lock_scope.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent tokens",
                not any(token in source for token in banned_tokens),
                failures,
            )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    if failures:
        print("")
        print("Result: FAIL")
        for failure in failures:
            print(failure)
        return 1

    print("")
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
