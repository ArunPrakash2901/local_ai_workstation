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
    quant_reports_summary,
    quant_artifacts_summary,
    quant_lineage_lookup
)

class TestWsQuantReportBrowser(unittest.TestCase):

    def test_quant_reports_summary(self):
        summary = quant_reports_summary()
        self.assertIn("latest_report", summary)
        self.assertIn("report_phases", summary)
        self.assertIn("all_q_reports", summary)
        # Verify grouping
        self.assertIsInstance(summary["report_phases"]["planning"], list)
        self.assertIsInstance(summary["report_phases"]["operator_commands"], list)

    def test_quant_artifacts_summary(self):
        summary = quant_artifacts_summary()
        self.assertIn("research_ideas", summary)
        self.assertIn("strategy_candidates", summary)
        self.assertFalse(summary["real_backtest_enabled"])
        self.assertFalse(summary["approval_granted"])
        for k, v in summary.items():
            if isinstance(v, dict):
                self.assertIn("count", v)

    def test_quant_lineage_lookup_valid(self):
        # We know RI-98e3264573b3 exists from research
        lineage = quant_lineage_lookup("RI-98e3264573b3")
        self.assertEqual(lineage["artifact_id"], "RI-98e3264573b3")
        self.assertEqual(lineage["artifact_type"], "research_idea")
        self.assertEqual(lineage["status"], "needs_human_review")

    def test_quant_lineage_lookup_not_found(self):
        lineage = quant_lineage_lookup("RI-NONEXISTENT")
        self.assertEqual(lineage["status"], "NOT_FOUND")

    def test_quant_lineage_lookup_invalid_prefix(self):
        lineage = quant_lineage_lookup("INVALID-123")
        self.assertEqual(lineage["status"], "NOT_FOUND")
        self.assertEqual(lineage["reason"], "Invalid ID prefix")

    def test_quant_lineage_lookup_chain(self):
        # SYN-f30f839cbcb1 links to CAN-951be4d5c93a-R3
        lineage = quant_lineage_lookup("SYN-f30f839cbcb1")
        self.assertIn("CAN-951be4d5c93a-R3", lineage["parents"])

if __name__ == "__main__":
    unittest.main()
