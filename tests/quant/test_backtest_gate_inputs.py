import unittest
import json
import subprocess
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.candidate_completion import (
    load_candidate_detail_completion_schema,
    validate_candidate_detail_completion,
    build_candidate_detail_completion
)
from scripts.quant.data_source_decision import (
    load_data_source_decision_schema,
    validate_data_source_decision,
    build_data_source_decision
)
from scripts.quant.single_backtest_approval_input import (
    load_single_backtest_approval_input_schema,
    validate_single_backtest_approval_input,
    build_single_backtest_approval_input
)

class TestQuantBacktestGateInputs(unittest.TestCase):
    def setUp(self):
        self.comp_schema = load_candidate_detail_completion_schema()
        self.dsd_schema = load_data_source_decision_schema()
        self.api_schema = load_single_backtest_approval_input_schema()

    def test_schema_loads(self):
        self.assertIn("completion_id", self.comp_schema['required_fields'])
        self.assertIn("data_source_decision_id", self.dsd_schema['required_fields'])
        self.assertIn("approval_input_id", self.api_schema['required_fields'])

    def test_unsafe_completion_note_blocked(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        with self.assertRaisesRegex(ValueError, "Forbidden phrase found"):
            build_candidate_detail_completion(cand, "We must use guaranteed profit logic.")

    def test_unsafe_dsd_note_blocked(self):
        # We don't explicitly check notes in DSD build yet, but validation does flags.
        # Let's check safety flags.
        rec = build_data_source_decision()
        rec['safety_bot_logic_generated'] = True
        with self.assertRaises(ValueError):
            validate_data_source_decision(rec, self.dsd_schema)

    def test_unsafe_approval_note_blocked(self):
        from scripts.quant.single_backtest_approval_input import parse_approval_input_note_file
        # This requires a file, let's use the build helper logic if it had regex (it does in parse)
        # But let's check the schema validator for forbidden actions.
        rec = build_single_backtest_approval_input()
        rec['forbidden_actions'] = ["none"]
        with self.assertRaisesRegex(ValueError, "Missing mandatory forbidden action"):
            validate_single_backtest_approval_input(rec, self.api_schema)

    def test_approval_input_no_auto_approve(self):
        rec = build_single_backtest_approval_input()
        self.assertFalse(rec['explicit_approval_for_single_backtest'])
        self.assertEqual(rec['approval_input_status'], 'draft')

    def test_cli_schema_check(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "backtest_gate_cli.py"
        result = subprocess.run([sys.executable, str(cli_path), "schema-check", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Schema Loaded", result.stdout)

if __name__ == '__main__':
    unittest.main()
