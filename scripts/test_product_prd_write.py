#!/usr/bin/env python3
"""Temp-root tests for Product Lane Phase 2 Slice 2 PRD write path."""

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
from product_prd import PRD_WRITE_ACTION, render_prd_document, write_prd  # noqa: E402
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
    for question in get_required_questions(product_type) + get_blocking_questions(product_type) + get_privacy_questions(product_type):
        question_id = str(question["id"])
        lines.append(f"{question_id}: answer for {question_id}")
    return "\n".join(lines) + "\n"


def _make_locked_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} prd write sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    record["state"] = "INBOX"
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
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
    print("Product PRD Write Validation")
    print("=============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_prd_write_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        ready = _make_locked_product(temp_root, product_type="website")
        product_id = str(ready["product_id"])
        pdir = temp_root / "products" / product_id
        product_file = pdir / "product.yaml"
        prd_file = pdir / "prd.md"
        scope_lock_text = (pdir / "scope_lock.md").read_text(encoding="utf-8")

        # 1/2 deterministic write content.
        expected_write = render_prd_document(ready, scope_lock_text, dry_run=False)
        result = write_prd(temp_root, product_id, confirm=True)
        expect("write_prd writes prd.md", prd_file.is_file(), failures)
        expect(
            "prd.md content is deterministic",
            prd_file.read_text(encoding="utf-8") == expected_write.rstrip() + "\n",
            failures,
        )

        # 4/7 product.yaml updates.
        updated = json.loads(product_file.read_text(encoding="utf-8"))
        expect(
            "product.yaml last_action updated",
            updated.get("last_action") == PRD_WRITE_ACTION,
            failures,
        )
        expect(
            "product.yaml updated_at refreshed",
            isinstance(updated.get("updated_at"), str) and bool(updated.get("updated_at")),
            failures,
        )
        expect(
            "product.yaml prd_created_at recorded",
            isinstance(updated.get("prd_created_at"), str) and bool(updated.get("prd_created_at")),
            failures,
        )
        expect(
            "state remains SCOPE_LOCKED",
            updated.get("state") == "SCOPE_LOCKED",
            failures,
        )
        expect(
            "helper result state remains SCOPE_LOCKED",
            result.get("state_before") == "SCOPE_LOCKED" and result.get("state_after") == "SCOPE_LOCKED",
            failures,
        )
        expect(
            "helper reports no model/provider/agent usage",
            result.get("used_model_provider_agent") is False,
            failures,
        )
        expect(
            "helper returns files written",
            str(prd_file) in result.get("files_written", []) and str(product_file) in result.get("files_written", []),
            failures,
        )

        # 3/6 overwrite and preconditions.
        try:
            write_prd(temp_root, product_id, confirm=True)
            failures.append("FAIL: write_prd should refuse existing prd.md")
        except FileExistsError:
            print("PASS: write_prd refuses existing prd.md")

        # 5 missing scope_lock.md rejected.
        missing_lock = _make_locked_product(temp_root, product_type="webapp")
        missing_lock_id = str(missing_lock["product_id"])
        (temp_root / "products" / missing_lock_id / "scope_lock.md").unlink()
        try:
            write_prd(temp_root, missing_lock_id, confirm=True)
            failures.append("FAIL: write_prd should refuse missing scope_lock.md")
        except FileNotFoundError:
            print("PASS: write_prd refuses missing scope_lock.md")

        # 6 missing scope_lock_hash rejected.
        missing_hash = _make_locked_product(temp_root, product_type="dashboard")
        missing_hash_id = str(missing_hash["product_id"])
        missing_hash_file = temp_root / "products" / missing_hash_id / "product.yaml"
        payload = json.loads(missing_hash_file.read_text(encoding="utf-8"))
        payload["scope_lock_hash"] = None
        missing_hash_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        try:
            write_prd(temp_root, missing_hash_id, confirm=True)
            failures.append("FAIL: write_prd should refuse missing scope_lock_hash")
        except ValueError:
            print("PASS: write_prd refuses missing scope_lock_hash")

        # 8 no downstream artifacts created.
        for forbidden in ("wireframes.md", "ux_spec.md", "technical_plan.md", "build_plan.md"):
            expect(f"{forbidden} is not created", not (pdir / forbidden).exists(), failures)

        # 9 writes stay under products/<product_id>/.
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

        # 10 unsupported product type rejected.
        unsupported = _make_locked_product(temp_root, product_type="automation")
        unsupported_id = str(unsupported["product_id"])
        unsupported_file = temp_root / "products" / unsupported_id / "product.yaml"
        unsupported_payload = json.loads(unsupported_file.read_text(encoding="utf-8"))
        unsupported_payload["product_type"] = "unsupported-type"
        unsupported_payload["type"] = "unsupported-type"
        unsupported_file.write_text(json.dumps(unsupported_payload, indent=2) + "\n", encoding="utf-8")
        try:
            write_prd(temp_root, unsupported_id, confirm=True)
            failures.append("FAIL: write_prd should refuse unsupported product type")
        except ValueError:
            print("PASS: write_prd refuses unsupported product type")

        # 11 command helper requires --confirm for write.
        cli_ready = _make_locked_product(temp_root, product_type="video-script")
        cli_ready_id = str(cli_ready["product_id"])
        no_mode = _run_prd_script(["--product", cli_ready_id], temp_root)
        expect(
            "ws product-prd requires a mode flag",
            no_mode.returncode != 0,
            failures,
            detail=f"rc={no_mode.returncode}, stderr={no_mode.stderr!r}",
        )
        dry_run = _run_prd_script(["--product", cli_ready_id, "--dry-run"], temp_root)
        expect(
            "ws product-prd --dry-run remains no-write",
            dry_run.returncode == 0 and "DRY RUN - no files written." in (dry_run.stdout or ""),
            failures,
            detail=f"rc={dry_run.returncode}, stderr={dry_run.stderr!r}",
        )
        confirm = _run_prd_script(["--product", cli_ready_id, "--confirm"], temp_root)
        expect(
            "ws product-prd --confirm succeeds",
            confirm.returncode == 0
            and "Product PRD draft written." in (confirm.stdout or "")
            and "files_written:" in (confirm.stdout or ""),
            failures,
            detail=f"rc={confirm.returncode}, stderr={confirm.stderr!r}",
        )

        # 12 dry-run helper still does not write.
        before = sorted(
            path.relative_to(temp_root).as_posix()
            for path in temp_root.rglob("*")
            if path.is_file()
        )
        _ = _run_prd_script(["--product", cli_ready_id, "--dry-run"], temp_root)
        after = sorted(
            path.relative_to(temp_root).as_posix()
            for path in temp_root.rglob("*")
            if path.is_file()
        )
        expect("dry-run remains no-write", before == after, failures)
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
