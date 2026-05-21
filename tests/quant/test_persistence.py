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

from quant.paths import quant_path
from quant.persistence import (
    detect_persistence_capabilities, 
    persist_ohlcv, 
    write_json_fixture
)

class TestPersistence(unittest.TestCase):

    def setUp(self):
        # Create a temp directory for persistence tests
        self.test_dir = repo_root / "data" / "quant" / "test_temp"
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        # Clean up temp directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_capability_probe(self):
        """Verify capability probe returns structured result."""
        res = detect_persistence_capabilities()
        self.assertIsInstance(res, dict)
        self.assertIn("pandas", res)
        self.assertIn("pyarrow", res)

    def test_json_fixture_write_requires_synthetic(self):
        """Verify JSON fixture write blocks when not synthetic."""
        rows = [{"timestamp": "2026-05-20", "close": 100}]
        path = self.test_dir / "test_out"
        meta = {"synthetic_fixture": False, "provider": "real", "symbol": "SPY", "interval": "1d"}
        
        res = write_json_fixture(rows, path, meta)
        self.assertFalse(res["ok"])
        self.assertIn("only permitted for synthetic data", res["error"])

    def test_persist_ohlcv_dry_run(self):
        """Verify dry-run does not write files."""
        rows = [{"timestamp": "2026-05-20", "close": 100}]
        path = quant_path("data", "quant", "raw", "test_file")
        meta = {"provider": "fixture", "symbol": "SPY", "interval": "1d"}
        
        res = persist_ohlcv(rows, path, "json_fixture", meta, dry_run=True)
        self.assertTrue(res["ok"])
        self.assertTrue(res["dry_run"])
        
        # Ensure no file was created
        self.assertFalse(path.with_suffix(".json.fixture").exists())

    def test_parquet_blocked_if_no_backend(self):
        """
        Verify Parquet blocks cleanly if backend is missing.
        Note: On this machine backend exists, so we test the 'ok' path or logic.
        """
        rows = [{"timestamp": "2026-05-20", "close": 100}]
        path = self.test_dir / "test_parquet"
        meta = {"provider": "fixture", "symbol": "SPY", "interval": "1d"}
        
        caps = detect_persistence_capabilities()
        has_parquet = caps["pandas"] and (caps["pyarrow"] or caps["fastparquet"])
        
        res = persist_ohlcv(rows, path, "parquet", meta, dry_run=False)
        
        if has_parquet:
            self.assertTrue(res["ok"])
            self.assertTrue(Path(res["written_to"]).exists())
        else:
            self.assertFalse(res["ok"])
            self.assertIn("backend (...) unavailable", res["error"])

    def test_unsupported_format_rejected(self):
        """Verify unsupported format is rejected."""
        rows = []
        path = self.test_dir / "test_fmt"
        meta = {"provider": "fixture", "symbol": "SPY", "interval": "1d"}
        
        res = persist_ohlcv(rows, path, "csv", meta, dry_run=False)
        self.assertFalse(res["ok"])
        self.assertIn("Unsupported format: csv", res["error"])

    def test_path_escape_blocked(self):
        """Verify path escape is blocked during persistence."""
        rows = []
        path = repo_root / ".." / "escaped_file"
        meta = {"provider": "fixture", "symbol": "SPY", "interval": "1d"}
        
        res = persist_ohlcv(rows, path, "json_fixture", meta, dry_run=False)
        self.assertFalse(res["ok"])
        self.assertIn("Path escape detected", res["error"])

if __name__ == "__main__":
    unittest.main()
