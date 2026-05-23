import unittest
import json
import subprocess
from pathlib import Path
import sys

# Adjust path for local imports
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.paper_replication import (
    load_research_paper_schema,
    load_replication_plan_schema,
    validate_research_paper_record,
    validate_replication_plan,
    build_research_paper_record,
    compute_paper_id,
    build_replication_plan_from_inputs,
    write_research_paper_record
)

class TestQuantPaperReplication(unittest.TestCase):
    def setUp(self):
        self.paper_schema = load_research_paper_schema()
        self.plan_schema = load_replication_plan_schema()
        
        self.test_dir = BASE_DIR / "scratch" / "quant_papers"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.valid_note = self.test_dir / "test_valid_note.md"
        self.valid_note.write_text("A simple, safe paper note for testing.")

    def tearDown(self):
        if self.valid_note.exists():
            self.valid_note.unlink()

    def test_schema_loads(self):
        self.assertIn("paper_id", self.paper_schema['required_fields'])
        self.assertIn("replication_plan_id", self.plan_schema['required_fields'])

    def test_valid_paper_record_passes(self):
        record = build_research_paper_record(
            title="Test Paper",
            source_type="manual_note",
            local_note_file=str(self.valid_note.relative_to(BASE_DIR))
        )
        self.assertTrue(validate_research_paper_record(record, self.paper_schema))

    def test_missing_required_field_fails(self):
        record = build_research_paper_record("Test", "manual_note", str(self.valid_note.relative_to(BASE_DIR)))
        del record["abstract_or_summary"]
        with self.assertRaises(ValueError):
            validate_research_paper_record(record, self.paper_schema)

    def test_unsafe_flag_fails(self):
        record = build_research_paper_record("Test", "manual_note", str(self.valid_note.relative_to(BASE_DIR)))
        record["safety_trading_signal_generated"] = True
        with self.assertRaises(ValueError):
            validate_research_paper_record(record, self.paper_schema)

    def test_forbidden_status_fails(self):
        record = build_research_paper_record("Test", "manual_note", str(self.valid_note.relative_to(BASE_DIR)))
        record["review_status"] = "live_trading"
        with self.assertRaises(ValueError):
            validate_research_paper_record(record, self.paper_schema)

    def test_buy_sell_hold_wording_blocked(self):
        bad_note = self.test_dir / "test_bad_note.md"
        try:
            bad_note.write_text("This paper claims a guaranteed profit using direct buy strategies.")
            with self.assertRaisesRegex(ValueError, "Forbidden phrase found"):
                build_research_paper_record("Test", "manual_note", str(bad_note.relative_to(BASE_DIR)))
        finally:
            if bad_note.exists():
                bad_note.unlink()

    def test_paper_note_outside_scratch_blocked(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp.write(b"Outside file.")
            tmp_path = tmp.name
            
        try:
            with self.assertRaisesRegex(ValueError, "must be within scratch/quant_papers"):
                build_research_paper_record("Test", "manual_note", tmp_path)
        finally:
            Path(tmp_path).unlink()

    def test_path_traversal_blocked(self):
        with self.assertRaisesRegex(ValueError, "must be within scratch/quant_papers"):
            build_research_paper_record("Test", "manual_note", "../../../Windows/System32/cmd.exe")

    def test_oversized_note_blocked(self):
        large_note = self.test_dir / "test_large_note.md"
        try:
            large_note.write_bytes(b"A" * (101 * 1024)) # 101 KB
            with self.assertRaisesRegex(ValueError, "exceeds maximum allowed size"):
                build_research_paper_record("Test", "manual_note", str(large_note.relative_to(BASE_DIR)))
        finally:
            if large_note.exists():
                large_note.unlink()

    def test_deterministic_paper_id(self):
        r1 = build_research_paper_record("Same Title", "manual_note", str(self.valid_note.relative_to(BASE_DIR)))
        r2 = build_research_paper_record("Same Title", "manual_note", str(self.valid_note.relative_to(BASE_DIR)))
        self.assertEqual(r1["paper_id"], r2["paper_id"])

    def test_dry_run_write_does_not_create_file(self):
        record = build_research_paper_record("Test", "manual_note", str(self.valid_note.relative_to(BASE_DIR)))
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_research_paper_record(record, output_dir=tmpdir, dry_run=True)
            self.assertEqual(result["status"], "dry_run")
            self.assertFalse(Path(result["path"]).exists())

    def test_replication_plan_links_correctly(self):
        paper = build_research_paper_record("Test Paper", "manual_note", str(self.valid_note.relative_to(BASE_DIR)))
        idea = {"idea_id": "RI-12345"}
        
        plan = build_replication_plan_from_inputs(idea_record=idea, paper_record=paper)
        
        self.assertEqual(plan["linked_idea_id"], "RI-12345")
        self.assertEqual(plan["linked_paper_id"], paper["paper_id"])
        self.assertEqual(plan["human_review_required"], True)
        self.assertEqual(plan["review_status"], "draft")
        self.assertTrue(validate_replication_plan(plan, self.plan_schema))
        self.assertFalse(plan["safety_trading_signal_generated"])

    def test_standalone_cli_schema_check(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "paper_replication_cli.py"
        result = subprocess.run(
            [sys.executable, str(cli_path), "schema-check", "--dry-run"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("[OK] Research Paper Schema Loaded.", result.stdout)

    def test_standalone_cli_paper_intake_dry_run(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "paper_replication_cli.py"
        result = subprocess.run(
            [
                sys.executable, str(cli_path), "paper-intake",
                "--paper-note", str(self.valid_note.relative_to(BASE_DIR)),
                "--dry-run"
            ],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("[DRY_RUN]", result.stdout)
        self.assertIn("financial_advice_generated: false", result.stdout)

if __name__ == '__main__':
    unittest.main()
