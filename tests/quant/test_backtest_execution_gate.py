import unittest
import json
import subprocess
import csv
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from scripts.quant.candidate_concrete_spec import (
    load_candidate_concrete_spec_schema,
    validate_candidate_concrete_spec,
    build_candidate_concrete_spec
)
from scripts.quant.manual_dataset_import import (
    load_manual_dataset_import_schema,
    validate_manual_dataset_import,
    build_manual_dataset_import,
    inspect_local_csv_dataset
)
from scripts.quant.backtest_execution_preflight import (
    load_backtest_execution_preflight_schema,
    validate_backtest_execution_preflight,
    build_backtest_execution_preflight
)

class TestQuantBacktestExecutionGate(unittest.TestCase):
    def setUp(self):
        self.spec_schema = load_candidate_concrete_spec_schema()
        self.imp_schema = load_manual_dataset_import_schema()
        self.pf_schema = load_backtest_execution_preflight_schema()
        
        self.import_dir = BASE_DIR / "scratch" / "quant_data_imports"
        self.import_dir.mkdir(parents=True, exist_ok=True)
        self.valid_csv = self.import_dir / "test_valid.csv"
        with open(self.valid_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            writer.writerow(["2026-01-01", 100, 105, 95, 102, 1000])

    def tearDown(self):
        if self.valid_csv.exists():
            self.valid_csv.unlink()

    def test_schema_loads(self):
        self.assertIn("concrete_spec_id", self.spec_schema['required_fields'])
        self.assertIn("import_id", self.imp_schema['required_fields'])
        self.assertIn("preflight_id", self.pf_schema['required_fields'])

    def test_valid_concrete_spec_passes(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        spec = build_candidate_concrete_spec(cand, "Test spec.")
        self.assertTrue(validate_candidate_concrete_spec(spec, self.spec_schema))

    def test_unsafe_spec_note_blocked(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        with self.assertRaisesRegex(ValueError, "Forbidden phrase found"):
            build_candidate_concrete_spec(cand, "Direct buy strategy here.")

    def test_path_traversal_dataset_blocked(self):
        with self.assertRaisesRegex(ValueError, "approved directories"):
            inspect_local_csv_dataset("../../../Windows/System32/cmd.exe")

    def test_oversized_dataset_blocked(self):
        large_csv = self.import_dir / "large.csv"
        try:
            with open(large_csv, 'wb') as f:
                f.write(b"A" * (1024 * 1024 + 1)) # 1MB + 1 byte
            with self.assertRaisesRegex(ValueError, "too large"):
                inspect_local_csv_dataset(str(large_csv))
        finally:
            if large_csv.exists():
                large_csv.unlink()

    def test_synthetic_csv_validates(self):
        inspection = inspect_local_csv_dataset(str(self.valid_csv), required_columns=["close"])
        self.assertTrue(inspection["file_exists"])
        self.assertTrue(inspection["required_columns_present"])
        self.assertEqual(inspection["row_count"], 1)

    def test_missing_columns_detected(self):
        inspection = inspect_local_csv_dataset(str(self.valid_csv), required_columns=["non_existent"])
        self.assertFalse(inspection["required_columns_present"])
        self.assertIn("non_existent", inspection["missing_required_columns"])

    def test_preflight_remains_blocked(self):
        cand = {"strategy_candidate_id": "CAN-1"}
        imp = {"import_status": "draft"} # invalid
        pf = build_backtest_execution_preflight(strategy_candidate_record=cand, manual_dataset_import_record=imp)
        self.assertEqual(pf['preflight_status'], 'blocked')
        self.assertFalse(pf['execution_allowed'])
        self.assertTrue(validate_backtest_execution_preflight(pf, self.pf_schema))

    def test_cli_schema_check(self):
        cli_path = BASE_DIR / "scripts" / "quant" / "backtest_execution_gate_cli.py"
        result = subprocess.run([sys.executable, str(cli_path), "schema-check", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Schema Loaded", result.stdout)

if __name__ == '__main__':
    unittest.main()
