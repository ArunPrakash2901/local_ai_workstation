#!/usr/bin/env python3
"""No-write tests for Product Lane Phase 1 static intake question helpers."""

from __future__ import annotations

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

from product_intake_questions import (  # noqa: E402
    get_blocking_questions,
    get_optional_questions,
    get_privacy_questions,
    get_question_bank,
    get_required_questions,
    get_supported_product_types,
    render_intake_preview,
    render_questions,
    validate_question_bank,
)


EXPECTED_TYPES = {
    "website",
    "webapp",
    "dashboard",
    "automation",
    "job-pack",
    "cover-letter",
    "interview-prep",
    "video-script",
}

QUESTION_FIELDS = {"id", "prompt", "required", "category", "blocking", "privacy"}


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


def main() -> int:
    print("Product Intake Question Bank Validation")
    print("======================================")
    failures: list[str] = []

    supported = set(get_supported_product_types())
    expect("question bank covers all supported product types", supported == EXPECTED_TYPES, failures)

    bank_errors = validate_question_bank()
    expect("validate_question_bank returns no errors", not bank_errors, failures, "; ".join(bank_errors))

    for product_type in sorted(EXPECTED_TYPES):
        required = get_required_questions(product_type)
        optional = get_optional_questions(product_type)
        blocking = get_blocking_questions(product_type)
        privacy = get_privacy_questions(product_type)
        combined = get_question_bank(product_type)

        expect(f"{product_type}: has required questions", len(required) > 0, failures)

        ids = [item.get("id") for item in combined]
        expect(
            f"{product_type}: question ids are unique",
            len(ids) == len(set(ids)),
            failures,
        )

        for item in combined:
            missing = QUESTION_FIELDS - set(item)
            expect(
                f"{product_type}: question has required fields",
                not missing,
                failures,
                detail=f"missing={sorted(missing)} in {item.get('id')}",
            )
            expect(
                f"{product_type}: required is boolean for {item['id']}",
                isinstance(item.get("required"), bool),
                failures,
            )
            expect(
                f"{product_type}: blocking is boolean for {item['id']}",
                isinstance(item.get("blocking"), bool),
                failures,
            )
            expect(
                f"{product_type}: privacy is boolean for {item['id']}",
                isinstance(item.get("privacy"), bool),
                failures,
            )

        rendered_markdown = render_questions(product_type, format="markdown")
        rendered_text = render_questions(product_type, format="text")
        expect(f"{product_type}: markdown render includes header", product_type in rendered_markdown, failures)
        expect(f"{product_type}: text render includes DRY RUN", "DRY RUN" in rendered_text, failures)

        if product_type in {"job-pack", "cover-letter", "interview-prep"}:
            expect(
                f"{product_type}: includes privacy questions",
                len(privacy) > 0 and any(item.get("privacy") is True for item in privacy),
                failures,
            )
        else:
            expect(f"{product_type}: privacy section exists", len(privacy) > 0, failures)

        expect(
            f"{product_type}: blocking section exists",
            len(blocking) > 0,
            failures,
        )
        expect(
            f"{product_type}: optional section exists",
            len(optional) > 0,
            failures,
        )

    try:
        get_question_bank("not-a-valid-type")
        failures.append("FAIL: unsupported product type should raise ValueError")
    except ValueError:
        print("PASS: unsupported product type rejected")

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_questions_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        before_files = sorted(path.as_posix() for path in temp_root.rglob("*"))
        _ = render_questions("website", format="markdown")
        _ = render_intake_preview("website")
        after_files = sorted(path.as_posix() for path in temp_root.rglob("*"))
        expect(
            "render helpers write no files",
            before_files == after_files,
            failures,
            detail=f"before={before_files}, after={after_files}",
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    preview = render_intake_preview("website")
    expect("intake preview states no files written", "No files written." in preview, failures)
    expect("questions preview states no files written", "No files written." in render_questions("website"), failures)

    banned_tokens = ("ollama", "gemini", "codex", "requests", "subprocess")
    for path in (
        SCRIPTS_DIR / "product_intake_questions.py",
        SCRIPTS_DIR / "ws_product_questions.py",
        SCRIPTS_DIR / "ws_product_intake.py",
    ):
        source = path.read_text(encoding="utf-8").lower()
        expect(
            f"{path.name}: no model/provider/agent tokens",
            not any(token in source for token in banned_tokens),
            failures,
        )
        expect(
            f"{path.name}: no write API tokens",
            "write_text(" not in source and ".mkdir(" not in source,
            failures,
        )

    if failures:
        print("")
        print("Result: FAIL")
        for item in failures:
            print(item)
        return 1

    print("")
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
