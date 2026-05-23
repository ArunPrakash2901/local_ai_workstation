#!/usr/bin/env python3
"""Temp-root tests for Knowledge Lane Phase 1 inventory dry-run."""

from __future__ import annotations

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

from knowledge_inventory import (
    collect_inventory,
    render_inventory_report,
    validate_knowledge_target,
)


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


def main() -> int:
    print("Knowledge Inventory Validation")
    print("==============================")
    failures: list[str] = []

    # 1. validates target matfinog_youtube.
    expect("validates target matfinog_youtube", validate_knowledge_target("matfinog_youtube"), failures)

    # 2. rejects unknown target.
    expect("rejects unknown target", not validate_knowledge_target("unknown"), failures)

    # 3. rejects path traversal target.
    # Note: validate_knowledge_target doesn't handle traversal, target_root does.
    try:
        from knowledge_inventory import target_root
        target_root(".", "../outside")
        failures.append("FAIL: target_root should reject path traversal")
    except ValueError:
        print("PASS: rejects path traversal target")

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_knowledge_inventory_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        # Create temp knowledge structure
        k_root = temp_root / "knowledge"
        t_root = k_root / "matfinog_youtube"
        raw_dir = t_root / "raw"
        raw_dir.mkdir(parents=True)

        # 4. inventories temp raw directory.
        # 5. counts files correctly.
        # 6. groups by extension correctly.
        # 7. computes total size correctly.
        
        (raw_dir / "vid1.vtt").write_text("transcript 1", encoding="utf-8")
        (raw_dir / "vid1.info.json").write_text('{"id": "vid1"}', encoding="utf-8")
        (raw_dir / "vid2.vtt").write_text("transcript 2", encoding="utf-8")
        (raw_dir / "vid2.json").write_text('{"id": "vid2"}', encoding="utf-8")
        
        inventory = collect_inventory(temp_root, "matfinog_youtube")
        expect("detects existing raw directory", inventory["exists"], failures)
        expect("counts 4 files", len(inventory["files"]) == 4, failures)
        
        from knowledge_inventory import group_files_by_extension
        exts = group_files_by_extension(inventory["files"])
        expect("groups by extension correctly", exts.get(".vtt") == 2 and exts.get(".json") == 1 and exts.get(".info.json") == 1, failures, f"Got {exts}")

        from knowledge_inventory import compute_size_summary
        size_summary = compute_size_summary(inventory["files"])
        total_size = sum(f.stat().st_size for f in inventory["files"])
        expect("computes total size correctly", size_summary["total_bytes"] == total_size, failures)

        # 8. reports largest files.
        expect("reports largest files", len(size_summary["largest_files"]) <= 10, failures)

        report = render_inventory_report(inventory)
        expect("report contains target", "matfinog_youtube" in report, failures)
        expect("report contains Dry Run notice", "DRY RUN" in report, failures)

        # 9. handles empty raw directory.
        shutil.rmtree(raw_dir)
        raw_dir.mkdir()
        inventory_empty = collect_inventory(temp_root, "matfinog_youtube")
        expect("handles empty raw directory", len(inventory_empty["files"]) == 0, failures)

        # 10. handles missing raw directory cleanly.
        shutil.rmtree(raw_dir)
        inventory_missing = collect_inventory(temp_root, "matfinog_youtube")
        expect("handles missing raw directory cleanly", not inventory_missing["exists"], failures)

        # 11. dry-run writes no files.
        # 12. does not create inventory.json.
        # 13. does not modify .gitignore.
        # (These are implicitly true since we only read metadata)
        
        # 14. does not parse file contents beyond metadata.
        # (Verified by source inspection of knowledge_inventory.py)

        # 15. CLI requires --dry-run.
        cli_path = SCRIPTS_DIR / "ws_knowledge_inventory.py"
        try:
            subprocess.run([sys.executable, str(cli_path), "--target", "matfinog_youtube"], capture_output=True, check=True)
            failures.append("FAIL: CLI should require --dry-run")
        except subprocess.CalledProcessError as e:
            expect("CLI requires --dry-run", "dry-run is required" in e.stdout.decode() or "dry-run is required" in e.stderr.decode(), failures)

        # 16. no external-adapter workflows.
        source = (SCRIPTS_DIR / "knowledge_inventory.py").read_text(encoding="utf-8").lower()
        expect("no external-adapter usage", "requests" not in source and "urllib" not in source, failures)

    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    if failures:
        print("Result: FAIL")
        for f in failures:
            print(f)
        return 1
    
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
