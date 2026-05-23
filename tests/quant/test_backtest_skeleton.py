import unittest
import json
import subprocess
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.backtest_plan import (
    load_backtest_plan_schema,
    validate_backtest_plan,
    build_backtest_plan_from_handoff
)
from scripts.quant.backtest_engine import (
    validate_synthetic_price_fixture,
    compute_simple_returns,
    run_synthetic_no_strategy_smoke_test,
    compute_basic_result_metrics
)
from scripts.quant.backtest_result_manifest import (
    load_backtest_result_manifest_schema,
    validate_backtest_result_manifest,
    build_synthetic_smoke_result_manifest
)

class TestQuantBacktestSkeleton(unittest.TestCase):
    def setUp(self):
        self.plan_schema = load_backtest_plan_schema()
        self.res_schema = load_backtest_result_manifest_schema()
        
        self.fixture = {
            "fixture_id": "TEST",
            "synthetic_fixture": True,
            "not_market_data": True,
            "not_strategy_result": True,
            "rows": [
                {"timestamp": "1", "close": 100.0},
                {"timestamp": "2", "close": 110.0},
                {"timestamp": "3", "close": 55.0}
            ]
        }

    def test_schemas_load(self):
        self.assertIn("backtest_plan_id", self.plan_schema['required_fields'])
        self.assertIn("result_manifest_id", self.res_schema['required_fields'])

    def test_plan_blocked_if_readiness_fails(self):
        rdy = {"readiness_id": "RDY", "readiness_status": "needs_more_detail"}
        cand = {"strategy_candidate_id": "CAN"}
        plan = build_backtest_plan_from_handoff(candidate_record=cand, readiness_record=rdy)
        self.assertEqual(plan['plan_status'], 'blocked')
        self.assertTrue(validate_backtest_plan(plan, self.plan_schema))

    def test_plan_draft_if_readiness_ready(self):
        rdy = {"readiness_id": "RDY", "readiness_status": "ready_for_human_backtest_review"}
        cand = {"strategy_candidate_id": "CAN"}
        plan = build_backtest_plan_from_handoff(candidate_record=cand, readiness_record=rdy)
        self.assertEqual(plan['plan_status'], 'draft')
        self.assertTrue(validate_backtest_plan(plan, self.plan_schema))

    def test_unsafe_plan_fails(self):
        rdy = {"readiness_id": "RDY", "readiness_status": "ready_for_human_backtest_review"}
        cand = {"strategy_candidate_id": "CAN"}
        plan = build_backtest_plan_from_handoff(candidate_record=cand, readiness_record=rdy)
        plan['safety_bot_logic_generated'] = True
        with self.assertRaises(ValueError):
            validate_backtest_plan(plan, self.plan_schema)

    def test_fixture_validates(self):
        self.assertTrue(validate_synthetic_price_fixture(self.fixture))

    def test_fixture_rejects_missing_safety_flags(self):
        bad_fixture = self.fixture.copy()
        del bad_fixture["not_strategy_result"]
        with self.assertRaises(ValueError):
             validate_synthetic_price_fixture(bad_fixture)

    def test_fixture_rejects_non_numeric_close(self):
        bad_fixture = {
            "synthetic_fixture": True, "not_market_data": True, "not_strategy_result": True,
            "rows": [{"timestamp": "1", "close": "100.0"}]
        }
        with self.assertRaises(ValueError):
             validate_synthetic_price_fixture(bad_fixture)

    def test_arithmetic_computation(self):
        returns = compute_simple_returns(self.fixture['rows'])
        self.assertAlmostEqual(returns[0], 0.1) # 100 to 110
        self.assertAlmostEqual(returns[1], -0.5) # 110 to 55

        res = run_synthetic_no_strategy_smoke_test(self.fixture['rows'], 1000)
        self.assertEqual(len(res['equity_curve']), 3)
        self.assertEqual(res['equity_curve'][-1], 550.0) # 1000 * 1.1 = 1100 * 0.5 = 550
        
        metrics = compute_basic_result_metrics(res['equity_curve'])
        self.assertAlmostEqual(metrics['total_return'], -0.45) # 1000 to 550

    def test_manifest_validates_smoke_test(self):
        res = run_synthetic_no_strategy_smoke_test(self.fixture['rows'], 1000)
        man = build_synthetic_smoke_result_manifest(res)
        self.assertEqual(man['result_status'], 'synthetic_smoke_test_only')
        self.assertTrue(validate_backtest_result_manifest(man, self.res_schema))

    def test_manifest_rejects_non_synthetic(self):
        res = run_synthetic_no_strategy_smoke_test(self.fixture['rows'], 1000)
        res['is_synthetic_fixture'] = False
        with self.assertRaisesRegex(ValueError, "non-synthetic"):
            build_synthetic_smoke_result_manifest(res)

    def test_manifest_rejects_real_strategy_logic(self):
        res = run_synthetic_no_strategy_smoke_test(self.fixture['rows'], 1000)
        man = build_synthetic_smoke_result_manifest(res)
        man['strategy_logic_used'] = True
        with self.assertRaisesRegex(ValueError, "strictly prohibited"):
            validate_backtest_result_manifest(man, self.res_schema)

if __name__ == '__main__':
    unittest.main()
