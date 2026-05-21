#!/usr/bin/env python3
"""Temp-root tests for Product Lane scope change confirm flow."""

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
from product_registry import create_product, get_product_status, initialize_products_dir, save_product  # noqa: E402
from product_scope_change import confirm_scope_change  # noqa: E402
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
        qid = str(question["id"])
        lines.append(f"{qid}: answer for {qid}")
    return "\n".join(lines) + "\n"


def _make_scope_locked_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} scope change confirm sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _make_scope_locked_with_prd(root: Path, *, approved: bool = False) -> dict[str, object]:
    record = _make_scope_locked_product(root, product_type="website")
    product_id = str(record["product_id"])
    write_prd(root, product_id, confirm=True)
    product_file = root / "products" / product_id / "product.yaml"
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    if approved:
        payload["prd_status"] = "APPROVED"
        payload["prd_reviewed_at"] = "2026-01-01T00:00:00Z"
        payload["prd_approved_at"] = "2026-01-01T00:00:00Z"
        payload["prd_review_notes"] = "approved for test"
        approval_dir = root / "products" / product_id / "decisions"
        approval_dir.mkdir(parents=True, exist_ok=True)
        (approval_dir / "prd_approval.md").write_text("# approval\n", encoding="utf-8")
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return get_product_status(root, product_id)


def _write_change_file(root: Path, content: str) -> Path:
    change_file = root / f"tmp_scope_change_confirm_{uuid4().hex}.md"
    change_file.write_text(content, encoding="utf-8")
    return change_file


def _run_scope_change_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_scope_change.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product Scope Change Confirm Validation")
    print("=======================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_scope_change_confirm_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)
        change_text = (
            "change_id: add-out-of-scope-for-portfolio-website\n"
            "reason: PRD review found Out of Scope TODO/UNKNOWN.\n"
            "field: out_of_scope\n"
            "proposed_value: >\n"
            "  Backend services, authentication, CMS/blog engine, payment features,\n"
            "  complex animations, and unrelated project source-code rewrites are out of scope.\n"
            "operator_note: This change fills a missing source answer discovered during PRD review.\n"
        )

        # 1/2/3/4/5/6/7/8/9 confirm write/update invariants.
        product = _make_scope_locked_with_prd(temp_root, approved=True)
        product_id = str(product["product_id"])
        product_dir = temp_root / "products" / product_id
        change_file = _write_change_file(temp_root, change_text)

        before_scope = (product_dir / "scope_lock.md").read_text(encoding="utf-8")
        before_prd = (product_dir / "prd.md").read_text(encoding="utf-8")
        answers_path = product_dir / "answers.md"
        before_answers = answers_path.read_text(encoding="utf-8")
        before_state = json.loads((product_dir / "product.yaml").read_text(encoding="utf-8"))["state"]

        result = confirm_scope_change(temp_root, product_id, change_file, confirm=True)
        decision_path = Path(result["decision_path"])
        updated_payload = json.loads((product_dir / "product.yaml").read_text(encoding="utf-8"))

        expect("confirm writes decisions/scope_change_*.md under temp product directory", decision_path.is_file(), failures)
        expect("confirm creates decisions/ if needed", decision_path.parent.is_dir(), failures)
        expect("confirm updates product.yaml scope_change_pending", updated_payload.get("scope_change_pending") is True, failures)
        expect(
            "confirm updates stale_artifacts when prd.md exists",
            "prd.md" in list(updated_payload.get("stale_artifacts", [])),
            failures,
            detail=str(updated_payload.get("stale_artifacts")),
        )
        expect(
            "confirm sets prd_status to NEEDS_REVISION or STALE when prd.md exists",
            updated_payload.get("prd_status") in {"NEEDS_REVISION", "STALE"},
            failures,
            detail=str(updated_payload.get("prd_status")),
        )
        expect("confirm leaves main product state unchanged", updated_payload.get("state") == before_state, failures)
        expect(
            "confirm does not modify scope_lock.md",
            (product_dir / "scope_lock.md").read_text(encoding="utf-8") == before_scope,
            failures,
        )
        expect(
            "confirm does not modify prd.md",
            (product_dir / "prd.md").read_text(encoding="utf-8") == before_prd,
            failures,
        )
        expect(
            "confirm does not modify answers.md",
            answers_path.read_text(encoding="utf-8") == before_answers,
            failures,
        )

        # 10 duplicate change_id refusal.
        try:
            confirm_scope_change(temp_root, product_id, change_file, confirm=True)
            failures.append("FAIL: confirm should refuse duplicate change_id")
        except FileExistsError:
            print("PASS: confirm refuses duplicate change_id")

        # 11 malformed change file refusal.
        bad_change_file = _write_change_file(temp_root, "change_id this is bad\n")
        try:
            confirm_scope_change(temp_root, product_id, bad_change_file, confirm=True)
            failures.append("FAIL: malformed change file should be rejected")
        except ValueError:
            print("PASS: malformed change file rejected")

        # 12 unsupported field refusal.
        unsupported_change_file = _write_change_file(
            temp_root,
            "change_id: unsupported\nreason: x\nfield: launch_plan\nproposed_value: y\n",
        )
        try:
            confirm_scope_change(temp_root, product_id, unsupported_change_file, confirm=True)
            failures.append("FAIL: unsupported field should be rejected")
        except ValueError:
            print("PASS: unsupported field rejected")

        # 13 writes nothing outside products/<product_id>/.
        outside_files = [
            path for path in temp_root.rglob("*")
            if path.is_file()
            and product_dir not in path.resolve().parents
            and path.resolve() != product_dir.resolve()
            and path.name.startswith("scope_change_")
        ]
        expect("confirm writes nothing outside products/<product_id>/", not outside_files, failures, detail=str(outside_files))

        # 14/15 confirm does not create scope_lock_v2.md or prd.md if absent.
        no_prd = _make_scope_locked_product(temp_root, product_type="website")
        no_prd_id = str(no_prd["product_id"])
        no_prd_dir = temp_root / "products" / no_prd_id
        no_prd_change = _write_change_file(
            temp_root,
            change_text.replace("add-out-of-scope-for-portfolio-website", "no-prd-scope-change"),
        )
        no_prd_result = confirm_scope_change(temp_root, no_prd_id, no_prd_change, confirm=True)
        expect("confirm does not create scope_lock_v2.md", not (no_prd_dir / "scope_lock_v2.md").exists(), failures)
        expect("confirm does not create prd.md if absent", not (no_prd_dir / "prd.md").exists(), failures)

        # 16 no model/provider/agent usage occurs.
        for script_name in ("product_scope_change.py", "ws_product_scope_change.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        # 17 CLI helper requires --confirm for write.
        cli_product = _make_scope_locked_with_prd(temp_root, approved=False)
        cli_product_id = str(cli_product["product_id"])
        cli_change = _write_change_file(
            temp_root,
            change_text.replace("add-out-of-scope-for-portfolio-website", "cli-confirm-change"),
        )
        cli_without_mode = _run_scope_change_script(
            ["--product", cli_product_id, "--file", str(cli_change)],
            temp_root,
        )
        expect(
            "CLI helper requires explicit mode flag",
            cli_without_mode.returncode != 0
            and "specify exactly one of --dry-run or --confirm" in (cli_without_mode.stderr or ""),
            failures,
            detail=f"rc={cli_without_mode.returncode}, stderr={cli_without_mode.stderr!r}",
        )
        cli_confirm = _run_scope_change_script(
            ["--product", cli_product_id, "--file", str(cli_change), "--confirm"],
            temp_root,
        )
        expect(
            "CLI helper requires --confirm for write",
            cli_confirm.returncode == 0 and "SCOPE CHANGE DECISION RECORDED" in (cli_confirm.stdout or ""),
            failures,
            detail=f"rc={cli_confirm.returncode}, stderr={cli_confirm.stderr!r}",
        )

        # 18 --dry-run remains no-write.
        dry_run_product = _make_scope_locked_with_prd(temp_root, approved=False)
        dry_run_id = str(dry_run_product["product_id"])
        dry_run_dir = temp_root / "products" / dry_run_id
        dry_run_change = _write_change_file(
            temp_root,
            change_text.replace("add-out-of-scope-for-portfolio-website", "dry-run-still-nowrite"),
        )
        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        before_product = (dry_run_dir / "product.yaml").read_text(encoding="utf-8")
        dry_run_result = _run_scope_change_script(
            ["--product", dry_run_id, "--file", str(dry_run_change), "--dry-run"],
            temp_root,
        )
        after_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect(
            "--dry-run remains no-write",
            dry_run_result.returncode == 0
            and before_files == after_files
            and before_product == (dry_run_dir / "product.yaml").read_text(encoding="utf-8"),
            failures,
            detail=f"rc={dry_run_result.returncode}, stderr={dry_run_result.stderr!r}",
        )

        expect(
            "confirm records stale artifacts when approval artifact exists",
            "decisions/prd_approval.md" in list(updated_payload.get("stale_artifacts", [])),
            failures,
            detail=str(updated_payload.get("stale_artifacts")),
        )
        expect(
            "confirm reports files written",
            decision_path.as_posix().endswith(".md") and str(no_prd_result["decision_path"]).endswith(".md"),
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
