#!/usr/bin/env python3
"""Temp-root tests for Product Lane Phase 1 Slice 3 answer import."""

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

from product_answer_import import (  # noqa: E402
    ANSWERS_FILENAME,
    ANSWER_IMPORT_ACTION,
    classify_intake_state,
    import_answers,
    parse_answers_text,
    validate_answers,
)
from product_intake_questions import (  # noqa: E402
    get_blocking_questions,
    get_privacy_questions,
    get_question_bank,
    get_required_questions,
)
from product_intake_artifacts import start_intake  # noqa: E402
from product_registry import (  # noqa: E402
    create_product,
    get_product_status,
    initialize_products_dir,
    save_product,
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


def _make_product(root: Path, *, product_type: str = "website", state: str = "INBOX") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    record["state"] = state
    save_product(record, root, confirm=True, allow_overwrite=False)
    return record


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_answers_text(product_type: str, *, include_privacy: bool, blank_ids: set[str] | None = None) -> str:
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


def _run_import_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_answer_import.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product Answer Import Validation")
    print("================================")
    failures: list[str] = []

    # 1 parse valid
    parsed = parse_answers_text("website.goal: clear goal\nwebsite.audience: clear audience\n")
    expect("parse_answers_text accepts valid lines", parsed == {
        "website.goal": "clear goal",
        "website.audience": "clear audience",
    }, failures)

    # 2 duplicate
    try:
        parse_answers_text("website.goal: one\nwebsite.goal: two\n")
        failures.append("FAIL: parse_answers_text should reject duplicate question ids")
    except ValueError:
        print("PASS: parse_answers_text rejects duplicate question ids")

    # 3 malformed
    try:
        parse_answers_text("website.goal clear goal\n")
        failures.append("FAIL: parse_answers_text should reject malformed lines")
    except ValueError:
        print("PASS: parse_answers_text rejects malformed lines")

    # 4 unknown question ids
    sample_record = {"product_id": "sample-id", "product_type": "website"}
    sample_bank = get_question_bank("website")
    try:
        validate_answers(sample_record, sample_bank, {"unknown.question": "x"})
        failures.append("FAIL: validate_answers should reject unknown question ids")
    except ValueError:
        print("PASS: validate_answers rejects unknown question ids")

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_answer_import_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        # Baseline scope-ready import flow.
        ready_record = _make_product(temp_root, product_type="website", state="INBOX")
        start_intake(ready_record, temp_root, confirm=True)
        ready_persisted = get_product_status(temp_root, str(ready_record["product_id"]))
        ready_text = _render_answers_text("website", include_privacy=True)
        ready_result = import_answers(ready_persisted, temp_root, ready_text, confirm=True)
        ready_dir = temp_root / "products" / str(ready_record["product_id"])
        ready_answers = ready_dir / ANSWERS_FILENAME
        ready_product_file = ready_dir / "product.yaml"

        # 5 write answers.md
        expect("import_answers writes answers.md", ready_answers.is_file(), failures)

        # 6 SCOPE_READY when all required/blocking/privacy answered
        ready_updated = _read_json(ready_product_file)
        expect("state moves to SCOPE_READY", ready_updated.get("state") == "SCOPE_READY", failures)

        # 8 open_questions updated accurately for ready case
        expect("open_questions empty when scope ready", ready_updated.get("open_questions") == [], failures)

        # 9 timestamps set for SCOPE_READY
        expect(
            "intake_completed_at set for SCOPE_READY",
            isinstance(ready_updated.get("intake_completed_at"), str) and bool(ready_updated.get("intake_completed_at")),
            failures,
        )
        expect(
            "scope_ready_at set for SCOPE_READY",
            isinstance(ready_updated.get("scope_ready_at"), str) and bool(ready_updated.get("scope_ready_at")),
            failures,
        )

        # 10 scope_locked_at remains unset
        expect("scope_locked_at remains unset", ready_updated.get("scope_locked_at") in {None, ""}, failures)
        expect(
            "result reports no model/provider/agent usage",
            ready_result.get("used_model_provider_agent") is False,
            failures,
        )

        # 7 CLARIFICATION_NEEDED when required/blocking/privacy unresolved.
        clarify_record = _make_product(temp_root, product_type="website", state="INBOX")
        start_intake(clarify_record, temp_root, confirm=True)
        clarify_persisted = get_product_status(temp_root, str(clarify_record["product_id"]))
        required_ids = [q["id"] for q in get_required_questions("website")]
        blank_required = {str(required_ids[0])} if required_ids else set()
        clarify_text = _render_answers_text("website", include_privacy=False, blank_ids=blank_required)
        clarify_result = import_answers(clarify_persisted, temp_root, clarify_text, confirm=True)
        clarify_updated = _read_json(temp_root / "products" / str(clarify_record["product_id"]) / "product.yaml")
        expect(
            "state moves to CLARIFICATION_NEEDED when unresolved remain",
            clarify_updated.get("state") == "CLARIFICATION_NEEDED",
            failures,
        )
        expect(
            "open_questions includes unresolved ids",
            isinstance(clarify_updated.get("open_questions"), list) and len(clarify_updated.get("open_questions")) > 0,
            failures,
        )
        expect(
            "intake_completed_at unset when clarification needed",
            clarify_updated.get("intake_completed_at") in {None, ""},
            failures,
        )
        expect(
            "scope_ready_at unset when clarification needed",
            clarify_updated.get("scope_ready_at") in {None, ""},
            failures,
        )
        expect(
            "clarification result includes unresolved privacy ids",
            len(clarify_result["unresolved_privacy"]) > 0,
            failures,
        )

        # 11 missing product
        missing = create_product(title="missing", product_type="website")
        try:
            import_answers(missing, temp_root, ready_text, confirm=True)
            failures.append("FAIL: import_answers should refuse missing product")
        except FileNotFoundError:
            print("PASS: import_answers refuses missing product")

        # 12 wrong product state
        inbox_record = _make_product(temp_root, product_type="website", state="INBOX")
        try:
            import_answers(inbox_record, temp_root, ready_text, confirm=True)
            failures.append("FAIL: import_answers should refuse non-intake state")
        except ValueError:
            print("PASS: import_answers refuses non-intake state")

        # 7b unsupported product type in caller payload
        unsupported_payload = {
            "product_id": str(ready_record["product_id"]),
            "product_type": "unsupported-type",
        }
        try:
            import_answers(unsupported_payload, temp_root, ready_text, confirm=True)
            failures.append("FAIL: import_answers should reject unsupported product type payload")
        except ValueError:
            print("PASS: import_answers rejects unsupported product type payload")

        # 13 overwrite refusal
        try:
            import_answers(clarify_persisted, temp_root, clarify_text, confirm=True)
            failures.append("FAIL: import_answers should refuse overwrite of existing answers.md")
        except FileExistsError:
            print("PASS: import_answers refuses overwrite of answers.md")

        # 14 no writes outside products/<product_id>
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

        # 15 content-private privacy questions are required/visible.
        content_record = _make_product(temp_root, product_type="job-pack", state="INBOX")
        start_intake(content_record, temp_root, confirm=True)
        content_persisted = get_product_status(temp_root, str(content_record["product_id"]))
        content_answers = _render_answers_text("job-pack", include_privacy=False)
        content_result = import_answers(content_persisted, temp_root, content_answers, confirm=True)
        content_privacy_ids = {q["id"] for q in get_privacy_questions("job-pack")}
        expect(
            "job-pack import reports unresolved privacy questions when omitted",
            bool(content_result["unresolved_privacy"])
            and set(content_result["unresolved_privacy"]).issubset(content_privacy_ids),
            failures,
        )

        # 16 no model/provider/agent usage tokens in source.
        banned_tokens = ("ollama", "gemini", "codex", "requests")
        for script_name in ("product_answer_import.py", "ws_product_answer_import.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent tokens",
                not any(token in source for token in banned_tokens),
                failures,
            )

        # 17 command helper requires --confirm.
        cli_record = _make_product(temp_root, product_type="dashboard", state="INBOX")
        start_intake(cli_record, temp_root, confirm=True)
        answers_file = temp_root / "products" / str(cli_record["product_id"]) / "answers_input.txt"
        answers_file.write_text(_render_answers_text("dashboard", include_privacy=True), encoding="utf-8")
        no_confirm = _run_import_script(
            ["--product", str(cli_record["product_id"]), "--file", str(answers_file)],
            temp_root,
        )
        expect(
            "ws product-answer-import requires --confirm",
            no_confirm.returncode != 0 and "--confirm" in (no_confirm.stderr or ""),
            failures,
            detail=f"rc={no_confirm.returncode}, stderr={no_confirm.stderr!r}",
        )

        # classification helper smoke check for deterministic output.
        classification = classify_intake_state(
            ready_persisted,
            get_question_bank("website"),
            validate_answers(ready_persisted, get_question_bank("website"), parse_answers_text(ready_text)),
        )
        expect(
            "classification sets SCOPE_READY when no unresolved questions remain",
            classification["state_after"] == "SCOPE_READY",
            failures,
        )
        expect(
            "last action constant is deterministic",
            ANSWER_IMPORT_ACTION == "ws product-answer-import --confirm",
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
