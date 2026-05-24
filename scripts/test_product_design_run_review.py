#!/usr/bin/env python3
"""Temp-root tests for Product Lane design run review preview/write flow."""

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

from product_design_run import prepare_design_run  # noqa: E402
from product_design_run_review import (  # noqa: E402
    DESIGN_INPUT_FILENAME,
    DESIGN_PROMPT_FILENAME,
    DESIGN_REVIEW_HTML_FILENAME,
    DESIGN_REVIEW_MANIFEST_FILENAME,
    DESIGN_REVIEW_REPORT_FILENAME,
    DESIGN_RUN_FILENAME,
    build_design_run_review,
    render_design_run_review_preview,
    write_design_run_review_artifacts,
)
from product_registry import create_product, initialize_products_dir, save_product  # noqa: E402
from product_scope_lock import compute_scope_lock_hash  # noqa: E402
from ws_product_design_run_review import main as review_cli_main  # noqa: E402


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


def _write_record(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _wireframe_text() -> str:
    return "\n".join(
        [
            "# Wireframe v1",
            "",
            "## Page/Screen Map",
            "- Home",
            "- Contact",
            "",
            "## ASCII/Text Wireframes",
            "[Home]",
            "[Hero] [CTA]",
            "",
            "## Component Inventory",
            "- Header",
            "- Hero",
            "",
            "## Navigation Model",
            "- Primary nav",
            "",
            "## Content Hierarchy",
            "- Hero first",
            "",
            "## Responsive Notes",
            "- Mobile-first",
            "",
            "## Accessibility Notes",
            "- Keyboard support",
            "",
            "## Generated From",
            "- prds/prd_v2.md",
            "- scope_locks/scope_lock_v2.md",
            "- no model/provider/agent calls",
            "",
        ]
    ) + "\n"


def _make_product(root: Path) -> tuple[str, Path]:
    record = create_product(
        title=f"design-run-review-{uuid4().hex[:8]}",
        product_type="website",
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    product_id = str(record["product_id"])
    pdir = root / "products" / product_id

    scope_rel = "scope_locks/scope_lock_v2.md"
    prd_rel = "prds/prd_v2.md"
    wireframe_rel = "wireframes/wireframe_v1.md"

    scope_text = "# Scope Lock Revision v2\n\n## In Scope\n- Marketing website refresh.\n"
    prd_text = "# PRD v2\n\n## Objective\n- Improve conversion.\n"
    wireframe_text = _wireframe_text()

    (pdir / scope_rel).parent.mkdir(parents=True, exist_ok=True)
    (pdir / prd_rel).parent.mkdir(parents=True, exist_ok=True)
    (pdir / wireframe_rel).parent.mkdir(parents=True, exist_ok=True)
    (pdir / scope_rel).write_text(scope_text, encoding="utf-8", newline="\n")
    (pdir / prd_rel).write_text(prd_text, encoding="utf-8", newline="\n")
    (pdir / wireframe_rel).write_text(wireframe_text, encoding="utf-8", newline="\n")

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
    _write_record(pdir / "product.yaml", payload)

    return product_id, pdir


def _prepared_run_paths(temp_root: Path, product_id: str) -> tuple[Path, Path, Path, Path]:
    run_dir = temp_root / "products" / product_id / "design_runs" / "open_design" / "open-design-render-v1"
    design_run = run_dir / DESIGN_RUN_FILENAME
    design_input = run_dir / DESIGN_INPUT_FILENAME
    design_prompt = run_dir / DESIGN_PROMPT_FILENAME
    return run_dir, design_run, design_input, design_prompt


def _expect_build_fails(
    temp_root: Path,
    product_id: str,
    failures: list[str],
    name: str,
    expected_fragment: str,
) -> None:
    try:
        _ = build_design_run_review(temp_root, product_id, "open-design")
        failures.append(f"FAIL: {name} - expected failure")
    except (FileNotFoundError, ValueError) as exc:
        expect(name, expected_fragment.lower() in str(exc).lower(), failures, str(exc))


def _write_run_payload(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    print("Product Design Run Review Validation")
    print("===================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_design_run_review_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)
        product_id, product_dir = _make_product(temp_root)

        _ = prepare_design_run(temp_root, product_id, "open-design", confirm=True)
        run_dir, design_run, design_input, design_prompt = _prepared_run_paths(temp_root, product_id)
        operator_report = run_dir / "operator_report.md"
        review_dir = run_dir / "review"

        product_yaml = product_dir / "product.yaml"
        product_before = product_yaml.read_text(encoding="utf-8")
        packet_before_hashes = {
            DESIGN_RUN_FILENAME: hashlib.sha256(design_run.read_bytes()).hexdigest(),
            DESIGN_INPUT_FILENAME: hashlib.sha256(design_input.read_bytes()).hexdigest(),
            DESIGN_PROMPT_FILENAME: hashlib.sha256(design_prompt.read_bytes()).hexdigest(),
        }

        before_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())

        review_model = build_design_run_review(temp_root, product_id, "open-design")
        preview_text = render_design_run_review_preview(review_model)
        expect("dry-run passes for prepared design run packet", review_model["review_status"] in {"PASS", "WARN"}, failures)
        expect(
            "dry-run reports planned review artifact paths",
            all(name in preview_text for name in (DESIGN_REVIEW_HTML_FILENAME, DESIGN_REVIEW_MANIFEST_FILENAME, DESIGN_REVIEW_REPORT_FILENAME)),
            failures,
        )

        after_preview_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("dry-run writes no files", before_files == after_preview_files, failures)
        expect("dry-run does not create review/", not review_dir.exists(), failures)

        write_result = write_design_run_review_artifacts(review_model, confirm=True)
        html_path = review_dir / DESIGN_REVIEW_HTML_FILENAME
        manifest_path = review_dir / DESIGN_REVIEW_MANIFEST_FILENAME
        report_path = review_dir / DESIGN_REVIEW_REPORT_FILENAME
        expect("confirm writes design_run_review.html", html_path.is_file(), failures)
        expect("confirm writes design_run_review_manifest.json", manifest_path.is_file(), failures)
        expect("confirm writes design_run_review_report.md", report_path.is_file(), failures)

        after_confirm_files = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        created_files = sorted(set(after_confirm_files) - set(before_files))
        allowed_prefix = f"products/{product_id}/design_runs/open_design/open-design-render-v1/review/"
        expect(
            "confirm writes only under review/",
            created_files and all(path.startswith(allowed_prefix) for path in created_files),
            failures,
            detail=str(created_files),
        )
        expect(
            "confirm does not create raw_output/prototype/screenshots/export",
            not any((run_dir / folder).exists() for folder in ("raw_output", "prototype", "screenshots", "export")),
            failures,
        )
        expect(
            "confirm does not write app/source files",
            all(all(token not in path for token in ("/src/", "/app/", "/components/")) for path in created_files)
            and not any(path.endswith("package.json") for path in created_files),
            failures,
            detail=str(created_files),
        )

        expect(
            "confirm refuses duplicate design_run_review.html",
            _duplicate_blocked(review_model),
            failures,
        )

        expect(
            "confirm does not update product.yaml",
            product_yaml.read_text(encoding="utf-8") == product_before,
            failures,
        )
        expect(
            "confirm does not modify design_input.yaml",
            hashlib.sha256(design_input.read_bytes()).hexdigest() == packet_before_hashes[DESIGN_INPUT_FILENAME],
            failures,
        )
        expect(
            "confirm does not modify design_prompt.md",
            hashlib.sha256(design_prompt.read_bytes()).hexdigest() == packet_before_hashes[DESIGN_PROMPT_FILENAME],
            failures,
        )
        expect(
            "confirm does not modify design_run.yaml",
            hashlib.sha256(design_run.read_bytes()).hexdigest() == packet_before_hashes[DESIGN_RUN_FILENAME],
            failures,
        )

        html_text = html_path.read_text(encoding="utf-8").lower()
        expect(
            "HTML is self-contained with no external CSS/JS/CDN references",
            all(
                token not in html_text
                for token in ("<script src=", "<link rel=", "http://", "https://", "cdn.")
            ),
            failures,
        )
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        hashes = manifest_payload.get("source_packet_hashes", {})
        expect(
            "manifest includes packet file hashes",
            isinstance(hashes, dict)
            and DESIGN_RUN_FILENAME in hashes
            and DESIGN_INPUT_FILENAME in hashes
            and DESIGN_PROMPT_FILENAME in hashes,
            failures,
            detail=str(hashes),
        )
        expect(
            "no Open Design execution",
            write_result["open_design_executed"] is False and write_result["open_design_installed"] is False,
            failures,
        )

        with contextlib.redirect_stdout(io.StringIO()) as stdout_capture, contextlib.redirect_stderr(io.StringIO()) as stderr_capture:
            rc = review_cli_main(
                [
                    "--root",
                    str(temp_root),
                    "--product",
                    product_id,
                    "--tool",
                    "open-design",
                ]
            )
        expect(
            "CLI requires exactly one of --dry-run or --confirm",
            rc == 2 and "exactly one of --dry-run or --confirm" in (stderr_capture.getvalue() or stdout_capture.getvalue()),
            failures,
        )
        with contextlib.redirect_stdout(io.StringIO()) as stdout_capture, contextlib.redirect_stderr(io.StringIO()) as stderr_capture:
            rc = review_cli_main(
                [
                    "--root",
                    str(temp_root),
                    "--product",
                    product_id,
                    "--tool",
                    "open-design",
                    "--dry-run",
                    "--confirm",
                ]
            )
        expect(
            "CLI requires exactly one of --dry-run or --confirm",
            rc == 2 and "exactly one of --dry-run or --confirm" in (stderr_capture.getvalue() or stdout_capture.getvalue()),
            failures,
        )

        missing_run_id, _missing_run_dir = _make_product(temp_root)
        _ = prepare_design_run(temp_root, missing_run_id, "open-design", confirm=True)
        _run_dir, bad_design_run, _bad_design_input, _bad_design_prompt = _prepared_run_paths(
            temp_root, missing_run_id
        )
        bad_design_run.unlink(missing_ok=True)
        _expect_build_fails(
            temp_root,
            missing_run_id,
            failures,
            "fails if design_run.yaml missing",
            DESIGN_RUN_FILENAME,
        )

        missing_input_id, _missing_input_dir = _make_product(temp_root)
        _ = prepare_design_run(temp_root, missing_input_id, "open-design", confirm=True)
        _run_dir, _bad_design_run, bad_design_input, _bad_design_prompt = _prepared_run_paths(
            temp_root, missing_input_id
        )
        bad_design_input.unlink(missing_ok=True)
        _expect_build_fails(
            temp_root,
            missing_input_id,
            failures,
            "fails if design_input.yaml missing",
            DESIGN_INPUT_FILENAME,
        )

        missing_prompt_id, _missing_prompt_dir = _make_product(temp_root)
        _ = prepare_design_run(temp_root, missing_prompt_id, "open-design", confirm=True)
        _run_dir, _bad_design_run, _bad_design_input, bad_design_prompt = _prepared_run_paths(
            temp_root, missing_prompt_id
        )
        bad_design_prompt.unlink(missing_ok=True)
        _expect_build_fails(
            temp_root,
            missing_prompt_id,
            failures,
            "fails if design_prompt.md missing",
            DESIGN_PROMPT_FILENAME,
        )

        bad_status_id, _bad_status_dir = _make_product(temp_root)
        _ = prepare_design_run(temp_root, bad_status_id, "open-design", confirm=True)
        _run_dir, bad_status_run, _bad_design_input, _bad_design_prompt = _prepared_run_paths(
            temp_root, bad_status_id
        )
        run_payload = json.loads(bad_status_run.read_text(encoding="utf-8"))
        run_payload["status"] = "EXECUTED"
        _write_run_payload(bad_status_run, run_payload)
        _expect_build_fails(
            temp_root,
            bad_status_id,
            failures,
            "fails if design_run status is EXECUTED or unknown",
            "status must be PREPARED_NOT_EXECUTED",
        )

        bad_mode_id, _bad_mode_dir = _make_product(temp_root)
        _ = prepare_design_run(temp_root, bad_mode_id, "open-design", confirm=True)
        _run_dir, bad_mode_run, _bad_design_input, _bad_design_prompt = _prepared_run_paths(
            temp_root, bad_mode_id
        )
        run_payload = json.loads(bad_mode_run.read_text(encoding="utf-8"))
        run_payload["execution_mode"] = "EXECUTED"
        _write_run_payload(bad_mode_run, run_payload)
        _expect_build_fails(
            temp_root,
            bad_mode_id,
            failures,
            "fails if execution_mode is not NOT_EXECUTED",
            "execution_mode must be NOT_EXECUTED",
        )

        bad_root_id, _bad_root_dir = _make_product(temp_root)
        _ = prepare_design_run(temp_root, bad_root_id, "open-design", confirm=True)
        _run_dir, bad_root_run, _bad_design_input, _bad_design_prompt = _prepared_run_paths(
            temp_root, bad_root_id
        )
        run_payload = json.loads(bad_root_run.read_text(encoding="utf-8"))
        run_payload["allowed_write_root"] = "../escape/"
        _write_run_payload(bad_root_run, run_payload)
        _expect_build_fails(
            temp_root,
            bad_root_id,
            failures,
            "fails if allowed_write_root escapes sandbox",
            "allowed_write_root",
        )

        bad_forbidden_id, _bad_forbidden_dir = _make_product(temp_root)
        _ = prepare_design_run(temp_root, bad_forbidden_id, "open-design", confirm=True)
        _run_dir, bad_forbidden_run, _bad_design_input, _bad_design_prompt = _prepared_run_paths(
            temp_root, bad_forbidden_id
        )
        run_payload = json.loads(bad_forbidden_run.read_text(encoding="utf-8"))
        run_payload["forbidden_paths"] = []
        _write_run_payload(bad_forbidden_run, run_payload)
        _expect_build_fails(
            temp_root,
            bad_forbidden_id,
            failures,
            "fails if forbidden paths missing",
            "forbidden_paths",
        )

        try:
            _ = build_design_run_review(temp_root, product_id, "unknown")
            failures.append("FAIL: rejects unknown tool - expected failure")
        except ValueError:
            expect("rejects unknown tool", True, failures)

        try:
            _ = build_design_run_review(temp_root, product_id, "../open-design")
            failures.append("FAIL: rejects path traversal tool - expected failure")
        except ValueError:
            expect("rejects path traversal tool", True, failures)

        for script_name in ("product_design_run_review.py", "ws_product_design_run_review.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            disallowed = ("pip install", "npm install", "subprocess.run(", "openai.", "anthropic.", "requests.post(")
            expect(
                "no Open Design execution",
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


def _duplicate_blocked(review_model: dict[str, object]) -> bool:
    try:
        _ = write_design_run_review_artifacts(review_model, confirm=True)
    except FileExistsError:
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
