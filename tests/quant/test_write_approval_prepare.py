import unittest
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import sys
import os

# Add scripts/quant to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR / "scripts" / "quant"))

from write_approval_prepare import (
    compute_file_sha256,
    validate_approved_source_input_path,
    build_approval_draft_record,
    write_approval_draft,
    build_evidence_pack,
    write_evidence_pack
)
from human_write_approval import evaluate_write_approval

class TestWriteApprovalPrepare(unittest.TestCase):

    def setUp(self):
        self.test_idea_file = BASE_DIR / "scratch" / "quant_ideas" / "test_idea.md"
        with open(self.test_idea_file, "w") as f:
            f.write("Test Research Idea")
        
        self.test_approval_dir = BASE_DIR / "scratch" / "test_approvals"
        self.test_evidence_dir = self.test_approval_dir / "evidence"

    def tearDown(self):
        if self.test_idea_file.exists():
            self.test_idea_file.unlink()
        
        # Clean up test directories
        import shutil
        if self.test_approval_dir.exists():
            shutil.rmtree(self.test_approval_dir)

    def test_source_input_hash_computes_deterministically(self):
        h1 = compute_file_sha256(self.test_idea_file)
        h2 = compute_file_sha256(self.test_idea_file)
        self.assertEqual(h1, h2)
        self.assertTrue(h1.startswith("sha256:"))

    def test_approved_source_path_passes(self):
        self.assertTrue(validate_approved_source_input_path(Path("scratch/quant_ideas/test_idea.md")))

    def test_path_traversal_source_path_fails(self):
        with self.assertRaisesRegex(ValueError, "Source input path must be within scratch/quant_ideas/"):
            validate_approved_source_input_path(Path("scratch/quant_ideas/../../etc/passwd"))

    def test_source_path_outside_scratch_quant_ideas_fails(self):
        with self.assertRaisesRegex(ValueError, "Source input path must be within scratch/quant_ideas/"):
            validate_approved_source_input_path(Path("docs/README.md"))

    def test_oversized_idea_file_fails(self):
        oversized_file = BASE_DIR / "scratch" / "quant_ideas" / "oversized.md"
        with open(oversized_file, "wb") as f:
            f.write(b"0" * (51 * 1024)) # 51KB
        try:
            with self.assertRaisesRegex(ValueError, "exceeds 50KB limit"):
                validate_approved_source_input_path(Path("scratch/quant_ideas/oversized.md"))
        finally:
            if oversized_file.exists():
                oversized_file.unlink()

    def test_approval_draft_defaults_to_not_approved(self):
        record = build_approval_draft_record("Test Title", "human_note", "scratch/quant_ideas/test_idea.md")
        self.assertEqual(record["approval_status"], "draft")
        self.assertEqual(record["operator_confirmation"], "PENDING_REVIEW")

    def test_evidence_pack_does_not_grant_approval(self):
        record = build_approval_draft_record("Test Title", "human_note", "scratch/quant_ideas/test_idea.md")
        evidence = build_evidence_pack(record)
        self.assertFalse(evidence["safety_flags"]["safety_backtest_run"])

    def test_write_draft_writes_only_under_approved_paths(self):
        record = build_approval_draft_record("Test Title", "human_note", "scratch/quant_ideas/test_idea.md")
        result = write_approval_draft(record, output_dir=self.test_approval_dir, dry_run=False)
        self.assertEqual(result["status"], "written")
        self.assertTrue(Path(result["path"]).exists())
        self.assertTrue(str(result["path"]).startswith(str(self.test_approval_dir)))

    def test_dry_run_creates_no_files(self):
        record = build_approval_draft_record("Test Title", "human_note", "scratch/quant_ideas/test_idea.md")
        result = write_approval_draft(record, output_dir=self.test_approval_dir, dry_run=True)
        self.assertEqual(result["status"], "dry_run")
        self.assertFalse(Path(result["path"]).exists())

    def test_human_write_approval_evaluator_still_blocks_draft_approval(self):
        record = build_approval_draft_record("Test Title", "human_note", "scratch/quant_ideas/test_idea.md")
        result = evaluate_write_approval(record, future_write_enabled=False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["allowed"])

if __name__ == '__main__':
    unittest.main()
