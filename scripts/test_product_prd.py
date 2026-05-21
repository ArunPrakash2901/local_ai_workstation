#!/usr/bin/env python3
"""Temp-root tests for Product Lane Phase 2 Slice 1 PRD preview."""

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
from product_intake_questions import get_blocking_questions, get_privacy_questions, get_required_questions  # noqa: E402
from product_prd import load_prd_inputs, render_prd_preview  # noqa: E402
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


def _make_product(root: Path, *, product_type: str = "website", state: str = "INBOX") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} prd sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    record["state"] = state
    save_product(record, root, confirm=True, allow_overwrite=False)
    return record


def _render_answers_text(product_type: str, *, include_privacy: bool = True) -> str:
    required = get_required_questions(product_type)
    blocking = get_blocking_questions(product_type)
    privacy = get_privacy_questions(product_type) if include_privacy else []
    lines: list[str] = []
    for question in required + blocking + privacy:
        question_id = str(question["id"])
        lines.append(f"{question_id}: answer for {question_id}")
    return "\n".join(lines) + "\n"


def _complete_locked_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = _make_product(root, product_type=product_type, state="INBOX")
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    answers_text = _render_answers_text(product_type, include_privacy=True)
    import_answers(persisted, root, answers_text, confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _run_prd_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_prd.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product PRD Preview Validation")
    print("==============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_prd_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        ready = _complete_locked_product(temp_root, product_type="website")
        product_id = str(ready["product_id"])
        pdir = temp_root / "products" / product_id
        product_file = pdir / "product.yaml"
        scope_lock_path = pdir / "scope_lock.md"
        scope_lock_text = scope_lock_path.read_text(encoding="utf-8")

        # 1 dry-run / no-write notice.
        preview = render_prd_preview(ready, scope_lock_text)
        expect("render_prd_preview includes DRY RUN/no files notice", "DRY RUN - no files written." in preview, failures)

        # 2 metadata presence.
        expect(
            "render_prd_preview includes product metadata",
            (
                f"product_id: `{product_id}`" in preview
                and f"product_type: `{ready['product_type']}`" in preview
                and f"label: {ready['label']}" in preview
                and f"current_state: `{ready['state']}`" in preview
            ),
            failures,
        )

        # 3 scope_lock_hash presence.
        expect(
            "render_prd_preview includes scope_lock_hash",
            f"scope_lock_hash: `{ready['scope_lock_hash']}`" in preview,
            failures,
        )

        # 4 generated_from section.
        expect("render_prd_preview includes generated_from", "## Generated From" in preview, failures)
        expect(
            "render_prd_preview lists source files",
            "product.yaml" in preview and "scope_lock.md" in preview,
            failures,
        )

        # 5 locked product renders PRD preview.
        expect("locked product renders preview", "## Executive Summary" in preview and "## Acceptance Criteria" in preview, failures)

        # 9 unknown/missing fields render TODO/UNKNOWN.
        truncated_lock = "\n".join(
            line for line in scope_lock_text.splitlines() if "## Constraints" not in line and "## Dependencies" not in line
        )
        truncated_preview = render_prd_preview(ready, truncated_lock)
        expect(
            "missing scope fields render TODO/UNKNOWN",
            "TODO/UNKNOWN" in truncated_preview,
            failures,
        )

        # 10/11/12 no writes.
        before = sorted(
            p.relative_to(temp_root).as_posix()
            for p in temp_root.rglob("*")
            if p.is_file()
        )
        product_before = product_file.read_text(encoding="utf-8")
        _ = render_prd_preview(ready, scope_lock_text)
        after = sorted(
            p.relative_to(temp_root).as_posix()
            for p in temp_root.rglob("*")
            if p.is_file()
        )
        expect("product-prd dry-run writes no files", before == after, failures)
        expect(
            "product.yaml update does not occur",
            product_before == product_file.read_text(encoding="utf-8"),
            failures,
        )
        expect("prd.md is not created", not (pdir / "prd.md").exists(), failures)
        for forbidden in ("wireframes.md", "technical_plan.md", "build_plan.md"):
            expect(f"{forbidden} is not created", not (pdir / forbidden).exists(), failures)

        # 6 non-SCOPE_LOCKED rejected.
        not_locked = _make_product(temp_root, product_type="webapp", state="INBOX")
        start_intake(not_locked, temp_root, confirm=True)
        try:
            load_prd_inputs(temp_root, str(not_locked["product_id"]))
            failures.append("FAIL: non-SCOPE_LOCKED product should be rejected")
        except ValueError:
            print("PASS: non-SCOPE_LOCKED product rejected")

        # 7 missing scope_lock.md rejected.
        missing_lock = _complete_locked_product(temp_root, product_type="dashboard")
        missing_lock_id = str(missing_lock["product_id"])
        (temp_root / "products" / missing_lock_id / "scope_lock.md").unlink()
        try:
            load_prd_inputs(temp_root, missing_lock_id)
            failures.append("FAIL: missing scope_lock.md should be rejected")
        except FileNotFoundError:
            print("PASS: missing scope_lock.md rejected")

        # 8 missing scope_lock_hash rejected.
        missing_hash = _complete_locked_product(temp_root, product_type="automation")
        missing_hash_id = str(missing_hash["product_id"])
        missing_hash_file = temp_root / "products" / missing_hash_id / "product.yaml"
        product_data = json.loads(missing_hash_file.read_text(encoding="utf-8"))
        product_data["scope_lock_hash"] = None
        missing_hash_file.write_text(json.dumps(product_data, indent=2) + "\n", encoding="utf-8")
        try:
            load_prd_inputs(temp_root, missing_hash_id)
            failures.append("FAIL: missing scope_lock_hash should be rejected")
        except ValueError:
            print("PASS: missing scope_lock_hash rejected")

        # 13/14 no model/provider/agent usage.
        banned_tokens = ("ollama", "gemini", "codex", "requests")
        for script_name in ("product_prd.py", "ws_product_prd.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent tokens",
                not any(token in source for token in banned_tokens),
                failures,
            )

        # 15 command helper requires --dry-run.
        cli_ready = _complete_locked_product(temp_root, product_type="video-script")
        cli_ready_id = str(cli_ready["product_id"])
        no_dry_run = _run_prd_script(["--product", cli_ready_id], temp_root)
        expect(
            "ws product-prd requires --dry-run",
            no_dry_run.returncode != 0
            and "--dry-run --confirm" in (no_dry_run.stderr or "")
            and "required" in (no_dry_run.stderr or ""),
            failures,
            detail=f"rc={no_dry_run.returncode}, stderr={no_dry_run.stderr!r}",
        )
        with_dry_run = _run_prd_script(["--product", cli_ready_id, "--dry-run"], temp_root)
        expect(
            "ws product-prd --dry-run succeeds",
            with_dry_run.returncode == 0 and "DRY RUN - no files written." in (with_dry_run.stdout or ""),
            failures,
            detail=f"rc={with_dry_run.returncode}, stderr={with_dry_run.stderr!r}",
        )

        # 16 unsupported product type rejected.
        unsupported = _complete_locked_product(temp_root, product_type="cover-letter")
        unsupported_id = str(unsupported["product_id"])
        unsupported_file = temp_root / "products" / unsupported_id / "product.yaml"
        unsupported_payload = json.loads(unsupported_file.read_text(encoding="utf-8"))
        unsupported_payload["product_type"] = "unsupported-type"
        unsupported_payload["type"] = "unsupported-type"
        unsupported_file.write_text(json.dumps(unsupported_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_prd_inputs(temp_root, unsupported_id)
            failures.append("FAIL: unsupported product type should be rejected")
        except ValueError:
            print("PASS: unsupported product type rejected")
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
