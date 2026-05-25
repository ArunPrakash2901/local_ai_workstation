#!/usr/bin/env python3
"""Local tests for Product Development Lane review artifacts."""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd: list[str]) -> tuple[int, str]:
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        [sys.executable] + cmd,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    )
    return result.returncode, result.stdout + result.stderr

def test_review_artifacts():
    lane_root = Path("product_development_lane")
    tools_dir = lane_root / "tools"
    manifest_path = lane_root / "manifests/positive_path_example_product_development_manifest.json"
    output_root = lane_root / "review_artifacts"

    print("--- Test: Help Commands ---")
    rc1, out1 = run_command([str(tools_dir / "build_review_html.py"), "--help"])
    assert rc1 == 0, f"build_review_html.py --help failed: {out1}"
    
    rc2, out2 = run_command([str(tools_dir / "audit_review_artifacts.py"), "--help"])
    assert rc2 == 0, f"audit_review_artifacts.py --help failed: {out2}"

    print("\n--- Test: HTML Generation ---")
    rc3, out3 = run_command([
        str(tools_dir / "build_review_html.py"),
        "--manifest", str(manifest_path),
        "--output", str(output_root)
    ])
    assert rc3 == 0, f"Generation failed: {out3}"
    assert "Successfully generated review artifacts" in out3

    print("\n--- Test: Artifact Presence ---")
    dashboard = output_root / "html/positive_path_example_review_dashboard.html"
    assert dashboard.exists(), "Dashboard missing"
    
    prd_review = output_root / "html/positive_path_example_prd_brief_review.html"
    assert prd_review.exists(), "PRD review HTML missing"
    
    review_manifest = output_root / "manifests/positive_path_example_review_artifact_manifest.json"
    assert review_manifest.exists(), "Review manifest missing"
    
    report = output_root / "reports/positive_path_example_review_artifact_report.md"
    assert report.exists(), "Review report missing"

    print("\n--- Test: Safety Warnings ---")
    prd_content = prd_review.read_text(encoding="utf-8")
    assert "Review surface only. Canonical source remains Markdown/JSON." in prd_content
    assert "No execution of worker prompts occurred." in prd_content
    assert "No branches were created" in prd_content
    assert "http://" not in prd_content or "<p>http://" in prd_content or "<li>http://" in prd_content # Allowed in content
    assert "<script" not in prd_content or "src=" not in prd_content

    print("\n--- Test: Audit ---")
    rc4, out4 = run_command([str(tools_dir / "audit_review_artifacts.py"), "--root", str(lane_root)])
    assert rc4 == 0, f"Audit failed: {out4}"
    assert "Result: PASS" in out4
    assert "review_manifests: 1" in out4

    print("\n--- All Review Artifact Tests Passed ---")

if __name__ == "__main__":
    try:
        test_review_artifacts()
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
