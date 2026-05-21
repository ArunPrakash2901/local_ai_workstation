import unittest
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add scripts to sys.path
repo_root = Path(__file__).resolve().parents[2]
scripts_dir = repo_root / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from quant.fixture_adapter import FixtureAdapter
from quant.ingest import ingest_ohlcv
from quant.schema import validate_ohlcv_dataset

class TestFixtureIngest(unittest.TestCase):

    def test_fixture_adapter_returns_deterministic_rows(self):
        """Verify fixture adapter returns expected 5 rows for SPY."""
        adapter = FixtureAdapter()
        start = datetime(2026, 5, 1)
        end = datetime(2026, 5, 30)
        data = adapter.fetch_ohlcv("SPY", start, end)
        
        self.assertEqual(len(data), 5)
        self.assertEqual(data[0]["metadata"]["provider"], "fixture")
        self.assertTrue(data[0]["metadata"]["synthetic"])

    def test_fixture_rows_pass_validation(self):
        """Verify fixture data passes schema validation."""
        adapter = FixtureAdapter()
        data = adapter.fetch_ohlcv("SPY", datetime(2026, 5, 1), datetime(2026, 5, 30))
        res = validate_ohlcv_dataset(data)
        self.assertTrue(res["ok"])

    def test_ingest_dry_run_does_not_write(self):
        """Verify dry-run does not create files."""
        adapter = FixtureAdapter()
        res = ingest_ohlcv(
            provider=adapter,
            symbol="SPY",
            start_date=datetime(2026, 5, 1),
            end_date=datetime(2026, 5, 30),
            dry_run=True,
            write_fixture=True # Should still not write because dry_run=True
        )
        self.assertTrue(res["ok"])
        self.assertIsNone(res.get("written_to"))
        
        # Check path safety
        self.assertIn("data/quant/raw/fixture/SPY.parquet", res["storage_path"].replace("\\", "/"))

    def test_unsupported_provider_rejected(self):
        """Verify unknown symbols/providers return errors or empty."""
        adapter = FixtureAdapter()
        data = adapter.fetch_ohlcv("INVALID", datetime(2026, 5, 1), datetime(2026, 5, 30))
        self.assertEqual(len(data), 0)

    def test_write_fixture_path_safety(self):
        """Verify fixture write stays under raw/ and uses correct suffix."""
        adapter = FixtureAdapter()
        # Mocking writing would require real FS or mock. 
        # For now we rely on the logic in ingest.py which we can unit test by inspecting the code.
        # But we can verify the path calculation.
        res = ingest_ohlcv(
            provider=adapter,
            symbol="SPY",
            start_date=datetime(2026, 5, 1),
            end_date=datetime(2026, 5, 30),
            dry_run=True
        )
        self.assertIn("data/quant/raw/fixture/SPY.parquet", res["storage_path"].replace("\\", "/"))

    def test_no_external_api_imports(self):
        """Ensure no common external market data APIs are imported in the quant scripts."""
        forbidden = ["yfinance", "alpaca_trade_api", "ib_insync", "polygon"]
        
        quant_scripts = list((scripts_dir / "quant").glob("*.py"))
        for script in quant_scripts:
            with open(script, "r", encoding="utf-8") as f:
                content = f.read()
                for fbd in forbidden:
                    self.assertNotIn(f"import {fbd}", content, f"Forbidden import {fbd} found in {script}")
                    self.assertNotIn(f"from {fbd}", content, f"Forbidden import {fbd} found in {script}")

if __name__ == "__main__":
    unittest.main()
