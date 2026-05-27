#!/usr/bin/env python3
"""Temp-root tests for Product Lane design render dry-run."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
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
import product_design_render_runtime as render_runtime  # noqa: E402
from product_design_run import prepare_design_run  # noqa: E402
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


def _create_open_design_checkout(root: Path, *, include_daemon_cli: bool = True) -> Path:
    checkout = root / "open_design_source"
    checkout.mkdir(parents=True, exist_ok=True)
    (checkout / "package.json").write_text("{}\n", encoding="utf-8")
    (checkout / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (checkout / "node_modules").mkdir(parents=True, exist_ok=True)
    if include_daemon_cli:
        daemon_cli = checkout / "apps" / "daemon" / "dist" / "cli.js"
        daemon_cli.parent.mkdir(parents=True, exist_ok=True)
        daemon_cli.write_text("console.log('daemon');\n", encoding="utf-8")
    return checkout


def _fake_runtime_probe(
    source_checkout: Path,
    *,
    readiness: str = "RENDER_READY",
    daemon_cli_present: bool = True,
    node_path: str = "/usr/bin/node",
) -> dict[str, object]:
    return {
        "readiness_classification": readiness,
        "detected_command_paths": {
            "open-design": None,
            "od": None,
            "node": node_path,
            "pnpm": "/usr/bin/pnpm",
            "npm": "/usr/bin/npm",
        },
        "source_checkout_detection": {
            "path": source_checkout.as_posix(),
            "exists": True,
            "is_valid": True,
            "required_files": {
                "package.json": True,
                "pnpm-lock.yaml": True,
                "node_modules/": True,
                "apps/daemon/dist/cli.js": daemon_cli_present,
            },
        },
    }


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

        with contextlib.redirect_stderr(io.StringIO()) as stderr_capture:
            try:
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
            except SystemExit as exc:
                rc = exc.code
        expect(
            "CLI requires exactly one of --dry-run or --confirm",
            rc == 2 and "one of the arguments --dry-run --confirm is required" in stderr_capture.getvalue(),
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

        # Guarded render dry-run plan details.
        planned_product_id, _planned_dir = _make_product(temp_root, product_type="website")
        _ = prepare_design_run(temp_root, planned_product_id, "open-design", confirm=True)
        source_checkout = _create_open_design_checkout(temp_root, include_daemon_cli=True)
        original_probe = render_runtime.probe_design_runtime
        try:
            render_runtime.probe_design_runtime = lambda *_args, **_kwargs: _fake_runtime_probe(  # type: ignore[assignment]
                source_checkout,
                readiness="RENDER_READY",
                daemon_cli_present=True,
            )
            plan = render_runtime.build_open_design_render_plan(
                temp_root,
                planned_product_id,
                "open-design",
                env={"OPEN_DESIGN_RENDER_PROVIDER_MODE": "local_cli"},
            )
            plan_rendered = render_runtime.render_open_design_render_plan(plan)
            expect("dry-run reports command plan/capture paths", "run_events.ndjson" in plan_rendered and "command_manifest.json" in plan_rendered, failures)
            expect("dry-run writes nothing and executes nothing", plan["execution"] == "no" and plan["writes"] == "none" and plan["provider_call"] == "no", failures)
        finally:
            render_runtime.probe_design_runtime = original_probe  # type: ignore[assignment]

        # Confirm refuses if daemon CLI missing.
        no_daemon_product_id, _no_daemon_dir = _make_product(temp_root, product_type="website")
        _ = prepare_design_run(temp_root, no_daemon_product_id, "open-design", confirm=True)
        no_daemon_checkout = _create_open_design_checkout(temp_root, include_daemon_cli=False)
        original_probe = render_runtime.probe_design_runtime
        try:
            render_runtime.probe_design_runtime = lambda *_args, **_kwargs: _fake_runtime_probe(  # type: ignore[assignment]
                no_daemon_checkout,
                readiness="RUNTIME_CANDIDATE_FOUND",
                daemon_cli_present=False,
            )
            try:
                _ = render_runtime.execute_open_design_render_confirm(
                    temp_root,
                    no_daemon_product_id,
                    "open-design",
                    env={"OPEN_DESIGN_RENDER_PROVIDER_MODE": "local_cli"},
                )
                failures.append("FAIL: confirm refuses if daemon CLI missing - expected exception")
            except ValueError as exc:
                expect("confirm refuses if daemon CLI missing", "DAEMON_CLI_MISSING" in str(exc), failures, str(exc))
        finally:
            render_runtime.probe_design_runtime = original_probe  # type: ignore[assignment]

        # Confirm refuses if allowed write root escapes run sandbox.
        escape_root_product_id, escape_root_dir = _make_product(temp_root, product_type="website")
        _ = prepare_design_run(temp_root, escape_root_product_id, "open-design", confirm=True)
        escape_checkout = _create_open_design_checkout(temp_root, include_daemon_cli=True)
        run_yaml = (
            escape_root_dir
            / "design_runs"
            / "open_design"
            / "open-design-render-v1"
            / "design_run.yaml"
        )
        run_payload = json.loads(run_yaml.read_text(encoding="utf-8"))
        run_payload["allowed_write_root"] = "../escape_root/"
        _write_record(run_yaml, run_payload)
        original_probe = render_runtime.probe_design_runtime
        try:
            render_runtime.probe_design_runtime = lambda *_args, **_kwargs: _fake_runtime_probe(  # type: ignore[assignment]
                escape_checkout,
                readiness="RENDER_READY",
                daemon_cli_present=True,
            )
            try:
                _ = render_runtime.execute_open_design_render_confirm(
                    temp_root,
                    escape_root_product_id,
                    "open-design",
                    env={"OPEN_DESIGN_RENDER_PROVIDER_MODE": "local_cli"},
                )
                failures.append("FAIL: confirm refuses if OD_DATA_DIR escapes allowed root - expected exception")
            except ValueError as exc:
                expect(
                    "confirm refuses if OD_DATA_DIR escapes allowed root",
                    "path escapes expected base" in str(exc),
                    failures,
                    str(exc),
                )
        finally:
            render_runtime.probe_design_runtime = original_probe  # type: ignore[assignment]

        # Confirm refuses if capture/output paths escape allowed root.
        capture_escape_product_id, _capture_escape_dir = _make_product(temp_root, product_type="website")
        _ = prepare_design_run(temp_root, capture_escape_product_id, "open-design", confirm=True)
        capture_checkout = _create_open_design_checkout(temp_root, include_daemon_cli=True)
        original_probe = render_runtime.probe_design_runtime
        original_plan = render_runtime.build_open_design_render_plan
        try:
            render_runtime.probe_design_runtime = lambda *_args, **_kwargs: _fake_runtime_probe(  # type: ignore[assignment]
                capture_checkout,
                readiness="RENDER_READY",
                daemon_cli_present=True,
            )
            safe_plan = original_plan(
                temp_root,
                capture_escape_product_id,
                "open-design",
                env={"OPEN_DESIGN_RENDER_PROVIDER_MODE": "local_cli"},
            )
            bad_plan = dict(safe_plan)
            bad_capture = dict(safe_plan["capture_paths"])
            bad_capture["stdout.txt"] = "../escape/stdout.txt"
            bad_plan["capture_paths"] = bad_capture
            render_runtime.build_open_design_render_plan = lambda *_args, **_kwargs: bad_plan  # type: ignore[assignment]
            try:
                _ = render_runtime.execute_open_design_render_confirm(
                    temp_root,
                    capture_escape_product_id,
                    "open-design",
                    env={"OPEN_DESIGN_RENDER_PROVIDER_MODE": "local_cli"},
                )
                failures.append("FAIL: confirm refuses if output/capture path escapes allowed root - expected exception")
            except ValueError as exc:
                expect(
                    "confirm refuses if output/capture path escapes allowed root",
                    "path escapes expected base" in str(exc),
                    failures,
                    str(exc),
                )
        finally:
            render_runtime.probe_design_runtime = original_probe  # type: ignore[assignment]
            render_runtime.build_open_design_render_plan = original_plan  # type: ignore[assignment]

        # Confirm executes mocked daemon lifecycle using explicit argv and shell=False.
        confirm_product_id, _confirm_dir = _make_product(temp_root, product_type="website")
        _ = prepare_design_run(temp_root, confirm_product_id, "open-design", confirm=True)
        confirm_checkout = _create_open_design_checkout(temp_root, include_daemon_cli=True)
        original_probe = render_runtime.probe_design_runtime
        original_popen = render_runtime.subprocess.Popen
        original_run = render_runtime.subprocess.run
        original_choose_port = render_runtime._choose_free_port
        popen_calls: list[dict[str, object]] = []
        run_calls: list[dict[str, object]] = []

        class _FakePopen:
            def __init__(
                self,
                cmd: list[str],
                *,
                cwd: str | None = None,
                env: dict[str, str] | None = None,
                stdout=None,
                stderr=None,
                text: bool | None = None,
                shell: bool | None = None,
            ) -> None:
                popen_calls.append(
                    {"cmd": list(cmd), "cwd": cwd, "shell": shell, "env_has_od_data_dir": bool(env and env.get("OD_DATA_DIR"))}
                )
                self._poll: int | None = None

            def poll(self) -> int | None:
                return self._poll

            def terminate(self) -> None:
                self._poll = 0

            def wait(self, timeout: int | None = None) -> int:
                _ = timeout
                self._poll = 0
                return 0

            def kill(self) -> None:
                self._poll = -9

        def _fake_run(
            cmd: list[str],
            *,
            cwd: str | None = None,
            env: dict[str, str] | None = None,
            capture_output: bool = False,
            text: bool = False,
            timeout: int | None = None,
            shell: bool | None = None,
        ) -> subprocess.CompletedProcess[str]:
            run_calls.append(
                {"cmd": list(cmd), "cwd": cwd, "shell": shell, "timeout": timeout, "env_has_od_data_dir": bool(env and env.get("OD_DATA_DIR"))}
            )
            _ = (capture_output, text)
            if len(cmd) >= 3 and cmd[2] == "status":
                return subprocess.CompletedProcess(cmd, 0, stdout='{"status":"ok"}\n', stderr="")
            if len(cmd) >= 4 and cmd[2] == "project" and cmd[3] == "create":
                return subprocess.CompletedProcess(cmd, 0, stdout='{"project":{"id":"proj_1"}}\n', stderr="")
            if len(cmd) >= 4 and cmd[2] == "run" and cmd[3] == "start":
                return subprocess.CompletedProcess(cmd, 0, stdout='{"event":"run_started"}\n{"event":"run_completed"}\n', stderr="")
            if len(cmd) >= 4 and cmd[2] == "files" and cmd[3] == "list":
                return subprocess.CompletedProcess(cmd, 0, stdout='{"files":[{"name":"prototype/index.html","size":123}]}\n', stderr="")
            if len(cmd) >= 4 and cmd[2] == "daemon" and cmd[3] == "stop":
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        try:
            render_runtime.probe_design_runtime = lambda *_args, **_kwargs: _fake_runtime_probe(  # type: ignore[assignment]
                confirm_checkout,
                readiness="RENDER_READY",
                daemon_cli_present=True,
            )
            render_runtime.subprocess.Popen = _FakePopen  # type: ignore[assignment]
            render_runtime.subprocess.run = _fake_run  # type: ignore[assignment]
            render_runtime._choose_free_port = lambda: 18555  # type: ignore[assignment]
            confirm_result = render_runtime.execute_open_design_render_confirm(
                temp_root,
                confirm_product_id,
                "open-design",
                env={"OPEN_DESIGN_RENDER_PROVIDER_MODE": "local_cli"},
            )
            expect("confirm starts mocked daemon with explicit argv list, no shell=True", all(call["shell"] is False for call in popen_calls + run_calls), failures, detail=str(popen_calls + run_calls))
            expect("confirm captures mocked NDJSON events", bool(confirm_result["capture_paths"]["run_events.ndjson"]), failures)
            run_events_path = temp_root / confirm_result["capture_paths"]["run_events.ndjson"]
            expect("confirm writes run events file", run_events_path.is_file() and "run_started" in run_events_path.read_text(encoding="utf-8"), failures)
            render_manifest_path = temp_root / confirm_result["capture_paths"]["render_manifest.json"]
            output_file_list_path = temp_root / confirm_result["capture_paths"]["output_file_list.json"]
            expect("confirm records render manifest and output file list", render_manifest_path.is_file() and output_file_list_path.is_file(), failures)
            expect("confirm preserves no app/source mutation", confirm_result["source_mutation_detected"] is False, failures)
        finally:
            render_runtime.probe_design_runtime = original_probe  # type: ignore[assignment]
            render_runtime.subprocess.Popen = original_popen  # type: ignore[assignment]
            render_runtime.subprocess.run = original_run  # type: ignore[assignment]
            render_runtime._choose_free_port = original_choose_port  # type: ignore[assignment]

        # Confirm handles UI blocker without inventing answers.
        ui_blocker_product_id, _ui_blocker_dir = _make_product(temp_root, product_type="website")
        _ = prepare_design_run(temp_root, ui_blocker_product_id, "open-design", confirm=True)
        ui_checkout = _create_open_design_checkout(temp_root, include_daemon_cli=True)
        original_probe = render_runtime.probe_design_runtime
        original_popen = render_runtime.subprocess.Popen
        original_run = render_runtime.subprocess.run
        original_choose_port = render_runtime._choose_free_port

        class _UIFakePopen(_FakePopen):
            pass

        def _ui_fake_run(
            cmd: list[str],
            *,
            cwd: str | None = None,
            env: dict[str, str] | None = None,
            capture_output: bool = False,
            text: bool = False,
            timeout: int | None = None,
            shell: bool | None = None,
        ) -> subprocess.CompletedProcess[str]:
            _ = (cwd, env, capture_output, text, timeout, shell)
            if len(cmd) >= 3 and cmd[2] == "status":
                return subprocess.CompletedProcess(cmd, 0, stdout='{"status":"ok"}\n', stderr="")
            if len(cmd) >= 4 and cmd[2] == "project" and cmd[3] == "create":
                return subprocess.CompletedProcess(cmd, 0, stdout='{"project":{"id":"proj_ui"}}\n', stderr="")
            if len(cmd) >= 4 and cmd[2] == "run" and cmd[3] == "start":
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout='{"event":"genui_surface_request","type":"question-form"}\n',
                    stderr="",
                )
            if len(cmd) >= 4 and cmd[2] == "files" and cmd[3] == "list":
                return subprocess.CompletedProcess(cmd, 0, stdout='{"files":[]}\n', stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        try:
            render_runtime.probe_design_runtime = lambda *_args, **_kwargs: _fake_runtime_probe(  # type: ignore[assignment]
                ui_checkout,
                readiness="RENDER_READY",
                daemon_cli_present=True,
            )
            render_runtime.subprocess.Popen = _UIFakePopen  # type: ignore[assignment]
            render_runtime.subprocess.run = _ui_fake_run  # type: ignore[assignment]
            render_runtime._choose_free_port = lambda: 19555  # type: ignore[assignment]
            ui_result = render_runtime.execute_open_design_render_confirm(
                temp_root,
                ui_blocker_product_id,
                "open-design",
                env={"OPEN_DESIGN_RENDER_PROVIDER_MODE": "local_cli"},
            )
            expect(
                "confirm handles UI/GenUI blocker without inventing answers",
                ui_result["status"] == "BLOCKED_NEEDS_OPERATOR_UI_RESPONSE"
                and "GENUI_SURFACE_REQUEST" in ui_result["ui_blockers"],
                failures,
                detail=str(ui_result),
            )
        finally:
            render_runtime.probe_design_runtime = original_probe  # type: ignore[assignment]
            render_runtime.subprocess.Popen = original_popen  # type: ignore[assignment]
            render_runtime.subprocess.run = original_run  # type: ignore[assignment]
            render_runtime._choose_free_port = original_choose_port  # type: ignore[assignment]

        for script_name in ("product_design_adapter.py", "ws_product_design_render.py", "product_design_render_runtime.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            disallowed = ("import requests", "pip install", "npm install", "openai.", "anthropic.")
            expect(
                "Open Design is not executed or installed",
                all(token not in source for token in disallowed),
                failures,
                script_name,
            )
        runtime_source = (SCRIPTS_DIR / "product_design_render_runtime.py").read_text(encoding="utf-8")
        expect(
            "guarded render runtime does not use shell=True",
            "shell=True" not in runtime_source,
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
