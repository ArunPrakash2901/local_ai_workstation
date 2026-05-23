import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

from quant.ws_quant_summary import (
    quant_status_summary,
    list_quant_tools,
    synthetic_status_summary,
    gate_status_summary
)

class TestWsQuantSummary(unittest.TestCase):

    def test_quant_status_summary_safety(self):
        summary = quant_status_summary()
        self.assertFalse(summary["real_backtest_enabled"])
        self.assertFalse(summary["approval_granted"])
        self.assertFalse(summary["broker_logic_present"])
        self.assertFalse(summary["live_trading_present"])
        self.assertEqual(summary["lane_status"], "ACTIVE_RESEARCH")

    def test_list_quant_tools(self):
        tools = list_quant_tools()
        self.assertIn("ws_exposed_commands", tools)
        self.assertIn("status", tools["ws_exposed_commands"])
        self.assertIn("list-tools", tools["ws_exposed_commands"])
        # Check if it found some standalone scripts (assuming they exist in the repo)
        self.assertIsInstance(tools["standalone_scripts"], list)

    def test_synthetic_status_summary_handles_missing(self):
        # Even if artifacts are missing, it should return a dictionary
        summary = synthetic_status_summary()
        self.assertIn("synthetic_execution_artifact_exists", summary)
        self.assertTrue(summary["confirm_synthetic_only"])
        self.assertTrue(summary["confirm_not_strategy_evaluation"])

    def test_gate_status_summary_safety(self):
        summary = gate_status_summary()
        self.assertTrue(summary["real_backtest_blocked"])
        self.assertIn("gates", summary)
        for gate, status in summary["gates"].items():
            self.assertIn(status, ["PASS", "UNKNOWN"])

    @patch('quant.ws_quant_summary.REPO_ROOT')
    def test_gate_status_summary_all_pass_still_blocked(self, mock_repo_root):
        # Mocking get_report_count to return > 0 for all gates
        with patch('quant.ws_quant_summary.get_report_count', return_value=1):
            summary = gate_status_summary()
            self.assertEqual(summary["gates"]["readiness"], "PASS")
            self.assertEqual(summary["gates"]["eligibility"], "PASS")
            self.assertEqual(summary["gates"]["preflight"], "PASS")
            self.assertEqual(summary["gates"]["approval_validation"], "PASS")
            # Should STILL be blocked in this milestone
            self.assertTrue(summary["real_backtest_blocked"])
            self.assertEqual(summary["block_reason"], "Real backtest execution not yet implemented/authorized")

if __name__ == "__main__":
    unittest.main()
