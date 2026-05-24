#!/usr/bin/env python3
"""Temp-root tests for Product Lane design render dry-run."""

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

from product_design_adapter import (  # noqa: E402
    FORBIDDEN_FUTURE_PATHS,
    PLANNED_RENDER_FILES,
    build_design_render_preview,
    validate_design_tool,
)
from product_registry import create_product, initialize_products_dir, save_product  # noqa: E402
from product_scope_lock import compute_scope_lock_hash  # noqa: E402
from ws_product_design_render import main as render_cli_main  # noqa: E402


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
        title=f"design-render-{uuid4().hex[:8]}",
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
        build_design_render_preview(root, product_id, "open-design")
        failures.append(f"FAIL: {name} - expected failure")
    except (ValueError, FileNotFoundError) as exc:
        expect(name, expected_fragment.lower() in str(exc).lower(), failures, str(exc))


def main() -> int:
    print("Product Design Render Validation")
    print("===============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_design_render_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        expect("accepts tool open-design", validate_design_tool("open-design") == "open-design", failures)
        try:
            validate_design_tool("unknown")
            failures.append("FAIL: rejects unknown tool - expected exception")
        except ValueError:
            expect("rejects unknown tool", True, failures)
        try:
            validate_design_tool("../open-design")
            failures.append("FAIL: rejects path traversal tool - expected exception")
        except ValueError:
            expect("rejects path traversal tool", True, failures)

        ready_product_id, ready_dir = _make_product(temp_root, product_type="website")
        preview = build_design_render_preview(temp_root, ready_product_id, "open-design")
        expect(
            "passes for UI product with approved active PRD, matching active scope, and matching active wireframe",
            preview["readiness_status"] == "READY_FOR_DESIGN_RENDER_DRY_RUN",
            failures,
        )
        expect("preview includes planned run directory", "products/" in preview["planned_run_directory"], failures)
        expect(
            "preview includes design_input.yaml, design_prompt.md, design_run.yaml",
            all(name in preview["planned_files"] for name in ("design_input.yaml", "design_prompt.md", "design_run.yaml")),
            failures,
        )
        expect(
            "preview includes forbidden app/source write paths",
            all(item in preview["forbidden_paths"] for item in FORBIDDEN_FUTURE_PATHS),
            failures,
        )
        expect("preview includes slash command /design render", preview["slash_command_surface"] == "/design render", failures)
        expect(
            "preview includes canonical mapped ws command",
            "ws product-design-render --product" in preview["canonical_ws_command"],
            failures,
        )
        expect("dry-run does not create design_runs/", not (ready_dir / "design_runs").exists(), failures)
        before_files = sorted(str(path.relative_to(ready_dir)) for path in ready_dir.rglob("*"))
        _ = build_design_render_preview(temp_root, ready_product_id, "open-design")
        after_files = sorted(str(path.relative_to(ready_dir)) for path in ready_dir.rglob("*"))
        expect("dry-run writes no files", before_files == after_files, failures)
        expect(
            "Open Design is not executed or installed",
            preview["external_execution_status"]["open_design_executed"] is False
            and preview["external_execution_status"]["install_attempted"] is False,
            failures,
        )

        unsupported_id, _unsupported_dir = _make_product(temp_root, product_type="automation")
        _expect_blocked(temp_root, unsupported_id, failures, "blocks unsupported product type", "not UI-capable")

        missing_scope_id, missing_scope_dir = _make_product(temp_root)
        data = json.loads((missing_scope_dir / "product.yaml").read_text(encoding="utf-8"))
        data["active_scope_lock"] = ""
        _write_record(missing_scope_dir / "product.yaml", data)
        _expect_blocked(temp_root, missing_scope_id, failures, "blocks missing active_scope_lock", "missing active_scope_lock")

        scope_mismatch_id, scope_mismatch_dir = _make_product(temp_root)
        data = json.loads((scope_mismatch_dir / "product.yaml").read_text(encoding="utf-8"))
        data["active_scope_lock_hash"] = "deadbeef"
        _write_record(scope_mismatch_dir / "product.yaml", data)
        _expect_blocked(temp_root, scope_mismatch_id, failures, "blocks active_scope_lock hash mismatch", "active_scope_lock hash mismatch")

        missing_prd_id, missing_prd_dir = _make_product(temp_root)
        data = json.loads((missing_prd_dir / "product.yaml").read_text(encoding="utf-8"))
        data["active_prd"] = ""
        _write_record(missing_prd_dir / "product.yaml", data)
        _expect_blocked(temp_root, missing_prd_id, failures, "blocks missing active_prd", "missing active_prd")

        prd_mismatch_id, prd_mismatch_dir = _make_product(temp_root)
        data = json.loads((prd_mismatch_dir / "product.yaml").read_text(encoding="utf-8"))
        data["active_prd_hash"] = "deadbeef"
        _write_record(prd_mismatch_dir / "product.yaml", data)
        _expect_blocked(temp_root, prd_mismatch_id, failures, "blocks active_prd hash mismatch", "active_prd hash mismatch")

        prd_status_id, prd_status_dir = _make_product(temp_root)
        data = json.loads((prd_status_dir / "product.yaml").read_text(encoding="utf-8"))
        data["prd_status"] = "DRAFTED"
        _write_record(prd_status_dir / "product.yaml", data)
        _expect_blocked(temp_root, prd_status_id, failures, "blocks prd_status not APPROVED", "prd_status must be APPROVED")

        missing_wf_id, missing_wf_dir = _make_product(temp_root)
        data = json.loads((missing_wf_dir / "product.yaml").read_text(encoding="utf-8"))
        data["active_wireframe"] = ""
        _write_record(missing_wf_dir / "product.yaml", data)
        _expect_blocked(temp_root, missing_wf_id, failures, "blocks missing active_wireframe", "missing active_wireframe")

        wf_mismatch_id, wf_mismatch_dir = _make_product(temp_root)
        data = json.loads((wf_mismatch_dir / "product.yaml").read_text(encoding="utf-8"))
        data["active_wireframe_hash"] = "deadbeef"
        _write_record(wf_mismatch_dir / "product.yaml", data)
        _expect_blocked(temp_root, wf_mismatch_id, failures, "blocks active_wireframe hash mismatch", "active_wireframe hash mismatch")

        wf_fail_id, _wf_fail_dir = _make_product(temp_root, wireframe_content=_wireframe_text(include_generated_from=False))
        _expect_blocked(temp_root, wf_fail_id, failures, "blocks wireframe review FAIL", "wireframe review status must be PASS")

        with_tech_id, _with_tech_dir = _make_product(temp_root, include_tech_plan=True)
        preview_with_tech = build_design_render_preview(temp_root, with_tech_id, "open-design")
        expect(
            "active technical plan is reported if present but not required",
            preview_with_tech["optional_technical_plan"]["present"] is True
            and preview_with_tech["optional_technical_plan"]["required"] is False,
            failures,
        )
        expect(
            "preview includes planned files",
            all(name in preview_with_tech["planned_files"] for name in PLANNED_RENDER_FILES),
            failures,
        )

        with contextlib.redirect_stdout(io.StringIO()) as stdout_capture:
            rc = render_cli_main(
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
            "CLI requires --dry-run",
            rc == 2 and "Write-mode product-design-render is not implemented in this slice. Use --dry-run." in stdout_capture.getvalue(),
            failures,
        )

        with contextlib.redirect_stdout(io.StringIO()):
            rc = render_cli_main(
                [
                    "--root",
                    str(temp_root),
                    "--product",
                    ready_product_id,
                    "--tool",
                    "open-design",
                    "--dry-run",
                ]
            )
        expect("dry-run CLI succeeds", rc == 0, failures)

        for script_name in ("product_design_adapter.py", "ws_product_design_render.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            disallowed = ("import requests", "subprocess.run(", "pip install", "npm install", "openai.", "anthropic.")
            expect(
                "Open Design is not executed or installed",
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


if __name__ == "__main__":
    raise SystemExit(main())
