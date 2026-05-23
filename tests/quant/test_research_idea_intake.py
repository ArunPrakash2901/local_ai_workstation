import unittest
import json
import subprocess
from pathlib import Path
import sys

# Adjust path for local imports
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.idea_intake import (
    load_research_idea_schema,
    validate_research_idea_record,
    build_research_idea_record,
    compute_idea_id,
    write_research_idea_record
)

from scripts.quant.hypothesis_contract import (
    load_hypothesis_contract_schema,
    validate_hypothesis_contract,
    build_hypothesis_contract_from_idea,
    write_hypothesis_contract
)

class TestQuantIdeaIntake(unittest.TestCase):
    def setUp(self):
        self.idea_schema = load_research_idea_schema()
        self.hyp_schema = load_hypothesis_contract_schema()
        
    def test_schema_loads(self):
        self.assertIn("idea_id", self.idea_schema['required_fields'])
        self.assertIn("hypothesis_id", self.hyp_schema['required_fields'])

    def test_valid_idea_record_passes(self):
        record = build_research_idea_record(
            title="Test Idea",
            source_type="human_note",
            raw_idea_text="Investigate mean reversion in VIX."
        )
        self.assertTrue(validate_research_idea_record(record, self.idea_schema))

    def test_missing_required_field_fails(self):
        record = build_research_idea_record("Test", "human_note", "Text")
        del record["raw_idea_text"]
        with self.assertRaises(ValueError):
            validate_research_idea_record(record, self.idea_schema)

    def test_unsafe_flag_fails(self):
        record = build_research_idea_record("Test", "human_note", "Text")
        record["safety_trading_signal_generated"] = True
        with self.assertRaises(ValueError):
            validate_research_idea_record(record, self.idea_schema)

    def test_forbidden_status_fails(self):
        record = build_research_idea_record("Test", "human_note", "Text")
        record["review_status"] = "live_trading"
        with self.assertRaises(ValueError):
            validate_research_idea_record(record, self.idea_schema)

    def test_buy_sell_hold_wording_blocked(self):
        bad_texts = [
            "We should direct buy AAPL.",
            "This provides a guaranteed profit.",
            "Broker execution module here.",
            "Live trading test."
        ]
        for bad_text in bad_texts:
            record = build_research_idea_record("Test", "human_note", bad_text)
            with self.assertRaisesRegex(ValueError, "Forbidden phrase found"):
                validate_research_idea_record(record, self.idea_schema)

    def test_deterministic_idea_id(self):
        r1 = build_research_idea_record("Same Title", "human_note", "Text A", source_reference="RefA")
        r2 = build_research_idea_record("Same Title", "human_note", "Text B", source_reference="RefA")
        self.assertEqual(r1["idea_id"], r2["idea_id"])

    def test_dry_run_write_does_not_create_file(self):
        record = build_research_idea_record("Test", "human_note", "Text")
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_research_idea_record(record, output_dir=tmpdir, dry_run=True)
            self.assertEqual(result["status"], "dry_run")
            self.assertFalse(Path(result["path"]).exists())

    def test_hypothesis_draft_links_correctly(self):
        idea = build_research_idea_record("Test Idea", "human_note", "Text")
        hyp = build_hypothesis_contract_from_idea(idea)
        
        self.assertEqual(hyp["linked_idea_id"], idea["idea_id"])
        self.assertEqual(hyp["human_review_required"], True)
        self.assertEqual(hyp["review_status"], "draft")
        self.assertTrue(validate_hypothesis_contract(hyp, self.hyp_schema))

    def test_hypothesis_does_not_approve_anything(self):
        idea = build_research_idea_record("Test Idea", "human_note", "Text")
        hyp = build_hypothesis_contract_from_idea(idea)
        self.assertFalse(hyp["safety_bot_logic_generated"])
        self.assertFalse(hyp["safety_live_trading_logic_generated"])

    def test_standalone_cli_schema_check(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "idea_cli.py"
        result = subprocess.run(
            [sys.executable, str(cli_path), "schema-check", "--dry-run"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("[OK] Research Idea Schema Loaded.", result.stdout)

    def test_standalone_cli_idea_intake_dry_run(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "idea_cli.py"
        result = subprocess.run(
            [
                sys.executable, str(cli_path), "idea-intake",
                "--title", "CLI Test",
                "--source-type", "human_note",
                "--raw-idea", "Safe test idea",
                "--dry-run"
            ],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("[DRY_RUN]", result.stdout)
        self.assertIn("financial_advice_generated: false", result.stdout)

    def test_cli_rejects_both_raw_idea_and_idea_file(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "idea_cli.py"
        result = subprocess.run(
            [
                sys.executable, str(cli_path), "idea-intake",
                "--title", "Test",
                "--source-type", "human_note",
                "--raw-idea", "A",
                "--idea-file", "B"
            ],
            capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cannot provide both", result.stdout)

    def test_cli_rejects_missing_idea_file(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "idea_cli.py"
        result = subprocess.run(
            [
                sys.executable, str(cli_path), "idea-intake",
                "--title", "Test",
                "--source-type", "human_note",
                "--idea-file", "scratch/quant_ideas/does_not_exist_at_all.md"
            ],
            capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Idea file not found", result.stdout)

    def test_cli_rejects_path_traversal(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "idea_cli.py"
        result = subprocess.run(
            [
                sys.executable, str(cli_path), "idea-intake",
                "--title", "Test",
                "--source-type", "human_note",
                "--idea-file", "../../../Windows/System32/cmd.exe"
            ],
            capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Path must be within", result.stdout)

    def test_cli_rejects_oversized_file(self):
        import tempfile
        cli_path = BASE_DIR / "scripts" / "quant" / "idea_cli.py"
        # We need a file inside an approved directory to test size independently of path rules.
        test_dir = BASE_DIR / "scratch" / "quant_ideas"
        test_dir.mkdir(parents=True, exist_ok=True)
        large_file = test_dir / "large_test_file.md"
        
        try:
            large_file.write_bytes(b"A" * (51 * 1024)) # 51 KB
            
            result = subprocess.run(
                [
                    sys.executable, str(cli_path), "idea-intake",
                    "--title", "Test",
                    "--source-type", "human_note",
                    "--idea-file", str(large_file.relative_to(BASE_DIR))
                ],
                cwd=str(BASE_DIR),
                capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exceeds maximum allowed size", result.stdout)
        finally:
            if large_file.exists():
                large_file.unlink()

    def test_cli_idea_intake_file_dry_run(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "idea_cli.py"
        test_dir = BASE_DIR / "scratch" / "quant_ideas"
        test_dir.mkdir(parents=True, exist_ok=True)
        valid_file = test_dir / "valid_test_file.md"
        
        try:
            valid_file.write_text("This is a safe idea test.")
            
            result = subprocess.run(
                [
                    sys.executable, str(cli_path), "idea-intake",
                    "--title", "File Test",
                    "--source-type", "human_note",
                    "--idea-file", str(valid_file.relative_to(BASE_DIR)),
                    "--dry-run"
                ],
                cwd=str(BASE_DIR),
                capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("[DRY_RUN]", result.stdout)
        finally:
            if valid_file.exists():
                valid_file.unlink()

if __name__ == '__main__':
    unittest.main()
