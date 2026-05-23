import unittest
import json
import subprocess
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.backtest_approval_validation import (
    load_backtest_approval_validation_schema,
    validate_backtest_approval_validation,
    build_backtest_approval_validation
)
from scripts.quant.backtest_eligibility import (
    load_backtest_eligibility_report_schema,
    validate_backtest_eligibility_report,
    build_backtest_eligibility_report
)

class TestQuantBacktestEligibility(unittest.TestCase):
    def setUp(self):
        self.vld_schema = load_backtest_approval_validation_schema()
        self.elg_schema = load_backtest_eligibility_report_schema()

    def test_schema_loads(self):
        self.assertIn("approval_validation_id", self.vld_schema['required_fields'])
        self.assertIn("eligibility_report_id", self.elg_schema['required_fields'])

    def test_approval_validation_blocks_when_empty(self):
        vld = build_backtest_approval_validation()
        self.assertEqual(vld['validation_status'], 'pending_human_completion')
        self.assertTrue(validate_backtest_approval_validation(vld, self.vld_schema))

    def test_approval_validation_blocks_when_explicit_approval_false(self):
        api = {"approval_input_id": "API-1", "explicit_approval_for_single_backtest": False}
        vld = build_backtest_approval_validation(approval_input_record=api)
        self.assertEqual(vld['validation_status'], 'blocked')
        self.assertIn("Explicit human approval is false.", vld['blocking_issues'])

    def test_eligibility_blocks_when_readiness_not_ready(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        rdy = {"readiness_status": "needs_more_detail"}
        elg = build_backtest_eligibility_report(strategy_candidate_record=cand, readiness_record=rdy)
        self.assertEqual(elg['eligibility_status'], 'blocked')
        self.assertIn("Readiness gate is needs_more_detail.", elg['blocking_issues'])
        self.assertTrue(validate_backtest_eligibility_report(elg, self.elg_schema))

    def test_eligibility_ready_only_when_all_pass(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        rdy = {"readiness_status": "ready_for_human_backtest_review"}
        dsd = {"decision_status": "selected_for_future_data_adapter_review"}
        btp = {"plan_status": "ready_for_human_backtest_review"}
        vld = {"validation_status": "valid_for_single_backtest_plan_review"}
        
        elg = build_backtest_eligibility_report(cand, rdy, dsd, btp, vld)
        self.assertEqual(elg['eligibility_status'], 'ready_for_future_single_backtest_execution')
        self.assertEqual(elg['blocking_issues'], ["NONE"])

    def test_unsafe_safety_flags_fails(self):
        elg = build_backtest_eligibility_report()
        elg['safety_financial_advice_generated'] = True
        with self.assertRaises(ValueError):
            validate_backtest_eligibility_report(elg, self.elg_schema)

    def test_cli_schema_check(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "backtest_eligibility_cli.py"
        result = subprocess.run([sys.executable, str(cli_path), "schema-check", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Schema Loaded", result.stdout)

if __name__ == '__main__':
    unittest.main()
