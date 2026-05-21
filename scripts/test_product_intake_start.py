#!/usr/bin/env python3
"""Temp-root tests for Product Lane Phase 1 Slice 2 intake start."""

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

from product_intake_artifacts import (  # noqa: E402
    intake_paths,
    start_intake,
)
from product_intake_questions import get_privacy_questions, render_intake_preview  # noqa: E402
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
        msg = f"FAIL: {name}"
        if detail:
            msg = f"{msg} - {detail}"
        failures.append(msg)


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
    record = create_product(title=f"{product_type} sample", product_type=product_type)
    record["state"] = state
    save_product(record, root, confirm=True, allow_overwrite=False)
    return record


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_intake.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product Intake Start Validation")
    print("===============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_intake_start_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        # 1-5 baseline start flow
        record = _make_product(temp_root, product_type="website", state="INBOX")
        result = start_intake(record, temp_root, confirm=True)
        paths = intake_paths(temp_root, str(record["product_id"]))
        expect("start_intake writes intake.md", paths["intake_md"].is_file(), failures)
        expect("start_intake writes questions.md", paths["questions_md"].is_file(), failures)

        updated = _read_json(paths["product_file"])
        expect(
            "product state updated to INTAKE_STARTED",
            updated.get("state") == "INTAKE_STARTED",
            failures,
        )
        expect(
            "intake_started_at is set",
            isinstance(updated.get("intake_started_at"), str) and bool(updated.get("intake_started_at")),
            failures,
        )
        expect(
            "updated_at is set",
            isinstance(updated.get("updated_at"), str) and bool(updated.get("updated_at")),
            failures,
        )
        expect("intake_completed_at is not set", "intake_completed_at" not in updated or updated.get("intake_completed_at") in {None, ""}, failures)
        expect("scope_ready_at is not set", "scope_ready_at" not in updated or updated.get("scope_ready_at") in {None, ""}, failures)
        expect(
            "scope_locked_at remains unset",
            updated.get("scope_locked_at") in {None, ""},
            failures,
        )

        expect(
            "result includes no model/provider/agent usage",
            result.get("used_model_provider_agent") is False,
            failures,
        )

        # 6 missing product
        missing = create_product(title="missing product", product_type="website")
        try:
            start_intake(missing, temp_root, confirm=True)
            failures.append("FAIL: start_intake should refuse missing product")
        except FileNotFoundError:
            print("PASS: start_intake refuses missing product")

        # 7 unsupported type
        bad = _make_product(temp_root, product_type="dashboard", state="INBOX")
        bad["product_type"] = "unsupported-type"
        try:
            start_intake(bad, temp_root, confirm=True)
            failures.append("FAIL: start_intake should refuse unsupported product type")
        except ValueError:
            print("PASS: start_intake refuses unsupported product type")

        # 8 non-INBOX state
        started = _make_product(temp_root, product_type="webapp", state="INTAKE_STARTED")
        try:
            start_intake(started, temp_root, confirm=True)
            failures.append("FAIL: start_intake should refuse non-INBOX products")
        except ValueError:
            print("PASS: start_intake refuses non-INBOX products")

        # 9/10 no overwrite
        duplicate = _make_product(temp_root, product_type="automation", state="INBOX")
        first_result = start_intake(duplicate, temp_root, confirm=True)
        expect("first intake start succeeds", bool(first_result.get("files_written")), failures)
        try:
            start_intake(duplicate, temp_root, confirm=True)
            failures.append("FAIL: start_intake should refuse overwriting intake artifacts")
        except ValueError:
            print("PASS: start_intake refuses overwrite when templates already exist")

        # 11 no writes outside products/<product_id> and 12 privacy inclusion checks
        content_product = _make_product(temp_root, product_type="job-pack", state="INBOX")
        start_intake(content_product, temp_root, confirm=True)
        content_paths = intake_paths(temp_root, str(content_product["product_id"]))
        intake_text = content_paths["intake_md"].read_text(encoding="utf-8")
        questions_text = content_paths["questions_md"].read_text(encoding="utf-8")
        privacy_questions = get_privacy_questions("job-pack")
        expect("job-pack has privacy questions in bank", len(privacy_questions) > 0, failures)
        expect("job-pack intake includes privacy section", "## Privacy Questions" in intake_text, failures)
        expect("job-pack questions include privacy section", "## Privacy Questions" in questions_text, failures)

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

        # 13 confirm requires --product when using command interface
        only_type_confirm = _run_script(["--type", "website", "--confirm"], temp_root)
        expect(
            "--confirm requires --product in command interface",
            only_type_confirm.returncode != 0 and "--confirm requires --product" in (only_type_confirm.stderr or ""),
            failures,
            detail=f"rc={only_type_confirm.returncode}, stderr={only_type_confirm.stderr!r}",
        )

        # 14 dry-run remains no-write
        dry_root = (temp_root / "dry-run-only").resolve()
        dry_root.mkdir(parents=True, exist_ok=True)
        initialize_products_dir(dry_root)
        dry_record = _make_product(dry_root, product_type="website", state="INBOX")
        before = sorted(
            path.relative_to(dry_root).as_posix()
            for path in dry_root.rglob("*")
            if path.is_file()
        )
        dry = _run_script(["--product", str(dry_record["product_id"]), "--dry-run"], dry_root)
        after = sorted(
            path.relative_to(dry_root).as_posix()
            for path in dry_root.rglob("*")
            if path.is_file()
        )
        expect("dry-run command exits 0", dry.returncode == 0, failures, detail=f"stderr={dry.stderr!r}")
        expect("dry-run writes no additional files", before == after, failures)
        expect("dry-run output says no files written", "No files written." in (dry.stdout or ""), failures)

        # 15 no model/provider/agent usage (source-level token check)
        banned_tokens = ("ollama", "gemini", "codex", "requests", "subprocess")
        for script_name in ("product_intake_artifacts.py", "ws_product_intake.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent tokens",
                not any(token in source for token in banned_tokens),
                failures,
            )

        preview = render_intake_preview("website")
        expect("intake preview still indicates preview-only", "Phase 1 Slice 1 preview only." in preview, failures)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

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
