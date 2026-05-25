import unittest
import json
import os
import shutil
import datetime
from pathlib import Path
from repo_context_lane.tools import inventory, graphify_plan, summarize, context_packet, packet_review, audit_repo_context_lane

class TestRepoContextLane(unittest.TestCase):
    def setUp(self):
        self.test_root = Path("test_repo_context_lane_root")
        self.test_root.mkdir(parents=True, exist_ok=True)
        
        self.output_root = self.test_root / "lane_output"
        self.output_root.mkdir(parents=True, exist_ok=True)
        
        self.project_path = self.test_root / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        (self.project_path / "src").mkdir(parents=True, exist_ok=True)
        (self.project_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
        (self.project_path / "README.md").write_text("test project", encoding="utf-8")
        (self.project_path / ".graphifyignore").write_text("node_modules", encoding="utf-8")

    def tearDown(self):
        if self.test_root.exists():
            shutil.rmtree(self.test_root)

    def test_inventory_basic(self):
        result = inventory.run_inventory(self.project_path, self.output_root, dry_run=False)
        self.assertEqual(result["project_id"], "test_project")
        self.assertEqual(result["status"], "SAFE_FOR_GRAPHIFY_PLAN")
        self.assertTrue((self.output_root / "project_inventories" / "test_project_inventory.json").exists())

    def test_graphify_plan_basic(self):
        result = graphify_plan.generate_plan(self.project_path, self.output_root, dry_run=False)
        self.assertEqual(result["project_id"], "test_project")
        self.assertTrue((self.output_root / "graphify_plans" / "test_project_plan.json").exists())

    def test_summarize_basic(self):
        graph_dir = self.test_root / "graphify-results" / "test_project" / "graphify-out"
        graph_dir.mkdir(parents=True, exist_ok=True)
        graph_path = graph_dir / "graph.json"
        graph_data = {"nodes": [{"id": "main.py"}], "edges": [], "communities": []}
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f)
        result = summarize.summarize_graph(graph_path, self.output_root, dry_run=False)
        self.assertEqual(result["project_id"], "test_project")

    def test_packet_generation(self):
        project_id = "test_project"
        inv_path = self.output_root / "project_inventories" / f"{project_id}_inventory.json"
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(inv_path, "w") as f:
            json.dump({"project_id": project_id, "stats": {}}, f)
            
        packet = context_packet.generate_packet(project_id, "test_task", self.output_root, dry_run=False)
        self.assertEqual(packet["human_approval_status"], "NOT_APPROVED")

    def test_packet_list(self):
        # Create two packets
        context_packet.generate_packet("p1", "t1", self.output_root, dry_run=False)
        context_packet.generate_packet("p2", "t2", self.output_root, dry_run=False)
        packets = packet_review.list_packets(self.output_root)
        self.assertEqual(len(packets), 2)
        self.assertEqual(packets[0]["task_name"], "t2") # reverse chron

    def test_packet_review_and_approve(self):
        project_id = "test_project"
        # 1. Generate
        inv_path = self.output_root / "project_inventories" / f"{project_id}_inventory.json"
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(inv_path, "w") as f:
            json.dump({"project_id": project_id, "stats": {}}, f)
        packet_data = context_packet.generate_packet(project_id, "test_task", self.output_root, dry_run=False)
        
        packet_files = list((self.output_root / "context_packets").glob("*.json"))
        packet_path = packet_files[0]
        
        # 2. Review
        is_valid, issues, data = packet_review.review_packet(packet_path, self.output_root)
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
        
        # 3. Approve without confirm -> fail
        success, msg, data = packet_review.approve_packet(packet_path, self.output_root, confirm=False)
        self.assertFalse(success)
        self.assertIn("requires --confirm", msg)
        
        # 4. Approve with confirm -> success
        success, msg, data = packet_review.approve_packet(packet_path, self.output_root, confirm=True)
        self.assertTrue(success)
        self.assertEqual(data["human_approval_status"], "APPROVED_FOR_CONTEXT_USE")
        self.assertEqual(data["approval_scope"], "CONTEXT_ONLY")
        self.assertIn("approved_at", data)
        
        # Verify JSON updated
        with open(packet_path, "r") as f:
            updated = json.load(f)
            self.assertEqual(updated["human_approval_status"], "APPROVED_FOR_CONTEXT_USE")

    def test_review_flags_risky(self):
        project_id = "test_project"
        inv_path = self.output_root / "project_inventories" / f"{project_id}_inventory.json"
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(inv_path, "w") as f:
            json.dump({"project_id": project_id, "stats": {}}, f)
            
        packet_data = {
            "project_id": project_id,
            "task_name": "risky_task",
            "human_approval_status": "NOT_APPROVED",
            "source_artifacts": {"inventory": str(inv_path)},
            "candidates": [
                {"path": "node_modules/lib/index.js", "reason": "mistake"},
                {"path": "secret.env", "reason": "bad"}
            ]
        }
        packet_dir = self.output_root / "context_packets"
        packet_dir.mkdir(parents=True, exist_ok=True)
        packet_path = packet_dir / "risky.json"
        with open(packet_path, "w") as f:
            json.dump(packet_data, f)
            
        is_valid, issues, data = packet_review.review_packet(packet_path, self.output_root)
        self.assertFalse(is_valid)
        self.assertEqual(len(issues), 2)
        self.assertIn("risky folder 'node_modules'", issues[0])
        self.assertIn("risky extension '.env'", issues[1])

    def test_audit_approval_validation(self):
        # Create an approved packet with missing metadata
        packet_dir = self.output_root / "context_packets"
        packet_dir.mkdir(parents=True, exist_ok=True)
        packet_path = packet_dir / "bad_approval.json"
        
        packet_data = {
            "project_id": "p1",
            "task_name": "t1",
            "human_approval_status": "APPROVED_FOR_CONTEXT_USE",
            "source_artifacts": {"inventory": "missing.json"},
            "candidates": []
        }
        with open(packet_path, "w") as f:
            json.dump(packet_data, f)
            
        # Need to create empty required folders
        for folder in audit_repo_context_lane.REQUIRED_FOLDERS:
            (self.output_root / folder).mkdir(parents=True, exist_ok=True)
            
        audit, counts = audit_repo_context_lane.audit_lane(self.output_root)
        self.assertTrue(len(audit["errors"]) > 0)
        self.assertTrue(any("Approved packet missing 'approved_at'" in e for e in audit["errors"]))
        self.assertTrue(any("Approved packet source inventory missing" in e for e in audit["errors"]))

if __name__ == "__main__":
    unittest.main()
