import unittest
import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add scripts to sys.path
repo_root = Path(__file__).resolve().parents[2]
scripts_dir = repo_root / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from quant.paths import quant_path, detect_repo_root
from quant.catalog import scan_catalog
from quant.analytics import detect_analytics_capabilities, profile_dataset, profile_ohlcv_rows

class TestCatalogAnalytics(unittest.TestCase):

    def setUp(self):
        self.repo_root = detect_repo_root()
        # Create a temp directory for catalog tests
        self.test_raw_dir = self.repo_root / "data" / "quant" / "raw" / "test_fixture"
        self.test_raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a dummy fixture file
        self.fixture_file = self.test_raw_dir / "test_spy.json.fixture"
        self.fixture_data = {
            "metadata": {"synthetic_fixture": True, "provider": "fixture", "symbol": "SPY", "interval": "1d"},
            "rows": [
                {"timestamp": "2026-05-20T00:00:00", "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000},
                {"timestamp": "2026-05-21T00:00:00", "open": 105, "high": 115, "low": 100, "close": 110, "volume": 1200}
            ]
        }
        with open(self.fixture_file, "w", encoding="utf-8") as f:
            json.dump(self.fixture_data, f)

    def tearDown(self):
        if self.test_raw_dir.exists():
            shutil.rmtree(self.test_raw_dir)

    def test_catalog_scans_approved_roots(self):
        """Verify catalog detects the dummy fixture."""
        catalog = scan_catalog()
        # Find our test fixture in the catalog
        found = [entry for entry in catalog if "test_fixture/test_spy.json.fixture" in entry["relative_path"]]
        self.assertTrue(len(found) >= 1)
        self.assertEqual(found[0]["format"], "json_fixture")
        self.assertTrue(found[0]["synthetic_fixture"])

    def test_analytics_capabilities(self):
        """Verify capabilities detection works."""
        caps = detect_analytics_capabilities()
        self.assertIsInstance(caps, dict)
        self.assertIn("pandas", caps)
        self.assertIn("duckdb", caps)

    def test_profile_ohlcv_rows(self):
        """Verify profiling logic for in-memory rows."""
        rows = self.fixture_data["rows"]
        profile = profile_ohlcv_rows(rows)
        
        self.assertEqual(profile["row_count"], 2)
        self.assertEqual(profile["min_timestamp"], "2026-05-20T00:00:00")
        self.assertEqual(profile["max_timestamp"], "2026-05-21T00:00:00")
        self.assertEqual(profile["numeric_ranges"]["high"]["max"], 115)
        self.assertTrue(profile["schema_validation"]["ok"])

    def test_profile_dataset_json(self):
        """Verify profiling a JSON fixture file."""
        profile = profile_dataset(self.fixture_file)
        self.assertEqual(profile["row_count"], 2)
        self.assertIn("test_spy.json.fixture", profile["path"])

    def test_profile_rejects_outside_approved_paths(self):
        """Verify profiling blocks paths outside data/quant/."""
        # Create a file in root (hypothetically, if we could)
        # We'll just test a path that exists but is outside approved roots
        outside_path = self.repo_root / "scripts" / "ws"
        profile = profile_dataset(outside_path)
        self.assertIn("errors", profile)
        self.assertIn("Path is not an approved Quant location", profile["errors"][0])

    def test_no_external_api_calls(self):
        """Verify external_api_called remains false in results."""
        # This is more of a CLI test, but we can verify our profiling logic doesn't import network libs
        import sys
        forbidden = ["yfinance", "alpaca_trade_api"]
        for mod in forbidden:
            self.assertNotIn(mod, sys.modules)

if __name__ == "__main__":
    unittest.main()
