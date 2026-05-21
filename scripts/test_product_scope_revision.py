#!/usr/bin/env python3
"""Temp-root tests for Product Lane scope revision dry-run preview."""

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
from product_scope_revision import (  # noqa: E402
    find_confirmed_scope_changes,
    load_scope_revision_inputs,
    parse_scope_change_decision,
    render_revised_scope_preview,
    render_scope_revision_dry_run,
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


def _answers_text(product_type: str) -> str:
    lines: list[str] = []
    for question in get_question_bank(product_type):
        qid = str(question["id"])
        lines.append(f"{qid}: answer for {qid}")
    return "\n".join(lines) + "\n"


def _make_scope_locked_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} scope revision sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _make_locked_product_with_prd(root: Path) -> dict[str, object]:
    locked = _make_scope_locked_product(root, product_type="website")
    write_prd(root, str(locked["product_id"]), confirm=True)
    return get_product_status(root, str(locked["product_id"]))


def _write_change_file(root: Path, *, change_id: str, field: str, proposed_value: str) -> Path:
    path = root / f"tmp_scope_revision_{uuid4().hex}.md"
    path.write_text(
        "\n".join(
            [
                f"change_id: {change_id}",
                "reason: Deterministic scope revision preview test.",
                f"field: {field}",
                "proposed_value: >",
                f"  {proposed_value}",
                "operator_note: Preview-only test change.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


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
    print("Product Scope Revision Validation")
    print("=================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_scope_revision_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        # 1 dry-run preview requires product exists.
        try:
            load_scope_revision_inputs(temp_root, "missing-product-scope-revision")
            failures.append("FAIL: missing product should be rejected")
        except Exception:
            print("PASS: dry-run preview requires product exists")

        # 2 requires scope_lock.md.
        missing_lock = _make_scope_locked_product(temp_root)
        missing_lock_id = str(missing_lock["product_id"])
        missing_lock_dir = temp_root / "products" / missing_lock_id
        (missing_lock_dir / "scope_lock.md").unlink()
        try:
            load_scope_revision_inputs(temp_root, missing_lock_id)
            failures.append("FAIL: missing scope_lock.md should be rejected")
        except FileNotFoundError:
            print("PASS: dry-run preview requires scope_lock.md")

        # 3 requires scope_change_pending true.
        no_pending = _make_scope_locked_product(temp_root)
        try:
            load_scope_revision_inputs(temp_root, str(no_pending["product_id"]))
            failures.append("FAIL: missing scope_change_pending should be rejected")
        except ValueError:
            print("PASS: dry-run preview requires scope_change_pending true")

        # 4 requires at least one scope_change decision record.
        no_decision = _make_scope_locked_product(temp_root)
        no_decision_id = str(no_decision["product_id"])
        product_file = temp_root / "products" / no_decision_id / "product.yaml"
        payload = json.loads(product_file.read_text(encoding="utf-8"))
        payload["scope_change_pending"] = True
        product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_scope_revision_inputs(temp_root, no_decision_id)
            failures.append("FAIL: missing decision record should be rejected")
        except FileNotFoundError:
            print("PASS: dry-run preview requires at least one scope_change decision record")

        # Base product for positive cases.
        product = _make_locked_product_with_prd(temp_root)
        product_id = str(product["product_id"])
        product_dir = temp_root / "products" / product_id
        out_change = _write_change_file(
            temp_root,
            change_id="replace-out-of-scope",
            field="out_of_scope",
            proposed_value="Backend services, authentication, CMS/blog engine, payments, and unrelated rewrites are out of scope.",
        )
        confirm_scope_change(temp_root, product_id, out_change, confirm=True)

        scope_before = (product_dir / "scope_lock.md").read_text(encoding="utf-8")
        prd_before = (product_dir / "prd.md").read_text(encoding="utf-8")
        product_before = (product_dir / "product.yaml").read_text(encoding="utf-8")
        files_before = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())

        revision_payload = load_scope_revision_inputs(temp_root, product_id)
        decisions = find_confirmed_scope_changes(temp_root, product_id)
        expect("parses confirmed scope_change decision", decisions[0]["change_id"] == "replace-out-of-scope", failures)
        parsed_decision = parse_scope_change_decision(Path(decisions[0]["decision_path"]).read_text(encoding="utf-8"))
        expect("parses confirmed scope_change decision fields", parsed_decision["field"] == "out_of_scope", failures)

        preview = render_revised_scope_preview(
            revision_payload["product_record"],
            revision_payload["scope_lock_text"],
            revision_payload["changes"],
        )
        report = render_scope_revision_dry_run(revision_payload["product_record"], preview)
        files_after_preview = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())

        # 6 previews out_of_scope replacement.
        expect(
            "previews out_of_scope replacement",
            "Out of Scope" in report and "Backend services, authentication, CMS/blog engine" in report,
            failures,
        )

        # 7 previews constraints replacement/addition.
        constraints_product = _make_scope_locked_product(temp_root)
        constraints_id = str(constraints_product["product_id"])
        constraints_change = _write_change_file(
            temp_root,
            change_id="update-constraints",
            field="constraints",
            proposed_value="Keep a lightweight static deployment and avoid new third-party SaaS dependencies.",
        )
        confirm_scope_change(temp_root, constraints_id, constraints_change, confirm=True)
        constraints_payload = load_scope_revision_inputs(temp_root, constraints_id)
        constraints_preview = render_revised_scope_preview(
            constraints_payload["product_record"],
            constraints_payload["scope_lock_text"],
            constraints_payload["changes"],
        )
        constraints_report = render_scope_revision_dry_run(constraints_payload["product_record"], constraints_preview)
        expect(
            "previews constraints replacement/addition",
            "Constraints" in constraints_report and "lightweight static deployment" in constraints_report,
            failures,
        )

        # 8 rejects unsupported change field.
        bad_product = _make_scope_locked_product(temp_root)
        bad_id = str(bad_product["product_id"])
        bad_dir = temp_root / "products" / bad_id
        bad_decisions = bad_dir / "decisions"
        bad_decisions.mkdir(parents=True, exist_ok=True)
        bad_payload = json.loads((bad_dir / "product.yaml").read_text(encoding="utf-8"))
        bad_payload["scope_change_pending"] = True
        (bad_dir / "product.yaml").write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")
        (bad_decisions / "scope_change_bad.md").write_text(
            "# Scope Change Decision\n\n- change_id: `bad`\n- reason: bad test\n- field: `launch_plan`\n- proposed_value: no\n",
            encoding="utf-8",
        )
        try:
            load_scope_revision_inputs(temp_root, bad_id)
            failures.append("FAIL: unsupported change field should be rejected")
        except ValueError:
            print("PASS: rejects unsupported change field")

        # 9 reports stale_artifacts from product.yaml.
        expect(
            "reports stale_artifacts from product.yaml",
            "prd.md" in report,
            failures,
        )

        # 10 includes generated_from section.
        expect(
            "includes generated_from section",
            "## Generated From" in report and "- product.yaml" in report and "- scope_lock.md" in report,
            failures,
        )

        # 11 includes DRY RUN / no files written.
        expect(
            "includes DRY RUN / no files written",
            "DRY RUN - no files written." in report,
            failures,
        )

        # 12 writes no files.
        expect("writes no files", files_before == files_after_preview, failures)

        # 13 does not update product.yaml.
        expect(
            "does not update product.yaml",
            (product_dir / "product.yaml").read_text(encoding="utf-8") == product_before,
            failures,
        )

        # 14 does not modify scope_lock.md.
        expect(
            "does not modify scope_lock.md",
            (product_dir / "scope_lock.md").read_text(encoding="utf-8") == scope_before,
            failures,
        )

        # 15 does not modify prd.md.
        expect(
            "does not modify prd.md",
            (product_dir / "prd.md").read_text(encoding="utf-8") == prd_before,
            failures,
        )

        # 16 does not create scope_lock_v2.md.
        expect(
            "does not create scope_lock_v2.md",
            not (product_dir / "scope_lock_v2.md").exists(),
            failures,
        )

        # 17 no model/provider/agent usage occurs.
        for script_name in ("product_scope_revision.py", "ws_product_scope_revision.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        # 18 CLI helper requires --dry-run.
        cli_without_dry_run = _run_scope_revision_script(["--product", product_id], temp_root)
        expect(
            "CLI helper requires --dry-run",
            cli_without_dry_run.returncode != 0
            and "specify exactly one of --dry-run or --confirm" in (cli_without_dry_run.stderr or ""),
            failures,
            detail=f"rc={cli_without_dry_run.returncode}, stderr={cli_without_dry_run.stderr!r}",
        )
        cli_with_dry_run = _run_scope_revision_script(["--product", product_id, "--dry-run"], temp_root)
        expect(
            "CLI dry-run preview succeeds",
            cli_with_dry_run.returncode == 0 and "Scope Revision Preview" in (cli_with_dry_run.stdout or ""),
            failures,
            detail=f"rc={cli_with_dry_run.returncode}, stderr={cli_with_dry_run.stderr!r}",
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
