#!/usr/bin/env python3
"""Validation for Product Development Lane non-executing adapter artifacts."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANE_ROOT = ROOT / "product_development_lane"
DISCOVERY_QUEUE = ROOT / "discovery_lane" / "execution_queues" / "positive_path_example_execution_queue.json"
EXAMPLES_QUEUE = ROOT / "discovery_lane" / "execution_queues" / "examples_execution_queue.json"


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


def main() -> int:
    build_tool = load_module("build_product_packet", LANE_ROOT / "tools" / "build_product_packet.py")
    audit_tool = load_module("audit_product_development_lane", LANE_ROOT / "tools" / "audit_product_development_lane.py")
    command_tool = load_module("product_dev_command", LANE_ROOT / "tools" / "product_dev_command.py")

    assert_true("--queue" in build_tool.build_parser().format_help(), "build parser should expose --queue")
    assert_true("--root" in audit_tool.build_parser().format_help(), "audit parser should expose --root")
    assert_true("build-packet" in command_tool.build_parser().format_help(), "command bridge should expose build-packet")
    assert_true(DISCOVERY_QUEUE.exists(), "positive Discovery queue should exist")

    if EXAMPLES_QUEUE.exists():
        example_queue = json.loads(EXAMPLES_QUEUE.read_text(encoding="utf-8"))
        if example_queue.get("queue_status") != "READY_FOR_EXECUTION_LANE":
            try:
                build_tool.build_product_packet(EXAMPLES_QUEUE, LANE_ROOT)
            except build_tool.ProductDevelopmentError as exc:
                assert_true("READY_FOR_EXECUTION_LANE" in str(exc), "non-ready queue should be refused")
            else:
                raise AssertionError("non-ready queue was not refused")

    manifest, paths = build_tool.build_product_packet(DISCOVERY_QUEUE, LANE_ROOT)
    assert_true(manifest["set_id"] == "positive_path_example", "set_id should come from queue")
    assert_true(manifest["source_queue_status"] == "READY_FOR_EXECUTION_LANE", "source queue status should be ready")
    assert_true(manifest["worker_prompts_executed"] is False, "worker prompts must not execute")
    assert_true(manifest["branches_created"] is False, "branches must not be created")
    assert_true(manifest["git_actions_performed"] is False, "git actions must not happen")
    assert_true(manifest["models_called"] is False, "models must not be called")
    for key in (
        "product_packet",
        "prd_brief",
        "wireframe_brief",
        "ui_ux_brief",
        "feature_spec",
        "implementation_plan",
        "manifest",
        "report",
    ):
        assert_true(paths[key].exists(), f"expected output missing: {key}")
    assert_true("No worker prompts were executed" in paths["product_packet"].read_text(encoding="utf-8"), "product packet should preserve non-execution boundary")
    assert_true("NOT_SPECIFIED_IN_DISCOVERY_HANDOFF" in paths["wireframe_brief"].read_text(encoding="utf-8"), "wireframe brief should mark unspecified UI details")

    with contextlib.redirect_stdout(io.StringIO()):
        rc = command_tool.main(["build-packet", "--queue", str(DISCOVERY_QUEUE), "--output", str(LANE_ROOT)])
    assert_true(rc == 0, "product-dev command build-packet should succeed")

    lane_audit = audit_tool.audit_product_development_lane(LANE_ROOT)
    assert_true(not lane_audit.errors, "Product Development Lane audit should pass: " + "; ".join(lane_audit.errors))
    with contextlib.redirect_stdout(io.StringIO()):
        rc = command_tool.main(["help"])
    assert_true(rc == 0, "product-dev help should succeed")
    with contextlib.redirect_stdout(io.StringIO()):
        rc = command_tool.main(["audit"])
    assert_true(rc == 0, "product-dev audit should succeed")

    print("Product Development Lane validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
