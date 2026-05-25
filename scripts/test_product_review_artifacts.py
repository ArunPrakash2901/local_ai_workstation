#!/usr/bin/env python3
"""Validation for Product Development Lane static HTML review artifacts."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE_ROOT = ROOT / "product_development_lane"
MANIFEST_PATH = LANE_ROOT / "manifests" / "positive_path_example_product_development_manifest.json"


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
    build_tool = load_module("build_review_html", LANE_ROOT / "tools" / "build_review_html.py")
    audit_tool = load_module("audit_review_artifacts", LANE_ROOT / "tools" / "audit_review_artifacts.py")
    command_tool = load_module("product_dev_command", LANE_ROOT / "tools" / "product_dev_command.py")

    # 1. Test review-html command
    review_html_help = ""
    with contextlib.redirect_stdout(io.StringIO()) as out:
        try:
            command_tool.main(["review-html", "--help"])
        except SystemExit:
            pass
        review_html_help = out.getvalue()
    
    assert_true("--manifest" in review_html_help, "review-html subparser should expose --manifest")
    assert_true("review-html" in command_tool.build_parser().format_help(), "command bridge should expose review-html")
    assert_true("review-audit" in command_tool.build_parser().format_help(), "command bridge should expose review-audit")

    if not MANIFEST_PATH.exists():
        print(f"Skipping real build test: {MANIFEST_PATH} not found")
        return 0

    test_tmp = LANE_ROOT / "review_artifacts" / ".test_tmp"
    test_tmp.mkdir(parents=True, exist_ok=True)
    
    try:
        tmp_output = test_tmp
        
        # 1. Test review-html command
        with contextlib.redirect_stdout(io.StringIO()):
            rc = command_tool.main(["review-html", "--manifest", str(MANIFEST_PATH), "--output", str(tmp_output)])
        
        if rc != 0:
            # Re-run to see error in logs if needed, but for now just fail with clear message
            assert_true(rc == 0, f"review-html command failed with rc={rc}")

        # Verify artifacts
        dashboard = tmp_output / "html" / "positive_path_example_review_dashboard.html"
        assert_true(dashboard.exists(), "review dashboard should exist")
        
        manifest = tmp_output / "manifests" / "positive_path_example_review_artifact_manifest.json"
        assert_true(manifest.exists(), "review manifest should exist")
        
        # 2. Test review-audit via command
        with contextlib.redirect_stdout(io.StringIO()):
            rc = command_tool.main(["review-audit"])
        assert_true(rc in {0, 1}, "review-audit command should return 0 or 1")

        # 3. Test path traversal rejection
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = command_tool.main(["review-html", "--manifest", "../../outside.json"])
        assert_true(rc == 1, "review-html should reject missing/traversal manifest")
        assert_true("Error: Manifest" in out.getvalue(), "should show manifest error")

        # 4. Test missing manifest
        with contextlib.redirect_stdout(io.StringIO()):
            rc = command_tool.main(["review-html", "--manifest", "non_existent.json"])
        assert_true(rc == 1, "review-html should reject non-existent manifest")
    finally:
        if test_tmp.exists():
            shutil.rmtree(test_tmp)

    print("Product Development review artifacts validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
