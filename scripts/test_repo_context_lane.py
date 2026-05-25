import unittest
import json
import os
import shutil
import datetime
from pathlib import Path
from repo_context_lane.tools import inventory, graphify_plan, summarize, context_packet, packet_review, context_handoff, graphify_plan_review, audit_repo_context_lane

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
        context_packet.generate_packet("p1", "t1", self.output_root, dry_run=False)
        context_packet.generate_packet("p2", "t2", self.output_root, dry_run=False)
        packets = packet_review.list_packets(self.output_root)
        self.assertEqual(len(packets), 2)

    def test_packet_review_and_approve(self):
        project_id = "test_project"
        inv_path = self.output_root / "project_inventories" / f"{project_id}_inventory.json"
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(inv_path, "w") as f:
            json.dump({"project_id": project_id, "stats": {}}, f)
        packet_data = context_packet.generate_packet(project_id, "test_task", self.output_root, dry_run=False)
        
        packet_files = list((self.output_root / "context_packets").glob("*.json"))
        packet_path = packet_files[0]
        
        is_valid, issues, data = packet_review.review_packet(packet_path, self.output_root)
        self.assertTrue(is_valid)
        
        success, msg, data = packet_review.approve_packet(packet_path, self.output_root, confirm=True)
        self.assertTrue(success)
        self.assertEqual(data["human_approval_status"], "APPROVED_FOR_CONTEXT_USE")

    def test_handoff_basic(self):
        project_id = "test_project"
        inv_path = self.output_root / "project_inventories" / f"{project_id}_inventory.json"
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(inv_path, "w") as f:
            json.dump({"project_id": project_id, "stats": {}}, f)
        
        packet_data = context_packet.generate_packet(project_id, "test_task", self.output_root, dry_run=False)
        packet_path = self.output_root / "context_packets" / list((self.output_root / "context_packets").glob("*.json"))[0].name
        
        packet_review.approve_packet(packet_path, self.output_root, confirm=True)
        
        success, msg, manifest = context_handoff.generate_handoff(packet_path, "gemini", self.output_root, dry_run=False)
        self.assertTrue(success)
        self.assertEqual(manifest["execution_status"], "NOT_EXECUTED")

    def test_graphify_plan_review_and_approve(self):
        # 1. Generate plan
        graphify_plan.generate_plan(self.project_path, self.output_root, dry_run=False)
        plan_path = self.output_root / "graphify_plans" / "test_project_plan.json"
        
        # 2. List
        plans = graphify_plan_review.list_plans(self.output_root)
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["project_id"], "test_project")
        
        # 3. Review
        is_valid, issues, data = graphify_plan_review.review_plan(plan_path, self.output_root)
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
        
        # 4. Approve without confirm
        success, msg, data = graphify_plan_review.approve_plan(plan_path, self.output_root, confirm=False)
        self.assertFalse(success)
        
        # 5. Approve with confirm
        success, msg, data = graphify_plan_review.approve_plan(plan_path, self.output_root, confirm=True)
        self.assertTrue(success)
        self.assertEqual(data["approval_status"], "APPROVED_FOR_GRAPHIFY_EXECUTION")
        self.assertEqual(data["approval_scope"], "GRAPHIFY_RUN_ONLY")

    def test_graphify_plan_review_unsafe_scope(self):
        plan_data = {
            "project_id": "root",
            "project_path": "D:\\",
            "proposed_output_path": "D:\\graphify-results\\root\\graphify-out",
            "graphify_exe": graphify_plan.GRAPHIFY_EXE,
            "proposed_command": "dummy",
            "approval_status": "NOT_APPROVED"
        }
        plan_path = self.output_root / "graphify_plans" / "unsafe_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        with open(plan_path, "w") as f:
            json.dump(plan_data, f)
            
        is_valid, issues, data = graphify_plan_review.review_plan(plan_path, self.output_root)
        self.assertFalse(is_valid)
        self.assertTrue(any("Unsafe project scope" in i for i in issues))

    def test_graphify_plan_review_output_inside_project(self):
        p_path = self.project_path.resolve()
        plan_data = {
            "project_id": "test_project",
            "project_path": str(p_path),
            "proposed_output_path": str(p_path / "graphify-out"),
            "graphify_exe": graphify_plan.GRAPHIFY_EXE,
            "proposed_command": "dummy",
            "approval_status": "NOT_APPROVED"
        }
        plan_path = self.output_root / "graphify_plans" / "inside_output_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        with open(plan_path, "w") as f:
            json.dump(plan_data, f)
            
        is_valid, issues, data = graphify_plan_review.review_plan(plan_path, self.output_root)
        self.assertFalse(is_valid)
        self.assertTrue(any("Output path is inside project root" in i for i in issues))

    def test_audit_v05(self):
        # Create approved plan with issues
        plan_dir = self.output_root / "graphify_plans"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_path = plan_dir / "bad_plan.json"
        
        plan_data = {
            "project_id": "p1",
            "project_path": "D:\\", # Unsafe
            "proposed_output_path": "E:\\out",
            "approval_status": "APPROVED_FOR_GRAPHIFY_EXECUTION",
            # missing approved_at
        }
        with open(plan_path, "w") as f:
            json.dump(plan_data, f)
            
        # Need to create empty required folders
        for folder in audit_repo_context_lane.REQUIRED_FOLDERS:
            (self.output_root / folder).mkdir(parents=True, exist_ok=True)
            
        audit, counts = audit_repo_context_lane.audit_lane(self.output_root)
        self.assertTrue(any("Approved plan missing 'approved_at'" in e for e in audit["errors"]))
        self.assertTrue(any("Approved plan has unsafe broad project scope" in e for e in audit["errors"]))

if __name__ == "__main__":
    unittest.main()
