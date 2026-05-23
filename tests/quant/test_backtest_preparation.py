import unittest
import json
import subprocess
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.backtest_data_requirements import (
    load_backtest_data_requirement_schema,
    validate_backtest_data_requirement,
    build_backtest_data_requirement
)
from scripts.quant.dataset_mapping_stub import (
    load_dataset_mapping_stub_schema,
    validate_dataset_mapping_stub,
    build_dataset_mapping_stub
)
from scripts.quant.human_backtest_decision import (
    load_human_backtest_decision_packet_schema,
    validate_human_backtest_decision_packet,
    build_human_backtest_decision_packet
)

class TestQuantBacktestPreparation(unittest.TestCase):
    def setUp(self):
        self.dr_schema = load_backtest_data_requirement_schema()
        self.dm_schema = load_dataset_mapping_stub_schema()
        self.dp_schema = load_human_backtest_decision_packet_schema()

    def test_schema_loads(self):
        self.assertIn("data_requirement_id", self.dr_schema['required_fields'])
        self.assertIn("mapping_id", self.dm_schema['required_fields'])
        self.assertIn("decision_packet_id", self.dp_schema['required_fields'])

    def test_data_requirement_blocked_if_unknowns(self):
        cand = {"strategy_candidate_id": "CAN-1", "data_requirements": "UNKNOWN", "universe_definition": "SPY", "timeframe_definition": "1m"}
        rdy = {"readiness_id": "RDY-1"}
        dtr = build_backtest_data_requirement(cand, rdy)
        self.assertEqual(dtr['requirement_status'], 'blocked_missing_candidate_detail')
        self.assertTrue(validate_backtest_data_requirement(dtr, self.dr_schema))

    def test_data_requirement_ready(self):
        cand = {"strategy_candidate_id": "CAN-1", "data_requirements": "OHLCV", "universe_definition": "SPY", "timeframe_definition": "1m"}
        rdy = {"readiness_id": "RDY-1"}
        dtr = build_backtest_data_requirement(cand, rdy)
        self.assertEqual(dtr['requirement_status'], 'needs_data_mapping')
        self.assertTrue(validate_backtest_data_requirement(dtr, self.dr_schema))

    def test_dataset_mapping_invalid_path_fails(self):
        dtr = {"data_requirement_id": "DTR-1", "linked_strategy_candidate_id": "CAN-1"}
        map_rec = build_dataset_mapping_stub(dtr)
        map_rec['proposed_local_dataset_path'] = "UNKNOWN"
        map_rec['local_file_exists'] = True
        with self.assertRaisesRegex(ValueError, "must be false"):
            validate_dataset_mapping_stub(map_rec, self.dm_schema)

    def test_decision_packet_blocked(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        rdy = {"readiness_id": "RDY-1", "readiness_status": "needs_more_detail"}
        dtr = {"data_requirement_id": "DTR-1"}
        map_rec = {"mapping_id": "MAP-1", "mapping_status": "needs_source_decision"}
        
        dec = build_human_backtest_decision_packet(cand, rdy, dtr, map_rec)
        self.assertEqual(dec['decision_status'], 'blocked')
        self.assertIn("Readiness gate not passed.", dec['blocking_issues'])
        self.assertIn("Dataset mapping not ready.", dec['blocking_issues'])
        self.assertTrue(validate_human_backtest_decision_packet(dec, self.dp_schema))

    def test_decision_packet_cannot_auto_approve(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        rdy = {"readiness_id": "RDY-1", "readiness_status": "ready_for_human_backtest_review"}
        dtr = {"data_requirement_id": "DTR-1"}
        map_rec = {"mapping_id": "MAP-1", "mapping_status": "ready_for_human_dataset_review"}
        
        dec = build_human_backtest_decision_packet(cand, rdy, dtr, map_rec)
        self.assertEqual(dec['decision_status'], 'pending_human_review')
        self.assertTrue(validate_human_backtest_decision_packet(dec, self.dp_schema))
        
        dec['decision_status'] = "approved_for_single_backtest_plan"
        with self.assertRaisesRegex(ValueError, "Cannot auto-approve"):
             validate_human_backtest_decision_packet(dec, self.dp_schema)

    def test_unsafe_safety_flags_fails(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        rdy = {"readiness_id": "RDY-1"}
        dtr = build_backtest_data_requirement(cand, rdy)
        dtr['safety_bot_logic_generated'] = True
        with self.assertRaises(ValueError):
            validate_backtest_data_requirement(dtr, self.dr_schema)

    def test_cli_schema_check(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "backtest_preparation_cli.py"
        result = subprocess.run([sys.executable, str(cli_path), "schema-check", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Schema Loaded", result.stdout)

if __name__ == '__main__':
    unittest.main()
