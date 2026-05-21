#!/usr/bin/env python3
"""No-write tests for Product Lane Phase 1 Slice 4 scope preview."""

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
from product_intake_artifacts import start_intake  # noqa: E402
from product_intake_questions import (  # noqa: E402
    get_blocking_questions,
    get_privacy_questions,
    get_required_questions,
)
from product_registry import (  # noqa: E402
    create_product,
    get_product_status,
    initialize_products_dir,
    save_product,
)
from product_scope import load_product_scope_inputs, parse_answers_md, render_scope_draft  # noqa: E402


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


def _render_answers_text(
    product_type: str,
    *,
    include_privacy: bool = True,
    blank_ids: set[str] | None = None,
) -> str:
    blank_ids = blank_ids or set()
    required = get_required_questions(product_type)
    blocking = get_blocking_questions(product_type)
    privacy = get_privacy_questions(product_type) if include_privacy else []
    lines: list[str] = []
    for question in required + blocking + privacy:
        question_id = str(question["id"])
        answer = "" if question_id in blank_ids else f"answer for {question_id}"
        lines.append(f"{question_id}: {answer}")
    return "\n".join(lines) + "\n"


def _make_product(root: Path, *, product_type: str = "website", state: str = "INBOX") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} scope sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    record["state"] = state
    save_product(record, root, confirm=True, allow_overwrite=False)
    return record


def _product_file(root: Path, product_id: str) -> Path:
    return root / "products" / product_id / "product.yaml"


def _answers_file(root: Path, product_id: str) -> Path:
    return root / "products" / product_id / ANSWERS_FILENAME


def _complete_scope_ready_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = _make_product(root, product_type=product_type, state="INBOX")
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    answers_text = _render_answers_text(product_type, include_privacy=True)
    import_answers(persisted, root, answers_text, confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _run_scope_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_scope.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product Scope Dry-Run Validation")
    print("================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_scope_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        # 4 baseline scope preview for SCOPE_READY product.
        ready = _complete_scope_ready_product(temp_root, product_type="website")
        ready_id = str(ready["product_id"])
        payload = load_product_scope_inputs(temp_root, ready_id)
        preview = render_scope_draft(
            payload["product_record"],
            payload["question_bank"],
            payload["answers"],
            source_status=payload["source_status"],
        )

        # 1 DRY RUN / no-write notice.
        expect(
            "render_scope_draft includes DRY RUN/no files notice",
            "DRY RUN - no files written." in preview,
            failures,
        )

        # 2 metadata presence.
        expect(
            "render_scope_draft includes product metadata",
            (
                f"product_id: `{ready_id}`" in preview
                and f"product_type: `{ready['product_type']}`" in preview
                and f"label: {ready['label']}" in preview
                and f"current_state: `{ready['state']}`" in preview
            ),
            failures,
        )

        # 3 generated_from section.
        expect("render_scope_draft includes generated_from", "## Generated From" in preview, failures)
        expect(
            "render_scope_draft includes source files",
            all(name in preview for name in ("product.yaml", "intake.md", "questions.md", "answers.md")),
            failures,
        )

        # 8 unknown sections are explicit TODO/UNKNOWN.
        expect("unknown scope fields render TODO/UNKNOWN", "TODO/UNKNOWN" in preview, failures)

        # parse_answers_md smoke (deterministic format support).
        parsed = parse_answers_md(payload["paths"]["answers_md"].read_text(encoding="utf-8"))
        expect("parse_answers_md parsed known question answers", len(parsed) > 0, failures)

        # 9 scope dry-run writes no files.
        before = sorted(
            p.relative_to(temp_root).as_posix()
            for p in temp_root.rglob("*")
            if p.is_file()
        )
        _ = render_scope_draft(
            payload["product_record"],
            payload["question_bank"],
            payload["answers"],
            source_status=payload["source_status"],
        )
        after = sorted(
            p.relative_to(temp_root).as_posix()
            for p in temp_root.rglob("*")
            if p.is_file()
        )
        expect("scope dry-run writes no files", before == after, failures)

        # 11 no product.yaml update occurs.
        product_file = _product_file(temp_root, ready_id)
        product_before = product_file.read_text(encoding="utf-8")
        _ = load_product_scope_inputs(temp_root, ready_id)
        product_after = product_file.read_text(encoding="utf-8")
        expect("scope helpers do not update product.yaml", product_before == product_after, failures)

        # 12 no scope artifacts are created.
        ready_dir = temp_root / "products" / ready_id
        expect("scope_draft.md is not created", not (ready_dir / "scope_draft.md").exists(), failures)
        expect("scope_lock.md is not created", not (ready_dir / "scope_lock.md").exists(), failures)

        # 5 non-SCOPE_READY products are rejected.
        not_ready = _make_product(temp_root, product_type="website", state="INBOX")
        start_intake(not_ready, temp_root, confirm=True)
        # Create answers.md so state check is the blocker.
        not_ready_answers = _answers_file(temp_root, str(not_ready["product_id"]))
        not_ready_answers.write_text(_render_answers_text("website"), encoding="utf-8")
        try:
            load_product_scope_inputs(temp_root, str(not_ready["product_id"]))
            failures.append("FAIL: non-SCOPE_READY product should be rejected")
        except ValueError:
            print("PASS: non-SCOPE_READY product rejected")

        # 6 missing answers.md is rejected.
        missing_answers = _complete_scope_ready_product(temp_root, product_type="dashboard")
        missing_answers_id = str(missing_answers["product_id"])
        _answers_file(temp_root, missing_answers_id).unlink()
        try:
            load_product_scope_inputs(temp_root, missing_answers_id)
            failures.append("FAIL: missing answers.md should be rejected")
        except FileNotFoundError:
            print("PASS: missing answers.md rejected")

        # 7 unresolved required/blocking/privacy answers are rejected.
        unresolved = _complete_scope_ready_product(temp_root, product_type="website")
        unresolved_id = str(unresolved["product_id"])
        answers_path = _answers_file(temp_root, unresolved_id)
        answer_text = answers_path.read_text(encoding="utf-8")
        required_first = get_required_questions("website")[0]["id"]
        answer_text = answer_text.replace(
            f"Answer: answer for {required_first}",
            "Answer: (unanswered)",
            1,
        )
        answers_path.write_text(answer_text, encoding="utf-8")
        try:
            load_product_scope_inputs(temp_root, unresolved_id)
            failures.append("FAIL: unresolved required questions should be rejected")
        except ValueError:
            print("PASS: unresolved required questions rejected")

        # 10 helper writes nothing outside product directory during scope rendering.
        files = sorted(
            p.relative_to(temp_root).as_posix()
            for p in temp_root.rglob("*")
            if p.is_file()
        )
        outside_products = [item for item in files if not item.startswith("products/")]
        expect(
            "scope helpers write nothing outside products/<product_id>",
            not outside_products,
            failures,
            detail=f"outside={outside_products}",
        )

        # 14 command helper requires --dry-run.
        cli_ready = _complete_scope_ready_product(temp_root, product_type="video-script")
        cli_ready_id = str(cli_ready["product_id"])
        no_dry_run = _run_scope_script(["--product", cli_ready_id], temp_root)
        expect(
            "ws product-scope requires --dry-run",
            no_dry_run.returncode != 0 and "Use --dry-run" in (no_dry_run.stderr or ""),
            failures,
            detail=f"rc={no_dry_run.returncode}, stderr={no_dry_run.stderr!r}",
        )
        with_dry_run = _run_scope_script(["--product", cli_ready_id, "--dry-run"], temp_root)
        expect(
            "ws product-scope --dry-run succeeds",
            with_dry_run.returncode == 0 and "DRY RUN - no files written." in (with_dry_run.stdout or ""),
            failures,
            detail=f"rc={with_dry_run.returncode}, stderr={with_dry_run.stderr!r}",
        )

        # 15 unsupported product type is rejected.
        unsupported = _complete_scope_ready_product(temp_root, product_type="automation")
        unsupported_id = str(unsupported["product_id"])
        unsupported_file = _product_file(temp_root, unsupported_id)
        unsupported_payload = json.loads(unsupported_file.read_text(encoding="utf-8"))
        unsupported_payload["product_type"] = "unsupported-type"
        unsupported_payload["type"] = "unsupported-type"
        unsupported_file.write_text(json.dumps(unsupported_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_product_scope_inputs(temp_root, unsupported_id)
            failures.append("FAIL: unsupported product type should be rejected")
        except ValueError:
            print("PASS: unsupported product type rejected")

        # 13 no model/provider/agent usage.
        banned_tokens = ("ollama", "gemini", "codex", "requests")
        for script_name in ("product_scope.py", "ws_product_scope.py"):
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
