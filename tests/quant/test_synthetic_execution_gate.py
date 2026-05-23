import unittest
import json
import subprocess
import csv
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.synthetic_execution_runner import (
    load_synthetic_execution_run_schema,
    validate_synthetic_execution_run,
    build_synthetic_execution_run,
    load_synthetic_csv_fixture
)
from scripts.quant.synthetic_result_review import (
    load_synthetic_result_review_schema,
    validate_synthetic_result_review,
    build_synthetic_result_review
)

class TestQuantSyntheticExecutionGate(unittest.TestCase):
    def setUp(self):
        self.run_schema = load_synthetic_execution_run_schema()
        self.rev_schema = load_synthetic_result_review_schema()
        
        self.import_dir = BASE_DIR / "scratch" / "quant_data_imports"
        self.import_dir.mkdir(parents=True, exist_ok=True)
        self.valid_csv = self.import_dir / "test_syn_valid.csv"
        with open(self.valid_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            writer.writerow(["2026-01-01", 100, 105, 95, 102, 1000])
            writer.writerow(["2026-01-02", 102, 108, 101, 105, 1100])

    def tearDown(self):
        if self.valid_csv.exists():
            self.valid_csv.unlink()

    def test_schema_loads(self):
        self.assertIn("synthetic_run_id", self.run_schema['required_fields'])
        self.assertIn("synthetic_review_id", self.rev_schema['required_fields'])

    def test_valid_synthetic_execution_passes(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        # build_synthetic_execution_run requires a real path relative to BASE_DIR or absolute
        fixture_rel = str(self.valid_csv.relative_to(BASE_DIR))
        run = build_synthetic_execution_run(cand, fixture_rel)
        self.assertTrue(validate_synthetic_execution_run(run, self.run_schema))
        self.assertFalse(run['real_market_data_used'])
        self.assertFalse(run['candidate_strategy_executed'])

    def test_synthetic_review_accepts_plumbing(self):
        run = {
            "synthetic_run_id": "SYN-1",
            "synthetic_fixture": True,
            "real_market_data_used": False,
            "real_strategy_logic_used": False,
            "candidate_strategy_executed": False,
            "metrics": {},
            "limitations": "Test"
        }
        rev = build_synthetic_result_review(run)
        self.assertTrue(rev['acceptable_for_engine_plumbing_validation'])
        self.assertFalse(rev['acceptable_for_strategy_evaluation'])
        self.assertTrue(validate_synthetic_result_review(rev, self.rev_schema))

    def test_synthetic_review_fails_if_real_logic_flag(self):
        run = {
            "synthetic_run_id": "SYN-1",
            "synthetic_fixture": True,
            "real_market_data_used": False,
            "real_strategy_logic_used": True,
            "candidate_strategy_executed": False
        }
        with self.assertRaisesRegex(ValueError, "real-world execution flags"):
            build_synthetic_result_review(run)

    def test_path_traversal_fixture_blocked(self):
        with self.assertRaisesRegex(ValueError, "within scratch/quant_data_imports"):
            load_synthetic_csv_fixture("../../../Windows/System32/cmd.exe")

    def test_cli_schema_check(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "synthetic_execution_cli.py"
        result = subprocess.run([sys.executable, str(cli_path), "schema-check", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Schema Loaded", result.stdout)

if __name__ == '__main__':
    unittest.main()
