#!/usr/bin/env python3
"""Smoke tests for Discovery Lane command bridge helpers and examples.

These tests use Discovery Lane example artifacts only. They do not execute
worker prompts, create git branches, commit, push, or merge.
"""

from __future__ import annotations

import importlib.util
import json
import contextlib
import io
import os
import shutil
import stat
import sys
import tempfile
import uuid
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_ROOT = ROOT / "discovery_lane"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load module spec: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def remove_tree(path: Path) -> None:
    def reset_permissions(function, target, _exc_info):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)

    shutil.rmtree(path, onexc=reset_permissions)


def main() -> int:
    codex_temp = Path.home() / ".codex" / "memories"
    temp_parent = codex_temp if codex_temp.is_dir() else Path(tempfile.gettempdir())
    tmp_root = temp_parent / f"discovery_lane_test_{uuid.uuid4().hex}"
    try:
        tmp_root.mkdir()
        discovery_root = tmp_root / "discovery_lane"
        shutil.copytree(DISCOVERY_ROOT, discovery_root)

        ingest = load_module("ingest_research_reports", discovery_root / "tools" / "ingest_research_reports.py")
        intake = load_module("intake_research_set", discovery_root / "tools" / "intake_research_set.py")
        ingest_set = load_module("ingest_research_set", discovery_root / "tools" / "ingest_research_set.py")
        approve_phase_packet = load_module("approve_phase_packet", discovery_root / "tools" / "approve_phase_packet.py")
        approve_set = load_module("approve_research_set", discovery_root / "tools" / "approve_research_set.py")
        queue_builder = load_module("build_execution_queue", discovery_root / "tools" / "build_execution_queue.py")
        audit_tool = load_module("audit_discovery_lane", discovery_root / "tools" / "audit_discovery_lane.py")
        dispatcher = load_module("discovery_command", discovery_root / "tools" / "discovery_command.py")

        slash_spec = discovery_root / "slash_commands" / "discovery_commands.json"
        spec_data = json.loads(slash_spec.read_text(encoding="utf-8"))
        assert_true(spec_data["current_executable_interface"] == "ws discovery <command>", "slash spec bridge mismatch")

        manifests = ingest.load_manifests(discovery_root)
        assert_true(isinstance(manifests, list), "manifest loading should return a list")
        assert_true("intake-set" in dispatcher.build_parser().format_help(), "dispatcher should expose intake-set")
        assert_true("ingest-set" in dispatcher.build_parser().format_help(), "dispatcher should expose ingest-set")
        assert_true("approve-set" in dispatcher.build_parser().format_help(), "dispatcher should expose approve-set")
        assert_true("handoff-list" in dispatcher.build_parser().format_help(), "dispatcher should expose handoff-list")
        assert_true("queue-plan" in dispatcher.build_parser().format_help(), "dispatcher should expose queue-plan")
        assert_true("--input" in intake.build_parser().format_help(), "intake parser should expose --input")
        assert_true("--set-id" in ingest_set.build_parser().format_help(), "ingest-set parser should expose --set-id")
        assert_true("--write-report" in approve_set.build_parser().format_help(), "approve-set parser should expose --write-report")
        assert_true("--write-report" in queue_builder.build_parser().format_help(), "queue-plan parser should expose --write-report")

        audit, _counts = audit_tool.audit_discovery_lane(discovery_root)
        assert_true(not audit.errors, "Discovery Lane audit should pass: " + "; ".join(audit.errors))

        example_state = discovery_root / "examples" / "generated"
        if example_state.exists():
            example_audit, _example_counts = audit_tool.audit_discovery_lane(discovery_root, example_state)
            assert_true(
                not example_audit.errors,
                "example Discovery Lane audit should pass: " + "; ".join(example_audit.errors),
            )
            with contextlib.redirect_stdout(io.StringIO()):
                rc = dispatcher.main(["status", "--output", str(example_state)])
            assert_true(rc == 0, "dispatcher status failed for example state")

        manifest = intake.build_research_set_manifest(
            discovery_root / "examples",
            discovery_root / "examples" / "generated",
            "example_product",
        )
        assert_true(manifest["report_count"] >= 1, "intake manifest should count example reports")
        assert_true(manifest["reports"][0]["sha256"], "intake manifest should record report checksum")
        assert_true(manifest["set_status"] in {"READY_FOR_INGEST", "NEEDS_HUMAN_DECISION", "NOT_READY"}, "invalid set status")
        intake_report = intake.render_intake_report(manifest)
        assert_true("Research Set Intake Report" in intake_report, "intake report should render")
        assert_true("Files Safe To Open In VS Code" in intake_report, "intake report should include review paths")

        duplicate_summary = intake.summarize_reports(
            [
                {"filename": "phase_01_a.md", "detected_phase_id": "phase_01", "detected_phase_title": "A"},
                {"filename": "phase_01_b.md", "detected_phase_id": "phase_01", "detected_phase_title": "B"},
            ]
        )
        assert_true(duplicate_summary["duplicate_phase_ids"] == ["phase_01"], "duplicate phase ids should be surfaced")

        changed_sources = ingest_set.verify_sources(
            discovery_root,
            {
                "reports": [
                    {
                        "source_path": "examples/phase_01_foundation_research.md",
                        "filename": "phase_01_foundation_research.md",
                        "sha256": "0" * 64,
                    }
                ]
            },
        )
        assert_true(changed_sources[4] == "FAILED_SOURCE_CHANGED", "checksum mismatch should block ingest")

        existing_ingest = discovery_root / "research_set_ingests" / "examples_ingest_manifest.json"
        if existing_ingest.exists():
            ingest_data = json.loads(existing_ingest.read_text(encoding="utf-8"))
            assert_true(ingest_data["ingest_status"] == "INGESTED", "example ingest should be INGESTED")
            for key in ("generated_phase_packets", "generated_worker_prompts", "generated_manifests"):
                assert_true(ingest_data[key], f"example ingest should record {key}")
                for generated_path in ingest_data[key]:
                    assert_true((discovery_root / generated_path).exists(), f"generated path missing: {generated_path}")
            approval_json_before = sorted((discovery_root / "approval_records").glob("*.json"))
            handoffs_before = sorted((discovery_root / "execution_handoffs").glob("*"))
            branch_plans_before = sorted((discovery_root / "branch_plans").glob("*.json"))
            review_plan = approve_set.build_approval_review_plan(discovery_root, "examples")
            assert_true(review_plan["counts"]["total_packets"] >= 1, "approval review should inspect packets")
            assert_true(review_plan["counts"]["ready_for_approval"] >= 1, "example packet should be ready for approval")
            assert_true("advisory only" in approve_set.render_review_plan(review_plan), "review report should be advisory")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = dispatcher.main(["approve-set", "--root", str(discovery_root), "examples", "--dry-run"])
            assert_true(rc == 0, "dispatcher approve-set dry-run failed")
            assert_true(
                approval_json_before == sorted((discovery_root / "approval_records").glob("*.json")),
                "approve-set dry-run must not create approval JSON",
            )
            assert_true(
                handoffs_before == sorted((discovery_root / "execution_handoffs").glob("*")),
                "approve-set dry-run must not create handoff bundles",
            )
            assert_true(
                branch_plans_before == sorted((discovery_root / "branch_plans").glob("*.json")),
                "approve-set dry-run must not create branch plans",
            )
            queue, queue_paths = queue_builder.build_execution_queue(discovery_root, "examples", write_report=True)
            assert_true(queue_paths["queue_manifest"].exists(), "queue manifest should be created")
            assert_true(queue_paths["queue_report"].exists(), "queue report should be created")
            assert_true(
                queue["queue_status"] in {"EMPTY_NO_APPROVED_HANDOFFS", "READY_FOR_EXECUTION_LANE"},
                "example queue should be empty or ready depending on approved fixtures",
            )
            if queue["queue_status"] == "EMPTY_NO_APPROVED_HANDOFFS":
                assert_true(queue["excluded_phases"], "empty queue should explain excluded unapproved packets")
            if queue["queued_phases"]:
                first = queue["queued_phases"][0]
                assert_true(first["execution_status"] == "NOT_STARTED", "queued phase execution status should be NOT_STARTED")
                assert_true(first["branch_status"] == "PLANNED_NOT_CREATED", "queued phase branch should be planned only")
                assert_true(first["handoff_bundle"], "queued phase should reference a handoff bundle")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = dispatcher.main(["handoff-list", "--output", str(discovery_root)])
            assert_true(rc == 0, "dispatcher handoff-list failed")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = dispatcher.main(["queue-plan", "--root", str(discovery_root), "examples"])
            assert_true(rc == 0, "dispatcher queue-plan failed")
            post_queue_audit, _post_queue_counts = audit_tool.audit_discovery_lane(discovery_root)
            assert_true(not post_queue_audit.errors, "Discovery Lane audit should pass after queue plan: " + "; ".join(post_queue_audit.errors))

        positive_set_id = "positive_path_example"
        positive_input = discovery_root / "examples" / "positive_path"
        positive_source = positive_input / "positive_phase_01_foundation_research.md"
        assert_true(positive_source.exists(), "positive-path fixture source report should exist")

        positive_intake, _positive_intake_paths = intake.intake_research_set(positive_input, discovery_root, positive_set_id)
        assert_true(positive_intake["set_status"] == "READY_FOR_INGEST", "positive-path intake should be ready")

        positive_ingest, _positive_ingest_paths = ingest_set.ingest_research_set(
            discovery_root,
            positive_set_id,
            overwrite=True,
        )
        assert_true(positive_ingest["ingest_status"] == "INGESTED", "positive-path ingest should succeed")
        assert_true(len(positive_ingest["generated_phase_packets"]) == 1, "positive path should generate one phase packet")

        positive_review_plan, positive_review_report = approve_set.approve_research_set(
            discovery_root,
            positive_set_id,
            dry_run=True,
            write_report=True,
        )
        assert_true(positive_review_plan["counts"]["total_packets"] == 1, "positive approval review should inspect one packet")
        assert_true(positive_review_report.exists(), "positive approval review report should exist")

        positive_packet = discovery_root / positive_ingest["generated_phase_packets"][0]
        packet = approve_phase_packet.load_packet(positive_packet, discovery_root)
        assert_true(packet["current_status"] == "READY_FOR_HUMAN_REVIEW", "positive packet should be ready for human review")
        phase_id = str(packet["phase_id"])
        phase_title = str(packet["phase_title"])
        slug = approve_phase_packet.json_slug(phase_id, phase_title)
        folder_slug = approve_phase_packet.packet_slug(phase_id, phase_title)
        approval_path = discovery_root / "approval_records" / f"{slug}_approval_record.json"
        handoff_dir = discovery_root / "execution_handoffs" / folder_slug
        branch_plan_path = discovery_root / "branch_plans" / f"{slug}_branch_plan.json"

        if not approval_path.exists():
            result = approve_phase_packet.approve_packet(
                Namespace(
                    packet=str(positive_packet),
                    output=str(discovery_root),
                    reject=False,
                    override=False,
                    reason="Approved for positive-path Discovery Lane fixture validation.",
                    allow_commit=False,
                    allow_push=False,
                    allow_merge=False,
                    branch_name="work/discovery/positive-phase-01-foundation-fixture",
                )
            )
            assert_true(result["approval_status"] == "APPROVED_FOR_EXECUTION_HANDOFF", "positive approval should succeed")

        assert_true(approval_path.exists(), "positive approval record should exist")
        assert_true(handoff_dir.exists(), "positive handoff bundle should exist")
        assert_true(branch_plan_path.exists(), "positive branch plan should exist")

        branch_plan = json.loads(branch_plan_path.read_text(encoding="utf-8"))
        assert_true(branch_plan["branch_status"] == "PLANNED_NOT_CREATED", "positive branch must remain planned only")
        assert_true(branch_plan["commit_allowed"] is False, "positive fixture should not allow commit by default")
        assert_true(branch_plan["push_allowed"] is False, "positive fixture should not allow push by default")
        assert_true(branch_plan["merge_allowed"] is False, "positive fixture should not allow merge by default")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = dispatcher.main(["handoff-list", "--output", str(discovery_root)])
        assert_true(rc == 0, "dispatcher handoff-list should work after positive approval")

        positive_queue, positive_queue_paths = queue_builder.build_execution_queue(
            discovery_root,
            positive_set_id,
            write_report=True,
        )
        assert_true(positive_queue_paths["queue_manifest"].exists(), "positive queue manifest should exist")
        assert_true(positive_queue_paths["queue_report"].exists(), "positive queue report should exist")
        assert_true(
            positive_queue["queue_status"] == "READY_FOR_EXECUTION_LANE",
            f"positive queue should be ready, got {positive_queue['queue_status']}",
        )
        assert_true(positive_queue["queued_phase_count"] == 1, "positive queue should include one queued phase")
        positive_phase = positive_queue["queued_phases"][0]
        assert_true(positive_phase["execution_status"] == "NOT_STARTED", "positive phase execution must not start")
        assert_true(positive_phase["branch_status"] == "PLANNED_NOT_CREATED", "positive queue must not create branches")
        assert_true(positive_phase["handoff_bundle"], "positive queue should reference handoff bundle")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = dispatcher.main(["queue-plan", "--root", str(discovery_root), positive_set_id, "--write-report"])
        assert_true(rc == 0, "dispatcher queue-plan should work for positive fixture")

        positive_audit, _positive_counts = audit_tool.audit_discovery_lane(discovery_root)
        assert_true(not positive_audit.errors, "Discovery Lane audit should pass after positive path: " + "; ".join(positive_audit.errors))
    finally:
        if tmp_root.exists():
            remove_tree(tmp_root)

    print("Discovery Lane smoke test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
