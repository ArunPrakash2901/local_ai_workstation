#!/usr/bin/env python3
"""Temp-root tests for Exchange dispatch dry-run preview gate."""

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

from exchange_dispatch import (  # noqa: E402
    _load_command_manifest,
    load_exchange_for_dispatch,
    render_dispatch_preview,
    validate_exchange_dispatch_ready,
)
from exchange_registry import create_exchange_packet, exchange_root, save_exchange  # noqa: E402


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


def _run_dispatch_cli(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_exchange_dispatch.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_packet(root: Path, packet: dict[str, object]) -> Path:
    result = save_exchange(packet, root, confirm=True)
    files = result["files_written"]
    exchange_yaml = [Path(p) for p in files if p.endswith("exchange.yaml")][0]
    return exchange_yaml


def main() -> int:
    print("Exchange Dispatch Validation")
    print("============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_exchange_dispatch_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    (temp_root / "registry").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "registry" / "ws_command_safety.yaml", temp_root / "registry" / "ws_command_safety.yaml")

    try:
        manifest = _load_command_manifest(ROOT)

        # 1 dispatch preview passes for valid exchange packet.
        packet = create_exchange_packet(target="codex_cli", task_type="review", summary="dispatch review")
        packet["source_artifacts"] = ["products/demo/prd.md"]
        yaml_path = _write_packet(temp_root, packet)
        loaded = load_exchange_for_dispatch(temp_root, packet["exchange_id"])
        ready = validate_exchange_dispatch_ready(loaded, manifest)
        expect("dispatch preview passes for valid exchange packet", ready["result"] in {"PASS", "WARN"}, failures)

        # 2 dispatch preview rejects missing exchange.
        missing = _run_dispatch_cli(["--exchange", "missing-id", "--dry-run"], temp_root)
        expect("dispatch preview rejects missing exchange", missing.returncode != 0, failures)

        # 3 dispatch preview rejects malformed exchange.yaml.
        bad_packet = create_exchange_packet(target="codex_cli", task_type="review", summary="bad")
        _write_packet(temp_root, bad_packet)
        bad_yaml = exchange_root(temp_root) / bad_packet["exchange_id"] / "exchange.yaml"
        bad_yaml.write_text("not: [valid", encoding="utf-8")
        malformed = _run_dispatch_cli(["--exchange", bad_packet["exchange_id"], "--dry-run"], temp_root)
        expect("dispatch preview rejects malformed exchange.yaml", malformed.returncode != 0, failures)

        # 4 dispatch preview rejects invalid target.
        bad_target = create_exchange_packet(target="codex_cli", task_type="review", summary="bad target")
        bad_target["exchange_id"] = f"bad-target-{uuid4().hex[:8]}"
        _write_packet(temp_root, bad_target)
        p = exchange_root(temp_root) / bad_target["exchange_id"] / "exchange.yaml"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["target"] = "not_a_target"
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        out = _run_dispatch_cli(["--exchange", bad_target["exchange_id"], "--dry-run"], temp_root)
        expect("dispatch preview rejects invalid target", out.returncode != 0, failures)

        # 5 dispatch preview rejects invalid safety_mode.
        bad_mode = create_exchange_packet(target="codex_cli", task_type="review", summary="bad mode")
        bad_mode["exchange_id"] = f"bad-mode-{uuid4().hex[:8]}"
        _write_packet(temp_root, bad_mode)
        p = exchange_root(temp_root) / bad_mode["exchange_id"] / "exchange.yaml"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["safety_mode"] = "NOT_REAL"
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        out = _run_dispatch_cli(["--exchange", bad_mode["exchange_id"], "--dry-run"], temp_root)
        expect("dispatch preview rejects invalid safety_mode", out.returncode != 0, failures)

        # 6 dispatch preview reports unknown allowed_commands as FAIL.
        unknown_cmd = create_exchange_packet(target="codex_cli", task_type="review", summary="unknown command")
        unknown_cmd["exchange_id"] = f"unknown-cmd-{uuid4().hex[:8]}"
        unknown_cmd["source_artifacts"] = ["products/demo/scope_lock.md"]
        unknown_cmd["allowed_commands"] = ["ws definitely-not-real"]
        _write_packet(temp_root, unknown_cmd)
        unknown_loaded = load_exchange_for_dispatch(temp_root, unknown_cmd["exchange_id"])
        unknown_ready = validate_exchange_dispatch_ready(unknown_loaded, manifest)
        expect("dispatch preview reports unknown allowed_commands as FAIL", unknown_ready["result"] == "FAIL", failures)

        # 7 dispatch preview accepts empty allowed_commands if task is REVIEW_ONLY.
        review_only = create_exchange_packet(target="codex_cli", task_type="review", summary="review only")
        review_only["exchange_id"] = f"review-only-{uuid4().hex[:8]}"
        review_only["source_artifacts"] = ["products/demo/prd.md"]
        review_only["allowed_commands"] = []
        _write_packet(temp_root, review_only)
        out = _run_dispatch_cli(["--exchange", review_only["exchange_id"], "--dry-run"], temp_root)
        expect("dispatch preview accepts empty allowed_commands if task is REVIEW_ONLY", "dispatch_readiness: FAIL" not in (out.stdout or ""), failures)

        # 8 dispatch preview requires forbidden_actions field.
        no_forbidden = create_exchange_packet(target="codex_cli", task_type="review", summary="no forbidden")
        no_forbidden["exchange_id"] = f"no-forbidden-{uuid4().hex[:8]}"
        no_forbidden["source_artifacts"] = ["products/demo/prd.md"]
        _write_packet(temp_root, no_forbidden)
        p = exchange_root(temp_root) / no_forbidden["exchange_id"] / "exchange.yaml"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["forbidden_actions"] = []
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        no_forbidden_loaded = load_exchange_for_dispatch(temp_root, no_forbidden["exchange_id"])
        no_forbidden_ready = validate_exchange_dispatch_ready(no_forbidden_loaded, manifest)
        expect("dispatch preview requires forbidden_actions field", no_forbidden_ready["result"] == "FAIL", failures)

        # 9 dispatch preview requires expected_outputs field.
        no_expected = create_exchange_packet(target="codex_cli", task_type="review", summary="no expected")
        no_expected["exchange_id"] = f"no-expected-{uuid4().hex[:8]}"
        no_expected["source_artifacts"] = ["products/demo/prd.md"]
        _write_packet(temp_root, no_expected)
        p = exchange_root(temp_root) / no_expected["exchange_id"] / "exchange.yaml"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["expected_outputs"] = []
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        no_expected_loaded = load_exchange_for_dispatch(temp_root, no_expected["exchange_id"])
        no_expected_ready = validate_exchange_dispatch_ready(no_expected_loaded, manifest)
        expect("dispatch preview requires expected_outputs field", no_expected_ready["result"] == "FAIL", failures)

        # 10 source_artifacts summary present.
        valid_cli = _run_dispatch_cli(["--exchange", packet["exchange_id"], "--dry-run"], temp_root)
        expect("dispatch preview includes source_artifacts summary", "### Source Artifacts" in (valid_cli.stdout or ""), failures)

        # 11 DRY RUN notice.
        expect("dispatch preview includes DRY RUN / no execution notice", "DRY RUN - no execution and no files written." in (valid_cli.stdout or ""), failures)

        # Snapshot files before extra checks.
        before = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())

        # 12 writes no files.
        _ = _run_dispatch_cli(["--exchange", packet["exchange_id"], "--dry-run"], temp_root)
        after = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("dispatch preview writes no files", before == after, failures)

        # 13 does not update exchange.yaml status.
        current = json.loads(yaml_path.read_text(encoding="utf-8"))
        expect("dispatch preview does not update exchange.yaml status", current.get("status") == packet["status"], failures)

        # 14-17 no result files created.
        packet_dir = exchange_root(temp_root) / packet["exchange_id"]
        expect("dispatch preview does not create raw_output.md", not (packet_dir / "raw_output.md").exists(), failures)
        expect("dispatch preview does not create parsed_result.json", not (packet_dir / "parsed_result.json").exists(), failures)
        expect("dispatch preview does not create validation.md", not (packet_dir / "validation.md").exists(), failures)
        expect("dispatch preview does not create operator_report.md", not (packet_dir / "operator_report.md").exists(), failures)

        # 18 no model/provider/agent usage markers.
        source = (SCRIPTS_DIR / "exchange_dispatch.py").read_text(encoding="utf-8").lower()
        expect(
            "dispatch preview does not call models/providers/agents",
            all(token not in source for token in ("subprocess", "requests.", "ollama_call", "browsermcp", "openai", "gemini")),
            failures,
        )

        # 19 CLI requires --dry-run.
        missing_mode = _run_dispatch_cli(["--exchange", packet["exchange_id"]], temp_root)
        expect("CLI helper requires --dry-run", missing_mode.returncode != 0 and "Use --dry-run" in (missing_mode.stdout or ""), failures)

        # 20 confirm requires explicit codex target in this slice.
        confirm_missing_target = _run_dispatch_cli(["--exchange", packet["exchange_id"], "--confirm"], temp_root)
        expect(
            "dispatch confirm requires target",
            confirm_missing_target.returncode != 0 and "--target <target> is required" in (confirm_missing_target.stderr or ""),
            failures,
        )
        confirm_bad_target = _run_dispatch_cli(["--exchange", packet["exchange_id"], "--target", "gemini_cli", "--confirm"], temp_root)
        expect(
            "dispatch confirm rejects unsupported target",
            confirm_bad_target.returncode != 0 and "only --target codex_cli is supported" in (confirm_bad_target.stderr or ""),
            failures,
        )

        # Render function sanity.
        expect("render_dispatch_preview returns title", "Exchange Dispatch Preview" in render_dispatch_preview(loaded, ready), failures)

    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    print("")
    if failures:
        print("Result: FAIL")
        for item in failures:
            print(item)
        return 1
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
