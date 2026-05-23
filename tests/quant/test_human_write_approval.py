import unittest
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys
import yaml

# Add scripts/quant to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR / "scripts" / "quant"))

from human_write_approval import (
    load_human_write_approval_schema,
    validate_human_write_approval,
    evaluate_write_approval,
    compute_file_hash,
    build_blocked_example_approval,
    parse_human_write_approval_file,
    compute_approval_id
)

class TestHumanWriteApproval(unittest.TestCase):

    def test_schema_loads(self):
        schema = load_human_write_approval_schema()
        self.assertIn("required_fields", schema)
        self.assertEqual(schema["approval_type"], "research_idea_intake_write")

    def test_template_exists(self):
        template_path = BASE_DIR / "contracts" / "quant" / "human_write_approval_template.md"
        self.assertTrue(template_path.exists())

    def test_valid_draft_approval_validates(self):
        record = build_blocked_example_approval()
        self.assertTrue(validate_human_write_approval(record))

    def test_missing_required_field_fails(self):
        record = build_blocked_example_approval()
        del record["operator_name"]
        with self.assertRaisesRegex(ValueError, "Missing required field: operator_name"):
            validate_human_write_approval(record)

    def test_unsafe_safety_flag_fails(self):
        record = build_blocked_example_approval()
        record["safety_financial_advice_generated"] = True
        with self.assertRaisesRegex(ValueError, "safety_financial_advice_generated MUST be explicitly False"):
            validate_human_write_approval(record)

    def test_missing_forbidden_actions_fails(self):
        record = build_blocked_example_approval()
        record["forbidden_actions"] = ["run_backtest"] # Missing others
        with self.assertRaisesRegex(ValueError, "Mandatory forbidden action missing from approval: generate_signal"):
            validate_human_write_approval(record)

    def test_unsupported_target_command_fails(self):
        record = build_blocked_example_approval()
        record["target_command"] = "ws quant execute-backtest --write"
        with self.assertRaisesRegex(ValueError, "Unsupported target command"):
            validate_human_write_approval(record)

    def test_source_input_outside_approved_folders_fails(self):
        record = build_blocked_example_approval()
        record["source_input_file"] = "C:/Windows/System32/config"
        with self.assertRaisesRegex(ValueError, "Source input file must be within approved folders"):
            validate_human_write_approval(record)

    def test_intended_output_outside_approved_folders_fails(self):
        record = build_blocked_example_approval()
        record["intended_output_directory"] = "data/market_data/"
        with self.assertRaisesRegex(ValueError, "Intended output directory must be within approved folders"):
            validate_human_write_approval(record)

    def test_expired_approval_fails(self):
        record = build_blocked_example_approval()
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        record["expires_at"] = past_time
        with self.assertRaisesRegex(ValueError, "Approval has expired"):
            validate_human_write_approval(record)

    def test_missing_operator_confirmation_fails(self):
        record = build_blocked_example_approval()
        record["operator_confirmation"] = ""
        with self.assertRaisesRegex(ValueError, "Operator confirmation is missing"):
            validate_human_write_approval(record)

    def test_approved_status_blocked_when_future_enabled_is_false(self):
        record = build_blocked_example_approval()
        record["approval_status"] = "approved_for_single_local_write"
        result = evaluate_write_approval(record, future_write_enabled=False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["allowed"])

    def test_evaluate_write_approval_blocks_by_default(self):
        record = build_blocked_example_approval()
        result = evaluate_write_approval(record) # future_write_enabled=False by default
        self.assertEqual(result["status"], "BLOCKED")

    def test_compute_file_hash_works_on_tiny_fixture(self):
        fixture_path = BASE_DIR / "scratch" / "test_hash_fixture.txt"
        with open(fixture_path, "w") as f:
            f.write("hello world")
        try:
            h = compute_file_hash(fixture_path)
            self.assertTrue(h.startswith("sha256:"))
            # sha256 of "hello world" is b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
            self.assertIn("b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9", h)
        finally:
            if fixture_path.exists():
                fixture_path.unlink()

    def test_parse_human_write_approval_file_md(self):
        path = BASE_DIR / "scratch" / "quant_approvals" / "example_idea_intake_write_approval_blocked.md"
        record = parse_human_write_approval_file(path)
        self.assertEqual(record["approval_id"], "HAF-WRITE-RI-EXAMPLE-BLOCKED")
        self.assertEqual(record["approval_type"], "research_idea_intake_write")

if __name__ == '__main__':
    unittest.main()
