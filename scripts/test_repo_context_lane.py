import unittest
import json
import os
import shutil
from pathlib import Path
from repo_context_lane.tools import inventory, graphify_plan, summarize, context_packet, audit_repo_context_lane

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
        self.assertTrue((self.output_root / "project_inventories" / "test_project_inventory.md").exists())

    def test_inventory_root_drive_rejection(self):
        # On Windows, Path("D:\\") is a root drive
        root_path = Path("D:\\")
        with self.assertRaises(ValueError) as cm:
            inventory.run_inventory(root_path, self.output_root, dry_run=True)
        self.assertIn("Drive root scans are forbidden", str(cm.exception))

    def test_graphify_plan_basic(self):
        result = graphify_plan.generate_plan(self.project_path, self.output_root, dry_run=False)
        self.assertEqual(result["project_id"], "test_project")
        self.assertEqual(result["approval_status"], "NOT_APPROVED")
        self.assertIn("graphify.exe", result["proposed_command"])
        self.assertTrue((self.output_root / "graphify_plans" / "test_project_plan.json").exists())

    def test_summarize_basic(self):
        # Create a synthetic graph.json
        graph_dir = self.test_root / "graphify-results" / "test_project" / "graphify-out"
        graph_dir.mkdir(parents=True, exist_ok=True)
        graph_path = graph_dir / "graph.json"
        
        graph_data = {
            "nodes": [{"id": "main.py"}, {"id": "lib.py"}],
            "edges": [{"source": "main.py", "target": "lib.py"}],
            "communities": [{"id": 0}]
        }
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f)
            
        result = summarize.summarize_graph(graph_path, self.output_root, dry_run=False)
        self.assertEqual(result["project_id"], "test_project")
        self.assertEqual(result["counts"]["nodes"], 2)
        self.assertTrue((self.output_root / "graph_summaries" / "test_project_summary.json").exists())

    def test_audit_basic(self):
        # Run some commands to generate files
        inventory.run_inventory(self.project_path, self.output_root, dry_run=False)
        graphify_plan.generate_plan(self.project_path, self.output_root, dry_run=False)
        
        # Need to create empty required folders that weren't touched
        for folder in audit_repo_context_lane.REQUIRED_FOLDERS:
            (self.output_root / folder).mkdir(parents=True, exist_ok=True)
            
        audit, counts = audit_repo_context_lane.audit_lane(self.output_root)
        self.assertEqual(len(audit["errors"]), 0)
        self.assertEqual(counts["inventories"], 1)
        self.assertEqual(counts["plans"], 1)

    def test_packet_generation(self):
        # Create synthetic inventory and summary
        project_id = "test_project"
        inv_path = self.output_root / "project_inventories" / f"{project_id}_inventory.json"
        sum_path = self.output_root / "graph_summaries" / f"{project_id}_summary.json"
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        sum_path.parent.mkdir(parents=True, exist_ok=True)
        
        inventory_data = {
            "project_id": project_id,
            "stats": {
                "risky_folders_found": ["node_modules"],
                "heavyweight_files": [{"path": "large.bin", "size": 20000000}]
            }
        }
        with open(inv_path, "w") as f:
            json.dump(inventory_data, f)
            
        summary_data = {
            "project_id": project_id,
            "suggested_entrypoints": ["main.py"],
            "high_degree_nodes": [{"id": "utils.py", "degree": 10}]
        }
        with open(sum_path, "w") as f:
            json.dump(summary_data, f)
            
        # Run packet generation
        packet = context_packet.generate_packet(project_id, "test_task", self.output_root, dry_run=False)
        
        self.assertEqual(packet["project_id"], project_id)
        self.assertEqual(packet["human_approval_status"], "NOT_APPROVED")
        self.assertEqual(len(packet["candidates"]), 2)
        self.assertEqual(packet["candidates"][0]["path"], "main.py")
        self.assertEqual(packet["candidates"][1]["path"], "utils.py")
        self.assertIn("node_modules", packet["exclusions"]["risky_folders"])
        
        # Check files written
        packet_files = list((self.output_root / "context_packets").glob("*.json"))
        self.assertEqual(len(packet_files), 1)
        
        report_files = list((self.output_root / "review_reports").glob("*.md"))
        self.assertEqual(len(report_files), 1)

    def test_packet_missing_artifacts(self):
        # Run packet generation with no artifacts
        packet = context_packet.generate_packet("nonexistent", "test_task", self.output_root, dry_run=True)
        self.assertEqual(packet["confidence"], "LOW")
        self.assertTrue(len(packet["uncertainty"]) >= 2)
        self.assertEqual(len(packet["candidates"]), 0)

if __name__ == "__main__":
    unittest.main()
