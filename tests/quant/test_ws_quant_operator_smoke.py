import unittest
import subprocess
import os
import sys
from pathlib import Path

# Detect REPO_ROOT
REPO_ROOT = Path(__file__).resolve().parents[2]

class TestWsQuantOperatorSmoke(unittest.TestCase):

    def run_ws_command(self, args):
        cmd = ["bash", "scripts/ws"] + args
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env={**os.environ, "WS_HOME": str(REPO_ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
        )
        return result

    def assert_safety_frame(self, output):
        self.assertIn("SAFETY NOTICE: Research Only", output)
        self.assertIn("- no_real_backtest_run: true", output)
        self.assertIn("- safety_financial_advice_generated: false", output)

    def test_ws_quant_status(self):
        result = self.run_ws_command(["quant", "status"])
        self.assertEqual(result.returncode, 0)
        self.assert_safety_frame(result.stdout)
        self.assertIn("lane_status: ACTIVE_RESEARCH", result.stdout)
        self.assertIn("real_backtest_enabled: False", result.stdout)

    def test_ws_quant_dashboard(self):
        result = self.run_ws_command(["quant", "dashboard"])
        self.assertEqual(result.returncode, 0)
        self.assert_safety_frame(result.stdout)
        self.assertIn("latest_completed_milestone: Q39-Q41", result.stdout)
        self.assertIn("real_backtest_enabled: False", result.stdout)
        self.assertIn("resource_posture: CPU-only, no GPU, low RAM", result.stdout)

    def test_ws_quant_reports(self):
        result = self.run_ws_command(["quant", "reports"])
        self.assertEqual(result.returncode, 0)
        self.assert_safety_frame(result.stdout)
        self.assertIn("Latest Report:", result.stdout)
        self.assertIn("Planning:", result.stdout)
        self.assertIn("Operator Commands:", result.stdout)

    def test_ws_quant_artifacts(self):
        result = self.run_ws_command(["quant", "artifacts"])
        self.assertEqual(result.returncode, 0)
        self.assert_safety_frame(result.stdout)
        self.assertIn("Quant Artifact Counts:", result.stdout)
        self.assertIn("research_ideas:", result.stdout)

    def test_ws_quant_lineage(self):
        # Test valid lineage
        result = self.run_ws_command(["quant", "lineage", "RI-98e3264573b3"])
        self.assertEqual(result.returncode, 0)
        self.assert_safety_frame(result.stdout)
        self.assertIn("artifact_id: RI-98e3264573b3", result.stdout)
        self.assertIn("artifact_type: research_idea", result.stdout)

        # Test not found
        result = self.run_ws_command(["quant", "lineage", "RI-NONEXISTENT"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("status: NOT_FOUND", result.stdout)

    def test_ws_quant_cheatsheet(self):
        result = self.run_ws_command(["quant", "cheatsheet"])
        self.assertEqual(result.returncode, 0)
        self.assert_safety_frame(result.stdout)
        self.assertIn("Quant Operator Cheatsheet", result.stdout)
        self.assertIn("ws quant dashboard", result.stdout)

    def test_ws_quant_list_tools(self):
        result = self.run_ws_command(["quant", "list-tools"])
        self.assertEqual(result.returncode, 0)
        self.assert_safety_frame(result.stdout)
        self.assertIn("Standalone Quant Tools:", result.stdout)
        self.assertIn("WS Exposed Commands:", result.stdout)
        self.assertIn("- ws quant dashboard", result.stdout)

    def test_ws_quant_synthetic_status(self):
        result = self.run_ws_command(["quant", "synthetic-status"])
        self.assertEqual(result.returncode, 0)
        self.assert_safety_frame(result.stdout)
        self.assertIn("confirm_synthetic_only: True", result.stdout)

    def test_ws_quant_gates_status(self):
        result = self.run_ws_command(["quant", "gates-status"])
        self.assertEqual(result.returncode, 0)
        self.assert_safety_frame(result.stdout)
        self.assertIn("Real Backtest Blocked: True", result.stdout)

    def test_ws_help_quant_section(self):
        result = self.run_ws_command(["help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Quant Trading Lane (Phase 6+):", result.stdout)
        self.assertIn("quant dashboard", result.stdout)
        self.assertIn("SAFETY NOTICE: Real backtests, approvals, and data downloads are BLOCKED", result.stdout)

if __name__ == "__main__":
    unittest.main()
