#!/usr/bin/env python3
"""Temp-root tests for Product Lane design run prepare confirm flow."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
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

from product_design_adapter import validate_design_tool  # noqa: E402
from product_design_run import prepare_design_run  # noqa: E402
from product_registry import create_product, initialize_products_dir, save_product  # noqa: E402
from product_scope_lock import compute_scope_lock_hash  # noqa: E402
from ws_product_design_run_prepare import main as prepare_cli_main  # noqa: E402


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


def _wireframe_text(*, include_generated_from: bool = True) -> str:
    lines = [
        "# Wireframe v1",
        "",
        "## Page/Screen Map",
        "",
        "- Home",
        "- Contact",
        "",
        "## ASCII/Text Wireframes",
        "",
        "[Home]",
        "[Hero] [CTA]",
        "",
        "## Component Inventory",
        "",
        "- Header",
        "- Hero",
        "- Footer",
        "",
        "## Navigation Model",
        "",
        "- Primary nav with Home/About/Contact",
        "",
        "## Content Hierarchy",
        "",
        "- Hero headline first",
        "",
        "## Responsive Notes",
        "",
        "- Mobile-first stacking",
        "",
        "## Accessibility Notes",
        "",
        "- Keyboard focus order defined",
        "",
    ]
    if include_generated_from:
        lines.extend(
            [
                "## Generated From",
                "",
                "- prds/prd_v2.md",
                "- scope_locks/scope_lock_v2.md",
                "- no model/provider/agent calls",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _write_record(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _make_product(
    root: Path,
    *,
    product_type: str = "website",
    include_tech_plan: bool = False,
    wireframe_content: str | None = None,
) -> tuple[str, Path]:
    record = create_product(
        title=f"design-run-prepare-{uuid4().hex[:8]}",
        product_type=product_type,
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    product_id = str(record["product_id"])
    pdir = root / "products" / product_id

    scope_rel = "scope_locks/scope_lock_v2.md"
    prd_rel = "prds/prd_v2.md"
    wireframe_rel = "wireframes/wireframe_v1.md"
    tech_rel = "technical_plans/technical_plan_v1.md"

    scope_path = pdir / scope_rel
    prd_path = pdir / prd_rel
    wireframe_path = pdir / wireframe_rel
    scope_path.parent.mkdir(parents=True, exist_ok=True)
    prd_path.parent.mkdir(parents=True, exist_ok=True)
    wireframe_path.parent.mkdir(parents=True, exist_ok=True)

    scope_text = "# Scope Lock Revision v2\n\n## In Scope\n- Marketing website refresh.\n"
    prd_text = "# PRD v2\n\n## Objective\n- Improve conversion.\n"
    wireframe_text = wireframe_content if wireframe_content is not None else _wireframe_text()
    scope_path.write_text(scope_text, encoding="utf-8", newline="\n")
    prd_path.write_text(prd_text, encoding="utf-8", newline="\n")
    wireframe_path.write_text(wireframe_text, encoding="utf-8", newline="\n")

    payload = json.loads((pdir / "product.yaml").read_text(encoding="utf-8"))
    payload["state"] = "SCOPE_LOCKED"
    payload["prd_status"] = "APPROVED"
    payload["active_scope_lock"] = scope_rel
    payload["active_scope_lock_hash"] = compute_scope_lock_hash(scope_text)
    payload["active_scope_revision"] = 2
    payload["active_prd"] = prd_rel
    payload["active_prd_hash"] = hashlib.sha256(prd_text.encode("utf-8")).hexdigest()
    payload["active_prd_revision"] = 2
    payload["active_wireframe"] = wireframe_rel
    payload["active_wireframe_hash"] = hashlib.sha256(wireframe_text.encode("utf-8")).hexdigest()
    payload["wireframe_status"] = "DRAFTED"
    if include_tech_plan:
        tech_path = pdir / tech_rel
        tech_path.parent.mkdir(parents=True, exist_ok=True)
        tech_text = "# Technical Plan v1\n\n- Optional context.\n"
        tech_path.write_text(tech_text, encoding="utf-8", newline="\n")
        payload["active_technical_plan"] = tech_rel
        payload["active_technical_plan_hash"] = hashlib.sha256(tech_text.encode("utf-8")).hexdigest()
        payload["active_technical_plan_revision"] = 1
    _write_record(pdir / "product.yaml", payload)
    return product_id, pdir


def _expect_blocked(root: Path, product_id: str, failures: list[str], name: str, expected_fragment: str) -> None:
    try:
        prepare_design_run(root, product_id, "open-design", confirm=True)
        failures.append(f"FAIL: {name} - expected failure")
    except (ValueError, FileNotFoundError) as exc:
        expect(name, expected_fragment.lower() in str(exc).lower(), failures, str(exc))


def main() -> int:
    print("Product Design Run Prepare Validation")
    print("====================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_design_run_prepare_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        expect("accepts tool open-design", validate_design_tool("open-design") == "open-design", failures)
        try:
            prepare_design_run(temp_root, "missing-product", "unknown", confirm=True)
            failures.append("FAIL: prepare refuses unknown tool - expected exception")
        except ValueError:
            expect("prepare refuses unknown tool", True, failures)
        try:
            prepare_design_run(temp_root, "missing-product", "../open-design", confirm=True)
            failures.append("FAIL: prepare refuses path traversal tool - expected exception")
        except ValueError:
            expect("prepare refuses path traversal tool", True, failures)

        ready_product_id, ready_dir = _make_product(temp_root, product_type="website")
        product_yaml = ready_dir / "product.yaml"
        product_before = json.loads(product_yaml.read_text(encoding="utf-8"))
        before_files = sorted(
            path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file()
        )
        before_dirs = sorted(
            path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_dir()
        )

        result = prepare_design_run(temp_root, ready_product_id, "open-design", confirm=True)
        run_dir = ready_dir / "design_runs" / "open_design" / "open-design-render-v1"
        design_input = run_dir / "design_input.yaml"
        design_prompt = run_dir / "design_prompt.md"
        design_run = run_dir / "design_run.yaml"
        operator_report = run_dir / "operator_report.md"

        expect("prepare writes design_input.yaml", design_input.is_file(), failures)
        expect("prepare writes design_prompt.md", design_prompt.is_file(), failures)
        expect("prepare writes design_run.yaml", design_run.is_file(), failures)
        expect("prepare optionally writes operator_report.md if implemented", operator_report.is_file(), failures)

        after_files = sorted(
            path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file()
        )
        after_dirs = sorted(
            path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_dir()
        )
        created_files = sorted(set(after_files) - set(before_files))
        created_dirs = sorted(set(after_dirs) - set(before_dirs))

        allowed_prefix = f"products/{ready_product_id}/design_runs/open_design/open-design-render-v1/"
        expect(
            "prepare creates only allowed sandbox directory",
            all(d.startswith(f"products/{ready_product_id}/design_runs") for d in created_dirs),
            failures,
            detail=str(created_dirs),
        )
        expect(
            "prepare writes only allowed sandbox files",
            all(path.startswith(allowed_prefix) for path in created_files),
            failures,
            detail=str(created_files),
        )
        expect("prepare refuses duplicate existing design_run.yaml", _duplicate_blocked(temp_root, ready_product_id), failures)

        unsupported_id, _unsupported_dir = _make_product(temp_root, product_type="automation")
        _expect_blocked(temp_root, unsupported_id, failures, "prepare refuses unsupported product type", "not ui-capable")

        scope_mismatch_id, scope_mismatch_dir = _make_product(temp_root)
        data = json.loads((scope_mismatch_dir / "product.yaml").read_text(encoding="utf-8"))
        data["active_scope_lock_hash"] = "deadbeef"
        _write_record(scope_mismatch_dir / "product.yaml", data)
        _expect_blocked(temp_root, scope_mismatch_id, failures, "prepare refuses active scope hash mismatch", "active_scope_lock hash mismatch")

        prd_mismatch_id, prd_mismatch_dir = _make_product(temp_root)
        data = json.loads((prd_mismatch_dir / "product.yaml").read_text(encoding="utf-8"))
        data["active_prd_hash"] = "deadbeef"
        _write_record(prd_mismatch_dir / "product.yaml", data)
        _expect_blocked(temp_root, prd_mismatch_id, failures, "prepare refuses active PRD hash mismatch", "active_prd hash mismatch")

        wf_mismatch_id, wf_mismatch_dir = _make_product(temp_root)
        data = json.loads((wf_mismatch_dir / "product.yaml").read_text(encoding="utf-8"))
        data["active_wireframe_hash"] = "deadbeef"
        _write_record(wf_mismatch_dir / "product.yaml", data)
        _expect_blocked(temp_root, wf_mismatch_id, failures, "prepare refuses active wireframe hash mismatch", "active_wireframe hash mismatch")

        prd_status_id, prd_status_dir = _make_product(temp_root)
        data = json.loads((prd_status_dir / "product.yaml").read_text(encoding="utf-8"))
        data["prd_status"] = "DRAFTED"
        _write_record(prd_status_dir / "product.yaml", data)
        _expect_blocked(temp_root, prd_status_id, failures, "prepare refuses unapproved PRD", "prd_status must be APPROVED")

        wf_fail_id, _wf_fail_dir = _make_product(temp_root, wireframe_content=_wireframe_text(include_generated_from=False))
        _expect_blocked(temp_root, wf_fail_id, failures, "prepare refuses wireframe review FAIL", "wireframe review status must be PASS")

        with_tech_id, with_tech_dir = _make_product(temp_root, include_tech_plan=True)
        _ = prepare_design_run(temp_root, with_tech_id, "open-design", confirm=True)
        with_tech_run = with_tech_dir / "design_runs" / "open_design" / "open-design-render-v1" / "design_run.yaml"
        with_tech_payload = json.loads(with_tech_run.read_text(encoding="utf-8"))
        source_artifacts = with_tech_payload.get("source_artifacts", {})
        expect(
            "prepare includes active technical plan if present",
            source_artifacts.get("active_technical_plan") == "technical_plans/technical_plan_v1.md",
            failures,
            detail=str(source_artifacts),
        )

        product_after = json.loads(product_yaml.read_text(encoding="utf-8"))
        active_design_keys = [k for k in product_after.keys() if k.startswith("active_design_")]
        expect(
            "prepare does not update product.yaml active_design_* metadata",
            not active_design_keys and product_before.get("updated_at") == product_after.get("updated_at"),
            failures,
            detail=str(active_design_keys),
        )

        expect(
            "prepare does not create raw_output/prototype/screenshots/export unless explicitly intended",
            not any((run_dir / folder).exists() for folder in ("raw_output", "prototype", "screenshots", "export")),
            failures,
        )
        expect(
            "prepare does not execute Open Design",
            result["open_design_executed"] is False and result["open_design_installed"] is False,
            failures,
        )
        expect(
            "prepare does not write app/source paths",
            all(all(token not in path for token in ("/src/", "/app/", "/components/")) for path in created_files) and not any(
                path.endswith("package.json") for path in created_files
            ),
            failures,
            detail=str(created_files),
        )

        with contextlib.redirect_stdout(io.StringIO()) as stdout_capture, contextlib.redirect_stderr(io.StringIO()) as stderr_capture:
            rc = prepare_cli_main(
                [
                    "--root",
                    str(temp_root),
                    "--product",
                    ready_product_id,
                    "--tool",
                    "open-design",
                ]
            )
        expect(
            "CLI requires --confirm",
            rc == 2 and "--confirm is required" in (stderr_capture.getvalue() or stdout_capture.getvalue()),
            failures,
        )

        for script_name in ("product_design_run.py", "ws_product_design_run_prepare.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            disallowed = ("pip install", "npm install", "openai.", "anthropic.", "requests.post(")
            expect(
                "prepare does not execute Open Design",
                all(token not in source for token in disallowed),
                failures,
                script_name,
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


def _duplicate_blocked(root: Path, product_id: str) -> bool:
    try:
        prepare_design_run(root, product_id, "open-design", confirm=True)
    except FileExistsError:
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())

