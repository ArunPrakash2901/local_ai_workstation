#!/usr/bin/env python3
"""Tests for Learning Review Packet Checklist State Layer v1."""

import json
import os
import shutil
import unittest
from pathlib import Path
from datetime import datetime
import subprocess
import sys

class TestLearningReviewChecklistState(unittest.TestCase):
    def setUp(self):
        self.ws_home = Path("_test_ws_home")
        if self.ws_home.exists():
            shutil.rmtree(self.ws_home)
        self.ws_home.mkdir(parents=True)
        
        self.stronghold_id = "test-stronghold"
        self.stronghold_dir = self.ws_home / "strongholds" / "learning" / self.stronghold_id
        self.stronghold_dir.mkdir(parents=True)
        
        self.packet_id = "ADV-PACKET-20260521T143413Z"
        self.packet_dir = self.stronghold_dir / "review_packets"
        self.packet_dir.mkdir(parents=True)
        self.packet_path = self.packet_dir / "20260521T143413Z_advancement_review_packet.md"
        self.packet_path.write_text(f"""# Advancement Review Packet
- Packet ID: {self.packet_id}

## 6. Required Human Checks
- [ ] Verify the learner has completed the current task.
- [ ] Verify the JSONL dataset formatting task is actually done.

## 7. Safety Boundary
""", encoding="utf-8")

        self.state_path = self.stronghold_dir / "state.json"
        self.state_path.write_text(json.dumps({
            "stronghold_id": self.stronghold_id,
            "current_state": "LOCAL_CHECKLIST_READY",
            "next_learning_task": "**Intern**: Format dataset as JSONL."
        }), encoding="utf-8")
        
        self.script_path = Path(__file__).parent / "learning_review_checklist_state.py"
        self.env = os.environ.copy()
        self.env["WS_HOME"] = str(self.ws_home.resolve())
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"

    def tearDown(self):
        if self.ws_home.exists():
            shutil.rmtree(self.ws_home)

    def run_script(self, args):
        cmd = [sys.executable, str(self.script_path), self.stronghold_id] + args
        return subprocess.run(cmd, capture_output=True, text=True, env=self.env)

    def test_no_mode_refusal(self):
        res = self.run_script(["--packet-id", self.packet_id])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Exactly one mode must be provided", res.stdout + res.stderr)

    def test_multiple_modes_refusal(self):
        res = self.run_script(["--packet-id", self.packet_id, "--dry-run-init", "--show"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Exactly one mode must be provided", res.stdout + res.stderr)

    def test_dry_run_init_no_writes(self):
        res = self.run_script(["--packet-id", self.packet_id, "--dry-run-init"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("DRY-RUN Initialization Preview", res.stdout)
        self.assertIn("1. [ ] Verify the learner has completed the current task.", res.stdout)
        
        checklist_dir = self.stronghold_dir / "review_checklists"
        self.assertFalse(checklist_dir.exists())

    def test_init_checklist_creation(self):
        res = self.run_script(["--packet-id", self.packet_id, "--init-checklist"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Checklist initialized", res.stdout)
        
        checklist_dir = self.stronghold_dir / "review_checklists"
        checklist_path = checklist_dir / f"{self.packet_id}_checklist.json"
        audit_path = checklist_dir / "checklist_audit.jsonl"
        
        self.assertTrue(checklist_path.is_file())
        self.assertTrue(audit_path.is_file())
        
        data = json.loads(checklist_path.read_text(encoding="utf-8"))
        self.assertEqual(data["packet_id"], self.packet_id)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["text"], "Verify the learner has completed the current task.")
        self.assertEqual(data["items"][0]["status"], "PENDING")
        
        audit_lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(audit_lines), 1)
        audit_data = json.loads(audit_lines[0])
        self.assertEqual(audit_data["action"], "INIT_CHECKLIST")

    def test_init_refuses_duplicate(self):
        self.run_script(["--packet-id", self.packet_id, "--init-checklist"])
        res = self.run_script(["--packet-id", self.packet_id, "--init-checklist"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Checklist state already exists", res.stdout + res.stderr)

    def test_show_no_writes(self):
        self.run_script(["--packet-id", self.packet_id, "--init-checklist"])
        
        # Capture mtime before show
        checklist_path = self.stronghold_dir / "review_checklists" / f"{self.packet_id}_checklist.json"
        mtime_before = checklist_path.stat().st_mtime
        
        res = self.run_script(["--packet-id", self.packet_id, "--show"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Checklist State for", res.stdout)
        self.assertIn("ITEM-001: [ ] Verify the learner has completed the current task.", res.stdout)
        
        mtime_after = checklist_path.stat().st_mtime
        self.assertEqual(mtime_before, mtime_after)

    def test_json_output(self):
        res = self.run_script(["--packet-id", self.packet_id, "--dry-run-init", "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "DRY_RUN")
        self.assertEqual(len(data["items"]), 2)

    def test_fallback_items(self):
        # Create a packet without a checklist section
        malformed_packet_id = "ADV-PACKET-MALFORMED"
        malformed_packet_path = self.packet_dir / "malformed_packet.md"
        malformed_packet_path.write_text(f"Packet ID: {malformed_packet_id}\nNo items here.", encoding="utf-8")
        
        res = self.run_script(["--packet-id", malformed_packet_id, "--dry-run-init", "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["item_source"], "fallback")
        self.assertGreater(len(data["items"]), 0)
        self.assertIn("Verify the learner has completed the current task.", data["items"])

    def test_non_mutation_guarantee(self):
        state_mtime = self.state_path.stat().st_mtime
        packet_mtime = self.packet_path.stat().st_mtime
        
        self.run_script(["--packet-id", self.packet_id, "--init-checklist"])
        
        self.assertEqual(state_mtime, self.state_path.stat().st_mtime)
        self.assertEqual(packet_mtime, self.packet_path.stat().st_mtime)

if __name__ == "__main__":
    unittest.main()
