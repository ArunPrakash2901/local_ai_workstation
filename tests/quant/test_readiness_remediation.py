import unittest
import json
import subprocess
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.readiness_remediation import (
    load_readiness_gap_report_schema,
    validate_readiness_gap_report,
    build_gap_report
)
from scripts.quant.strategy_revision import (
    load_strategy_candidate_revision_schema,
    validate_strategy_candidate_revision,
    apply_candidate_revision
)
from scripts.quant.human_approval import (
    load_human_backtest_approval_schema,
    validate_human_backtest_approval,
    build_pending_human_backtest_approval
)

class TestQuantReadinessRemediation(unittest.TestCase):
    def setUp(self):
        self.gap_schema = load_readiness_gap_report_schema()
        self.rev_schema = load_strategy_candidate_revision_schema()
        self.app_schema = load_human_backtest_approval_schema()

        self.test_dir = BASE_DIR / "scratch" / "quant_strategy_candidates"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.valid_note = self.test_dir / "test_valid_rev_note.md"
        self.valid_note.write_text("A simple, safe revision note.")

    def tearDown(self):
        if self.valid_note.exists():
            self.valid_note.unlink()

    def test_schema_loads(self):
        self.assertIn("gap_report_id", self.gap_schema['required_fields'])
        self.assertIn("revision_id", self.rev_schema['required_fields'])
        self.assertIn("approval_id", self.app_schema['required_fields'])

    def test_gap_report_identifies_unknowns(self):
        cand = {"strategy_candidate_id": "CAN-1", "universe_definition": "UNKNOWN", "title": "TEST"}
        rdy = {"readiness_id": "RDY-1", "readiness_status": "needs_more_detail"}
        
        gap = build_gap_report(cand, rdy)
        self.assertIn("universe_definition", gap["missing_fields"])
        self.assertEqual(gap["recommended_next_status"], "revise_candidate")
        self.assertTrue(validate_readiness_gap_report(gap, self.gap_schema))

    def test_revision_note_applies_safely(self):
        cand = {"strategy_candidate_id": "CAN-1", "universe_definition": "UNKNOWN"}
        gap = {"gap_report_id": "GAP-1"}
        
        rev = apply_candidate_revision(cand, gap, "Clarifying universe.")
        self.assertEqual(rev["revision_status"], "draft")
        self.assertEqual(rev["candidate_record_after_revision"]["strategy_candidate_id"], "CAN-1-R1")
        self.assertTrue(validate_strategy_candidate_revision(rev, self.rev_schema))

    def test_unsafe_revision_note_fails(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        with self.assertRaisesRegex(ValueError, "Forbidden phrase found"):
            apply_candidate_revision(cand, None, "We should paper trading this.")

    def test_approval_stub_defaults_pending(self):
        app = build_pending_human_backtest_approval()
        self.assertEqual(app["approval_status"], "pending")
        self.assertTrue(validate_human_backtest_approval(app, self.app_schema))

    def test_approval_stub_cannot_be_approved_in_this_phase(self):
        app = build_pending_human_backtest_approval()
        app["approval_status"] = "approved_for_single_backtest_plan"
        with self.assertRaisesRegex(ValueError, "Cannot default to approved status"):
            validate_human_backtest_approval(app, self.app_schema)

    def test_cli_schema_check(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "readiness_remediation_cli.py"
        result = subprocess.run([sys.executable, str(cli_path), "schema-check", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Schema Loaded", result.stdout)

    def test_cli_path_traversal_blocked(self):
        import tempfile
        cli_path = BASE_DIR / "scripts" / "quant" / "readiness_remediation_cli.py"
        
        with tempfile.NamedTemporaryFile(suffix=".json", mode='w', delete=False) as tmp_cand:
            json.dump({"strategy_candidate_id": "CAN-1"}, tmp_cand)
            cand_path = tmp_cand.name
            
        with tempfile.NamedTemporaryFile(suffix=".json", mode='w', delete=False) as tmp_gap:
            json.dump({"gap_report_id": "GAP-1"}, tmp_gap)
            gap_path = tmp_gap.name

        try:
            result = subprocess.run([
                sys.executable, str(cli_path), "revise-candidate",
                "--candidate-file", cand_path,
                "--gap-report-file", gap_path,
                "--revision-note", "../../../Windows/System32/cmd.exe"
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be within scratch/quant_strategy_candidates/", result.stdout)
        finally:
            Path(cand_path).unlink()
            Path(gap_path).unlink()

if __name__ == '__main__':
    unittest.main()
