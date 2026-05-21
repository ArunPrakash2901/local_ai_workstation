import unittest
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add scripts to sys.path
repo_root = Path(__file__).resolve().parents[2]
scripts_dir = repo_root / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from quant.paths import REPO_ROOT, quant_path, ensure_within_repo, is_approved_quant_path
from quant.contracts import load_data_contracts, load_risk_policy, SecurityError
from quant.schema import validate_ohlcv_dataset
from quant.freshness import check_freshness

class TestQuantFoundation(unittest.TestCase):

    def test_paths_safety(self):
        """Verify path safety and escape blocking."""
        self.assertEqual(REPO_ROOT, repo_root.resolve())
        
        # Approved path
        p = quant_path("data", "quant", "raw")
        self.assertTrue(is_approved_quant_path(p))
        
        # Escape attempt
        with self.assertRaises(PermissionError):
            ensure_within_repo(repo_root / "..")
            
        # Non-approved quant path
        with self.assertRaises(PermissionError):
            quant_path("scripts", "ai_ask.sh")

    def test_contract_loading(self):
        """Verify contracts can be loaded and validated."""
        data_c = load_data_contracts()
        self.assertIn("sources", data_c)
        
        risk = load_risk_policy()
        self.assertIn("limits", risk)
        self.assertFalse(risk["safety_settings"]["live_trading_allowed"])

    def test_ohlcv_validation(self):
        """Verify OHLCV schema validation."""
        valid_data = [
            {"timestamp": "2026-05-20T00:00:00", "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000}
        ]
        res = validate_ohlcv_dataset(valid_data)
        self.assertTrue(res["ok"])
        
        # Invalid: High < Low
        invalid_data = [
            {"timestamp": "2026-05-20T00:00:00", "open": 100, "high": 80, "low": 90, "close": 105, "volume": 1000}
        ]
        res = validate_ohlcv_dataset(invalid_data)
        self.assertFalse(res["ok"])
        self.assertIn("High (80) is less than Low (90)", res["errors"][0])

        # Duplicate timestamps
        dup_data = [
            {"timestamp": "2026-05-20T00:00:00", "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000},
            {"timestamp": "2026-05-20T00:00:00", "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000}
        ]
        res = validate_ohlcv_dataset(dup_data)
        self.assertFalse(res["ok"])
        self.assertIn("Duplicate timestamps detected", res["errors"])

    def test_freshness(self):
        """Verify freshness logic."""
        now = datetime.now()
        
        # Fresh (1 hour old, 24h policy)
        latest = now - timedelta(hours=1)
        res = check_freshness(latest, "max_lag_24h", current_time=now)
        self.assertTrue(res["ok"])
        self.assertFalse(res["stale"])
        
        # Stale (25 hours old, 24h policy)
        latest = now - timedelta(hours=25)
        res = check_freshness(latest, "max_lag_24h", current_time=now)
        self.assertFalse(res["ok"])
        self.assertTrue(res["stale"])

if __name__ == "__main__":
    unittest.main()
