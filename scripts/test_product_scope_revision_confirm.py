#!/usr/bin/env python3
"""Temp-root tests for Product Lane scope revision confirm flow."""

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
        title=f"{product_type} scope revision confirm sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _make_revision_ready_product(root: Path) -> tuple[dict[str, object], Path]:
    record = _make_scope_locked_product(root, product_type="website")
    product_id = str(record["product_id"])
    write_prd(root, product_id, confirm=True)
    change_file = root / f"tmp_scope_revision_confirm_{uuid4().hex}.md"
    change_file.write_text(
        "\n".join(
            [
                "change_id: add-out-of-scope-for-portfolio-website",
                "reason: PRD review found Out of Scope TODO/UNKNOWN.",
                "field: out_of_scope",
                "proposed_value: >",
                "  Backend services, authentication, CMS/blog engine, payment features,",
                "  complex animations, and unrelated project source-code rewrites are out of scope.",
                "operator_note: This change fills a missing source answer discovered during PRD review.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    confirm_scope_change(root, product_id, change_file, confirm=True)
    return get_product_status(root, product_id), change_file


def _run_scope_revision_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_scope_revision.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product Scope Revision Confirm Validation")
    print("=========================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_scope_revision_confirm_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        product, _change_file = _make_revision_ready_product(temp_root)
        product_id = str(product["product_id"])
        product_dir = temp_root / "products" / product_id

        before_scope = (product_dir / "scope_lock.md").read_text(encoding="utf-8")
        before_prd = (product_dir / "prd.md").read_text(encoding="utf-8")
        before_answers = (product_dir / "answers.md").read_text(encoding="utf-8")
        before_state = json.loads((product_dir / "product.yaml").read_text(encoding="utf-8"))["state"]
        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())

        result = confirm_scope_revision(temp_root, product_id, confirm=True)
        updated_payload = json.loads((product_dir / "product.yaml").read_text(encoding="utf-8"))
        revision_path = product_dir / "scope_locks" / "scope_lock_v2.md"
        after_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())

        expect("confirm writes scope_locks/scope_lock_v2.md under temp product directory", revision_path.is_file(), failures)
        expect("confirm creates scope_locks/ if needed", (product_dir / "scope_locks").is_dir(), failures)
        expect("confirm updates product.yaml active_scope_lock", updated_payload.get("active_scope_lock") == "scope_locks/scope_lock_v2.md", failures, detail=str(updated_payload.get("active_scope_lock")))
        expect("confirm updates product.yaml active_scope_lock_hash", isinstance(updated_payload.get("active_scope_lock_hash"), str) and len(updated_payload.get("active_scope_lock_hash")) == 64, failures, detail=str(updated_payload.get("active_scope_lock_hash")))
        expect("confirm updates active_scope_revision to 2", updated_payload.get("active_scope_revision") == 2, failures, detail=str(updated_payload.get("active_scope_revision")))
        expect("confirm sets scope_change_pending false", updated_payload.get("scope_change_pending") is False, failures)
        expect("confirm keeps main state SCOPE_LOCKED", updated_payload.get("state") == before_state == "SCOPE_LOCKED", failures)
        expect("confirm keeps prd_status NEEDS_REVISION when prd.md exists", updated_payload.get("prd_status") == "NEEDS_REVISION", failures, detail=str(updated_payload.get("prd_status")))
        expect("confirm leaves stale_artifacts containing prd.md when prd.md exists", "prd.md" in list(updated_payload.get("stale_artifacts", [])), failures, detail=str(updated_payload.get("stale_artifacts")))

        # 10/11/12/13/14/15 refusal and write constraints.
        try:
            confirm_scope_revision(temp_root, "missing-product-scope-revision", confirm=True)
            failures.append("FAIL: confirm refuses missing product")
        except FileNotFoundError:
            print("PASS: confirm refuses missing product")

        missing_scope = _make_scope_locked_product(temp_root)
        missing_scope_id = str(missing_scope["product_id"])
        missing_scope_dir = temp_root / "products" / missing_scope_id
        (missing_scope_dir / "scope_lock.md").unlink()
        scope_change_file = temp_root / f"tmp_missing_scope_{uuid4().hex}.md"
        scope_change_file.write_text("change_id: x\nreason: x\nfield: out_of_scope\nproposed_value: y\n", encoding="utf-8")
        confirm_scope_change(temp_root, missing_scope_id, scope_change_file, confirm=True)
        try:
            confirm_scope_revision(temp_root, missing_scope_id, confirm=True)
            failures.append("FAIL: confirm refuses missing scope_lock.md")
        except FileNotFoundError:
            print("PASS: confirm refuses missing scope_lock.md")

        no_pending = _make_scope_locked_product(temp_root)
        try:
            confirm_scope_revision(temp_root, str(no_pending["product_id"]), confirm=True)
            failures.append("FAIL: confirm refuses no pending change")
        except ValueError:
            print("PASS: confirm refuses no pending change")

        missing_decision = _make_scope_locked_product(temp_root)
        missing_decision_id = str(missing_decision["product_id"])
        product_file = temp_root / "products" / missing_decision_id / "product.yaml"
        payload = json.loads(product_file.read_text(encoding="utf-8"))
        payload["scope_change_pending"] = True
        product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        try:
            confirm_scope_revision(temp_root, missing_decision_id, confirm=True)
            failures.append("FAIL: confirm refuses missing decision record")
        except FileNotFoundError:
            print("PASS: confirm refuses missing decision record")

        existing_target = _make_revision_ready_product(temp_root)[0]
        existing_target_id = str(existing_target["product_id"])
        existing_target_dir = temp_root / "products" / existing_target_id
        (existing_target_dir / "scope_locks").mkdir(parents=True, exist_ok=True)
        (existing_target_dir / "scope_locks" / "scope_lock_v2.md").write_text("existing\n", encoding="utf-8")
        try:
            confirm_scope_revision(temp_root, existing_target_id, confirm=True)
            failures.append("FAIL: confirm refuses existing scope_lock_v2.md")
        except FileExistsError:
            print("PASS: confirm refuses existing scope_lock_v2.md")

        unsupported = _make_scope_locked_product(temp_root)
        unsupported_id = str(unsupported["product_id"])
        unsupported_dir = temp_root / "products" / unsupported_id
        unsupported_decisions = unsupported_dir / "decisions"
        unsupported_decisions.mkdir(parents=True, exist_ok=True)
        unsupported_payload = json.loads((unsupported_dir / "product.yaml").read_text(encoding="utf-8"))
        unsupported_payload["scope_change_pending"] = True
        (unsupported_dir / "product.yaml").write_text(json.dumps(unsupported_payload, indent=2) + "\n", encoding="utf-8")
        (unsupported_decisions / "scope_change_bad.md").write_text(
            "# Scope Change Decision\n\n- change_id: `bad`\n- reason: bad\n- field: `launch_plan`\n- proposed_value: nope\n",
            encoding="utf-8",
        )
        try:
            confirm_scope_revision(temp_root, unsupported_id, confirm=True)
            failures.append("FAIL: confirm refuses unsupported change field")
        except ValueError:
            print("PASS: confirm refuses unsupported change field")

        expect("confirm does not modify original scope_lock.md", (product_dir / "scope_lock.md").read_text(encoding="utf-8") == before_scope, failures)
        expect("confirm does not modify prd.md", (product_dir / "prd.md").read_text(encoding="utf-8") == before_prd, failures)
        expect("confirm does not modify answers.md", (product_dir / "answers.md").read_text(encoding="utf-8") == before_answers, failures)
        expect("confirm does not create prd_v2.md", not (product_dir / "prd_v2.md").exists(), failures)

        created_files = sorted(set(after_files) - set(before_files))
        outside_files = [
            relpath for relpath in created_files
            if not relpath.startswith(f"products/{product_id}/")
        ]
        expect("confirm writes nothing outside products/<product_id>/", not outside_files, failures, detail=str(outside_files))

        for script_name in ("product_scope_revision.py", "ws_product_scope_revision.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        cli_product, _ = _make_revision_ready_product(temp_root)
        cli_product_id = str(cli_product["product_id"])
        cli_without_mode = _run_scope_revision_script(["--product", cli_product_id], temp_root)
        expect(
            "CLI helper requires mode",
            cli_without_mode.returncode != 0 and "specify exactly one of --dry-run or --confirm" in (cli_without_mode.stderr or ""),
            failures,
            detail=f"rc={cli_without_mode.returncode}, stderr={cli_without_mode.stderr!r}",
        )
        cli_confirm = _run_scope_revision_script(["--product", cli_product_id, "--confirm"], temp_root)
        expect(
            "CLI helper requires --confirm for write",
            cli_confirm.returncode == 0 and "SCOPE REVISION RECORDED" in (cli_confirm.stdout or ""),
            failures,
            detail=f"rc={cli_confirm.returncode}, stderr={cli_confirm.stderr!r}",
        )

        dry_run_product, _ = _make_revision_ready_product(temp_root)
        dry_run_id = str(dry_run_product["product_id"])
        dry_run_dir = temp_root / "products" / dry_run_id
        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        before_product = (dry_run_dir / "product.yaml").read_text(encoding="utf-8")
        dry_run_result = _run_scope_revision_script(["--product", dry_run_id, "--dry-run"], temp_root)
        after_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect(
            "--dry-run remains no-write",
            dry_run_result.returncode == 0
            and before_files == after_files
            and before_product == (dry_run_dir / "product.yaml").read_text(encoding="utf-8"),
            failures,
            detail=f"rc={dry_run_result.returncode}, stderr={dry_run_result.stderr!r}",
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
