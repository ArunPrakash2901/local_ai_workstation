#!/usr/bin/env python3
"""Validation for Exchange Lane v0.1 (non-executing)."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANE_ROOT = ROOT / "exchange_lane"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def copy_lane_scaffold(target: Path) -> None:
    for folder in ("contracts", "tools", "examples"):
        shutil.copytree(LANE_ROOT / folder, target / folder)
    for folder in ("packets", "result_packets", "routing", "manifests", "reports"):
        (target / folder).mkdir(parents=True, exist_ok=True)


def remove_tree(path: Path) -> None:
    def reset_permissions(function, target, _exc_info):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)

    shutil.rmtree(path, onexc=reset_permissions)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    exchange_packet = load_module("exchange_packet", LANE_ROOT / "tools" / "exchange_packet.py")
    audit_exchange_lane = load_module("audit_exchange_lane", LANE_ROOT / "tools" / "audit_exchange_lane.py")
    exchange_command = load_module("exchange_command", LANE_ROOT / "tools" / "exchange_command.py")

    assert_true("create" in exchange_packet.build_parser().format_help(), "exchange_packet help should include create")
    assert_true("--root" in audit_exchange_lane.build_parser().format_help(), "audit should expose --root")
    assert_true("status" in exchange_command.build_parser().format_help(), "exchange_command help should include status")

    source_text = (LANE_ROOT / "tools" / "exchange_packet.py").read_text(encoding="utf-8")
    forbidden_terms = ("subprocess", "os.system", "Popen", "git checkout", "git commit", "git push", "git branch")
    for term in forbidden_terms:
        assert_true(term not in source_text, f"exchange_packet.py should not contain execution term: {term}")

    codex_temp = Path.home() / ".codex" / "memories"
    temp_parent = codex_temp if codex_temp.is_dir() else Path(tempfile.gettempdir())
    tmp_root = temp_parent / f"exchange_lane_test_{uuid.uuid4().hex}"
    try:
        tmp_root.mkdir()
        lane_root = tmp_root / "exchange_lane"
        copy_lane_scaffold(lane_root)
        repo_root = lane_root.parent
        runtime_adapters = repo_root / "runtime_lane" / "adapters"
        runtime_adapters.mkdir(parents=True, exist_ok=True)
        write_text(runtime_adapters / "codex_cli_profile.json", json.dumps({"adapter_id": "codex_cli", "launch_mode": "manual_terminal"}))
        safe_source = repo_root / "product_development_lane" / "implementation_plans" / "positive_path_example_implementation_plan.md"
        write_text(safe_source, "# example implementation plan\n")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = exchange_command.main(["--root", str(lane_root), "help"])
        assert_true(rc == 0, "exchange_command help should pass")
        assert_true("packet-list" in output.getvalue(), "exchange_command help should include packet-list")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = exchange_command.main(["--root", str(lane_root), "status"])
        assert_true(rc == 0, "exchange_command status should pass")
        assert_true("packet_count: 0" in output.getvalue(), "status should show zero packets initially")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = exchange_command.main(["--root", str(lane_root), "packet-list"])
        assert_true(rc == 0, "packet-list should pass")
        assert_true("no exchange packets" in output.getvalue(), "packet-list should show empty")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = exchange_command.main(["--root", str(lane_root), "adapter-list"])
        assert_true(rc == 0, "adapter-list should pass")
        assert_true("codex_cli" in output.getvalue(), "adapter-list should include codex_cli")

        ex_packet = json.loads((lane_root / "examples" / "example_product_dev_to_codex_packet.json").read_text(encoding="utf-8"))
        ex_result = json.loads((lane_root / "examples" / "example_codex_result_packet.json").read_text(encoding="utf-8"))
        assert_true(ex_packet["execution_allowed"] is False, "example execution_allowed should be false")
        assert_true(ex_packet["commit_allowed"] is False, "example commit_allowed should be false")
        assert_true(ex_packet["push_allowed"] is False, "example push_allowed should be false")
        assert_true(ex_packet["merge_allowed"] is False, "example merge_allowed should be false")
        assert_true(ex_result["execution_occurred"] is False, "example result execution_occurred should be false")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = exchange_packet.main(
                [
                    "create",
                    "--root",
                    str(lane_root),
                    "--source-artifact",
                    str(safe_source),
                    "--source-lane",
                    "product_development_lane",
                    "--target-adapter",
                    "codex_cli",
                    "--task-type",
                    "implementation_planning",
                    "--objective",
                    "Review implementation plan context only.",
                ]
            )
        assert_true(rc == 0, "create packet should pass")
        packet_files = list((lane_root / "packets").glob("*.json"))
        assert_true(len(packet_files) == 1, "create should write one packet")
        packet = json.loads(packet_files[0].read_text(encoding="utf-8"))
        assert_true(packet["packet_status"] == "DRAFT", "new packet should start DRAFT")
        assert_true(len(packet["source_artifact_checksum"]) == 64, "file source should have sha256")
        assert_true(packet["execution_allowed"] is False, "execution_allowed default false")

        packet_id = packet["packet_id"]
        with contextlib.redirect_stdout(io.StringIO()):
            rc = exchange_packet.main(["mark-ready", "--root", str(lane_root), "--packet-id", packet_id, "--note", "operator ready check"])
        assert_true(rc == 0, "mark-ready should pass")
        packet = json.loads(packet_files[0].read_text(encoding="utf-8"))
        assert_true(packet["packet_status"] == "READY_FOR_REVIEW", "mark-ready should set READY_FOR_REVIEW")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = exchange_packet.main(["block", "--root", str(lane_root), "--packet-id", packet_id, "--reason", "waiting for human review"])
        assert_true(rc == 0, "block should pass")
        packet = json.loads(packet_files[0].read_text(encoding="utf-8"))
        assert_true(packet["packet_status"] == "BLOCKED", "block should set BLOCKED")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = exchange_command.main(["--root", str(lane_root), "packet-status", "--packet-id", packet_id])
        assert_true(rc == 0, "packet-status should pass")
        assert_true('"packet_status": "BLOCKED"' in output.getvalue(), "packet-status should show blocked")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = audit_exchange_lane.main(["--root", str(lane_root)])
        assert_true(rc == 0, "audit should pass after packet creation")

        assert_true("dispatch" not in exchange_command.build_parser().format_help().lower(), "exchange_command should not expose dispatch command")
    finally:
        remove_tree(tmp_root)

    print("Exchange Lane validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
