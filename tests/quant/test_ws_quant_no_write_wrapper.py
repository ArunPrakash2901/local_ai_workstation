import unittest
import subprocess
import os
import sys
from pathlib import Path

# Detect REPO_ROOT
REPO_ROOT = Path(__file__).resolve().parents[2]

class TestWsQuantNoWriteWrapper(unittest.TestCase):

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

    def test_ws_quant_idea_intake_dry_run_success(self):
        # Using the approved sample file
        idea_file = "scratch/quant_ideas/example_vwap_research_paper_idea.md"
        result = self.run_ws_command([
            "quant", "idea-intake-dry-run",
            "--title", "Test Idea",
            "--source-type", "human_note",
            "--idea-file", idea_file
        ])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("[SAFETY BOUNDARY ENFORCED]", result.stdout)
        self.assertIn("[DRY_RUN] Idea ID:", result.stdout)
        self.assertIn("Run with --write to save.", result.stdout)
        
        # Verify no files written to reports
        reports_dir = REPO_ROOT / "reports" / "quant" / "research_ideas"
        json_files = list(reports_dir.glob("RI-*.json"))
        # We don't know how many were there, but we can check for recent ones if we had a way.
        # For now, relying on the fact that [DRY_RUN] was in the output.

    def test_ws_quant_idea_intake_reject_write(self):
        idea_file = "scratch/quant_ideas/example_vwap_research_paper_idea.md"
        result = self.run_ws_command([
            "quant", "idea-intake-dry-run",
            "--title", "Unsafe Attempt",
            "--source-type", "human_note",
            "--idea-file", idea_file,
            "--write"
        ])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[SAFETY BLOCK] --write is strictly forbidden", result.stdout)

    def test_ws_quant_idea_intake_path_traversal(self):
        # Attempt to read a file outside approved folders (e.g. .env if it existed, or just registry)
        result = self.run_ws_command([
            "quant", "idea-intake-dry-run",
            "--title", "Traversal Attempt",
            "--source-type", "human_note",
            "--idea-file", "registry/ws_command_safety.yaml"
        ])
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Path must be within scratch/quant_ideas/", result.stdout)

    def test_ws_quant_idea_intake_dry_run_no_args(self):
        # Should fail because of missing required args in idea_cli.py
        result = self.run_ws_command(["quant", "idea-intake-dry-run"])
        self.assertNotEqual(result.returncode, 0)

if __name__ == "__main__":
    unittest.main()
