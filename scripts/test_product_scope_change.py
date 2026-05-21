#!/usr/bin/env python3
"""Temp-root tests for Product Lane scope change dry-run preview."""

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
from product_scope_change import (  # noqa: E402
    compute_scope_change_impact,
    load_scope_change_inputs,
    parse_scope_change_text,
    render_scope_change_dry_run,
    validate_scope_change_request,
)
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
        if qid.endswith(".out_of_scope") or qid.endswith(".non_goals") or qid.endswith(".non_goal"):
            continue
        lines.append(f"{qid}: answer for {qid}")
    return "\n".join(lines) + "\n"


def _make_scope_locked_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} scope change sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    record["state"] = "INBOX"
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _make_scope_locked_with_prd(root: Path, *, product_type: str = "website", approved: bool = False) -> dict[str, object]:
    record = _make_scope_locked_product(root, product_type=product_type)
    product_id = str(record["product_id"])
    write_prd(root, product_id, confirm=True)
    product_file = root / "products" / product_id / "product.yaml"
    payload = json.loads(product_file.read_text(encoding="utf-8"))
    if approved:
        payload["prd_status"] = "APPROVED"
        payload["prd_reviewed_at"] = "2026-01-01T00:00:00Z"
        payload["prd_approved_at"] = "2026-01-01T00:00:00Z"
        payload["prd_review_notes"] = "deterministic test approval"
    product_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return get_product_status(root, product_id)


def _write_change_file(root: Path, content: str) -> Path:
    change_file = root / f"tmp_scope_change_{uuid4().hex}.md"
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
    print("Product Scope Change Validation")
    print("===============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_scope_change_{uuid4().hex}").resolve()
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

        # 1 parse valid change file.
        parsed = parse_scope_change_text(change_text)
        validated = validate_scope_change_request(parsed)
        expect(
            "parse valid change file",
            validated["field"] == "out_of_scope"
            and "Backend services" in validated["proposed_value"]
            and "complex animations" in validated["proposed_value"],
            failures,
        )

        # 2 reject missing required keys.
        try:
            validate_scope_change_request(parse_scope_change_text("reason: x\nfield: out_of_scope\nproposed_value: y\n"))
            failures.append("FAIL: missing required keys should be rejected")
        except ValueError:
            print("PASS: missing required keys rejected")

        # 3 reject blank proposed_value.
        try:
            validate_scope_change_request(
                parse_scope_change_text(
                    "change_id: test\nreason: x\nfield: out_of_scope\nproposed_value:   \n"
                )
            )
            failures.append("FAIL: blank proposed_value should be rejected")
        except ValueError:
            print("PASS: blank proposed_value rejected")

        # 4 reject unsupported field.
        try:
            validate_scope_change_request(
                parse_scope_change_text(
                    "change_id: test\nreason: x\nfield: unsupported_field\nproposed_value: value\n"
                )
            )
            failures.append("FAIL: unsupported field should be rejected")
        except ValueError:
            print("PASS: unsupported field rejected")

        # 5/6/7 dry-run impact reports target field / affected artifacts / prd stale.
        with_prd = _make_scope_locked_with_prd(temp_root, product_type="website", approved=False)
        with_prd_id = str(with_prd["product_id"])
        payload = load_scope_change_inputs(temp_root, with_prd_id)
        impact = compute_scope_change_impact(payload["product_record"], validated, payload["paths"])
        report = render_scope_change_dry_run(payload["product_record"], validated, impact)
        expect("dry-run impact reports target field", "- target_field: `out_of_scope`" in report, failures)
        expect(
            "dry-run impact reports affected artifacts",
            "## Affected Artifacts" in report and "- scope_lock.md: present" in report and "- prd.md: present" in report,
            failures,
        )
        expect(
            "SCOPE_LOCKED + prd.md reports PRD_WOULD_BECOME_STALE",
            "PRD_WOULD_BECOME_STALE" in report,
            failures,
        )

        # 8 APPROVED PRD reports APPROVAL_WOULD_BECOME_STALE.
        approved = _make_scope_locked_with_prd(temp_root, product_type="website", approved=True)
        approved_id = str(approved["product_id"])
        approved_payload = load_scope_change_inputs(temp_root, approved_id)
        approved_impact = compute_scope_change_impact(approved_payload["product_record"], validated, approved_payload["paths"])
        approved_report = render_scope_change_dry_run(approved_payload["product_record"], validated, approved_impact)
        expect(
            "APPROVED PRD reports APPROVAL_WOULD_BECOME_STALE",
            "APPROVAL_WOULD_BECOME_STALE" in approved_report,
            failures,
        )

        # 9 existing wireframes.md reports WIREFRAMES_WOULD_BECOME_STALE.
        wireframe_product = _make_scope_locked_with_prd(temp_root, product_type="website", approved=True)
        wireframe_id = str(wireframe_product["product_id"])
        wireframe_dir = temp_root / "products" / wireframe_id
        (wireframe_dir / "wireframes.md").write_text("# existing wireframes\n", encoding="utf-8")
        wireframe_payload = load_scope_change_inputs(temp_root, wireframe_id)
        wireframe_report = render_scope_change_dry_run(
            wireframe_payload["product_record"],
            validated,
            compute_scope_change_impact(wireframe_payload["product_record"], validated, wireframe_payload["paths"]),
        )
        expect(
            "existing wireframes.md reports WIREFRAMES_WOULD_BECOME_STALE",
            "WIREFRAMES_WOULD_BECOME_STALE" in wireframe_report,
            failures,
        )

        # 10 no downstream artifacts reports SCOPE_ONLY_CHANGE.
        scope_only = create_product(title=f"scope only {uuid4().hex[:8]}", product_type="website")
        save_product(scope_only, temp_root, confirm=True, allow_overwrite=False)
        scope_only_payload = load_scope_change_inputs(temp_root, str(scope_only["product_id"]))
        scope_only_report = render_scope_change_dry_run(
            scope_only_payload["product_record"],
            validated,
            compute_scope_change_impact(scope_only_payload["product_record"], validated, scope_only_payload["paths"]),
        )
        expect(
            "no downstream artifacts reports SCOPE_ONLY_CHANGE",
            "SCOPE_ONLY_CHANGE" in scope_only_report,
            failures,
        )

        # 11 command helper requires explicit mode flag.
        change_file = _write_change_file(temp_root, change_text)
        no_dry_run = _run_scope_change_script(
            ["--product", with_prd_id, "--file", str(change_file)],
            temp_root,
        )
        expect(
            "command helper requires explicit mode flag",
            no_dry_run.returncode != 0
            and "specify exactly one of --dry-run or --confirm" in (no_dry_run.stderr or ""),
            failures,
            detail=f"rc={no_dry_run.returncode}, stderr={no_dry_run.stderr!r}",
        )

        # 12/13/14/15 dry-run writes no files / no product.yaml update / no scope/prd changes / no decisions directory.
        before_files = sorted(
            path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file()
        )
        before_product = (temp_root / "products" / with_prd_id / "product.yaml").read_text(encoding="utf-8")
        before_scope = (temp_root / "products" / with_prd_id / "scope_lock.md").read_text(encoding="utf-8")
        before_prd = (temp_root / "products" / with_prd_id / "prd.md").read_text(encoding="utf-8")

        with_dry_run = _run_scope_change_script(
            ["--product", with_prd_id, "--file", str(change_file), "--dry-run"],
            temp_root,
        )
        expect(
            "dry-run command succeeds",
            with_dry_run.returncode == 0 and "Scope Change Impact Preview" in (with_dry_run.stdout or ""),
            failures,
            detail=f"rc={with_dry_run.returncode}, stderr={with_dry_run.stderr!r}",
        )
        expect(
            "dry-run writes no files",
            before_files
            == sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file()),
            failures,
        )
        expect(
            "no product.yaml update occurs",
            before_product == (temp_root / "products" / with_prd_id / "product.yaml").read_text(encoding="utf-8"),
            failures,
        )
        expect(
            "no scope_lock.md/prd.md changes occur",
            before_scope == (temp_root / "products" / with_prd_id / "scope_lock.md").read_text(encoding="utf-8")
            and before_prd == (temp_root / "products" / with_prd_id / "prd.md").read_text(encoding="utf-8"),
            failures,
        )
        expect(
            "no decisions directory is created",
            not (temp_root / "products" / with_prd_id / "decisions" / "scope_change_test.md").exists(),
            failures,
        )

        # 16 no model/provider/agent usage occurs.
        for script_name in ("product_scope_change.py", "ws_product_scope_change.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
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
