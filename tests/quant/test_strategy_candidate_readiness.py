import unittest
import json
import subprocess
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.strategy_candidate import (
    load_strategy_candidate_schema,
    validate_strategy_candidate,
    build_strategy_candidate_from_inputs,
    write_strategy_candidate
)
from scripts.quant.pre_backtest_readiness import (
    load_pre_backtest_readiness_schema,
    validate_pre_backtest_readiness,
    evaluate_strategy_candidate_readiness
)
from scripts.quant.backtest_handoff import (
    load_backtest_handoff_schema,
    validate_backtest_handoff,
    build_backtest_handoff_from_readiness
)

class TestQuantReadinessBundle(unittest.TestCase):
    def setUp(self):
        self.cand_schema = load_strategy_candidate_schema()
        self.rdy_schema = load_pre_backtest_readiness_schema()
        self.hof_schema = load_backtest_handoff_schema()

        self.test_dir = BASE_DIR / "scratch" / "quant_strategy_candidates"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.valid_note = self.test_dir / "test_valid_cand_note.md"
        self.valid_note.write_text("A simple, safe strategy note.")

    def tearDown(self):
        if self.valid_note.exists():
            self.valid_note.unlink()

    def test_schema_loads(self):
        self.assertIn("strategy_candidate_id", self.cand_schema['required_fields'])
        self.assertIn("readiness_id", self.rdy_schema['required_fields'])
        self.assertIn("handoff_id", self.hof_schema['required_fields'])

    def test_valid_candidate_passes(self):
        record = build_strategy_candidate_from_inputs(title="Test", note_text="Safe test.")
        self.assertTrue(validate_strategy_candidate(record, self.cand_schema))

    def test_unsafe_candidate_fails(self):
        record = build_strategy_candidate_from_inputs(title="Test", note_text="Safe test.")
        record["safety_trading_signal_generated"] = True
        with self.assertRaises(ValueError):
            validate_strategy_candidate(record, self.cand_schema)

    def test_forbidden_wording_fails(self):
        with self.assertRaisesRegex(ValueError, "Forbidden phrase found"):
            build_strategy_candidate_from_inputs(title="Test", note_text="We must do live trading now.")

    def test_readiness_incomplete_status(self):
        # Candidate has UNKNOWN for data, so readiness should be not_ready/needs_more_detail
        record = build_strategy_candidate_from_inputs(title="Test", note_text="Safe test.")
        rdy = evaluate_strategy_candidate_readiness(record)
        self.assertEqual(rdy["readiness_status"], "needs_more_detail")
        self.assertFalse(rdy["required_data_complete"])
        self.assertTrue(validate_pre_backtest_readiness(rdy, self.rdy_schema))

    def test_readiness_complete_status(self):
        record = build_strategy_candidate_from_inputs(title="Test", note_text="Safe test.")
        record["data_requirements"] = "1 min OHLCV"
        record["universe_definition"] = "SPY"
        record["timeframe_definition"] = "Intraday"
        record["feature_requirements"] = "VWAP"
        record["transaction_cost_assumptions"] = "0.005"
        record["slippage_assumptions"] = "1 tick"
        record["execution_assumptions"] = "MOC"
        record["risk_controls_required"] = "Stop loss 1%"
        record["validation_requirements"] = "OOS"
        record["known_failure_modes"] = "Trending days"
        
        rdy = evaluate_strategy_candidate_readiness(record)
        self.assertEqual(rdy["readiness_status"], "ready_for_human_backtest_review")
        self.assertTrue(rdy["required_data_complete"])

    def test_handoff_blocked_when_readiness_fails(self):
        record = build_strategy_candidate_from_inputs(title="Test", note_text="Safe test.")
        rdy = evaluate_strategy_candidate_readiness(record)
        hof = build_backtest_handoff_from_readiness(record, rdy)
        self.assertEqual(hof["handoff_status"], "blocked")
        self.assertTrue(validate_backtest_handoff(hof, self.hof_schema))

    def test_cli_schema_check(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "strategy_candidate_cli.py"
        result = subprocess.run([sys.executable, str(cli_path), "schema-check", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Schema Loaded", result.stdout)

    def test_cli_path_traversal_blocked(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "strategy_candidate_cli.py"
        result = subprocess.run([
            sys.executable, str(cli_path), "candidate-draft",
            "--note-file", "../../../Windows/System32/cmd.exe"
        ], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be within scratch/quant_strategy_candidates/", result.stdout)

if __name__ == '__main__':
    unittest.main()
