import unittest
import json
import os
import shutil
import datetime
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repo_context_lane.tools import (
    inventory, graphify_plan, summarize, context_packet, 
    packet_review, context_handoff, graphify_plan_review, 
    graphify_run, graphify_intake, status, audit_repo_context_lane
)

class TestRepoContextLane(unittest.TestCase):
    def setUp(self):
        self.test_root = Path("scratch") / f"test_repo_context_lane_root_{uuid.uuid4().hex}"
        self.test_root.mkdir(parents=True, exist_ok=True)
        
        self.output_root = self.test_root / "lane_output"
        self.output_root.mkdir(parents=True, exist_ok=True)
        
        self.project_path = (self.test_root / "test_project").resolve()
        self.project_path.mkdir(parents=True, exist_ok=True)
        (self.project_path / "src").mkdir(parents=True, exist_ok=True)
        (self.project_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
        (self.project_path / "README.md").write_text("test project", encoding="utf-8")
        (self.project_path / ".graphifyignore").write_text("node_modules", encoding="utf-8")

    def tearDown(self):
        if self.test_root.exists():
            shutil.rmtree(self.test_root)

    def write_artifact(self, folder, filename, data):
        path = self.output_root / folder / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    def test_inventory_basic(self):
        result = inventory.run_inventory(self.project_path, self.output_root, dry_run=False)
        self.assertEqual(result["project_id"], "test_project")
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

    def test_packet_review_and_approve(self):
        project_id = "test_project"
        inv_path = self.output_root / "project_inventories" / f"{project_id}_inventory.json"
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(inv_path, "w") as f:
            json.dump({"project_id": project_id, "stats": {}}, f)
        packet_data = context_packet.generate_packet(project_id, "test_task", self.output_root, dry_run=False)
        packet_path = self.output_root / "context_packets" / list((self.output_root / "context_packets").glob("*.json"))[0].name
        
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

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_graphify_run_basic(self, mock_exists, mock_run):
        mock_exists.return_value = True
        
        graphify_plan.generate_plan(self.project_path, self.output_root, dry_run=False)
        plan_path = self.output_root / "graphify_plans" / "test_project_plan.json"
        
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
        plan_data["approval_status"] = "APPROVED_FOR_GRAPHIFY_EXECUTION"
        plan_data["approval_scope"] = "GRAPHIFY_RUN_ONLY"
        plan_data["approved_at"] = datetime.datetime.now().isoformat()
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f)
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "graphify success"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc
        
        success, msg, manifest = graphify_run.run_graphify(plan_path, self.output_root, confirm=True)
        self.assertTrue(success)
        self.assertEqual(manifest["execution_status"], "SUCCEEDED")

    def test_graphify_intake_basic(self):
        project_id = "test_project"
        output_path = self.test_root / "graphify-results" / project_id / "graphify-out"
        output_path.mkdir(parents=True, exist_ok=True)
        graph_path = output_path / "graph.json"
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump({"nodes": [], "edges": [], "communities": []}, f)
            
        run_manifest = {
            "project_id": project_id,
            "execution_status": "SUCCEEDED",
            "graphify_executable": r"C:\Users\abi62\AppData\Roaming\Python\Python313\Scripts\graphify.exe",
            "project_path": str(self.project_path),
            "output_path": str(output_path)
        }
        run_path = self.output_root / "graphify_runs" / f"{project_id}_run.json"
        run_path.parent.mkdir(parents=True, exist_ok=True)
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(run_manifest, f)
            
        success, msg, report = graphify_intake.run_intake(run_path, self.output_root, dry_run=False)
        self.assertTrue(success)

    def test_status_basic(self):
        # 1. Create synthetic inventory
        pid = "status_test"
        self.write_artifact("project_inventories", f"{pid}_inventory.json", {"project_id": pid})
            
        # 2. Check status
        projects = status.discover_projects(self.output_root)
        self.assertIn(pid, projects)
        self.assertIsNotNone(projects[pid]["inventory"])
        self.assertIsNone(projects[pid]["plan"])
        
        # 3. Check recommendation
        rec = status.get_recommendation(pid, projects[pid])
        self.assertIn("graphify-plan", rec)
        
        # 4. Render status
        output = status.render_status(projects)
        self.assertIn(f"Project: {pid}", output)
        self.assertIn("Inventory: EXISTS", output)

    def test_status_discovers_projects_from_synthetic_artifacts(self):
        self.write_artifact("project_inventories", "inventory_only_inventory.json", {"project_id": "inventory_only"})
        self.write_artifact(
            "graphify_plans",
            "plan_only_plan.json",
            {"project_id": "plan_only", "approval_status": "NOT_APPROVED"},
        )

        projects = status.discover_projects(self.output_root)

        self.assertIn("inventory_only", projects)
        self.assertIn("plan_only", projects)
        self.assertIsNotNone(projects["inventory_only"]["inventory"])
        self.assertIsNotNone(projects["plan_only"]["plan"])

    def test_status_handles_malformed_artifacts_without_crashing(self):
        malformed_path = self.output_root / "project_inventories" / "broken_inventory.json"
        malformed_path.parent.mkdir(parents=True, exist_ok=True)
        malformed_path.write_text("{not valid json", encoding="utf-8")

        projects = status.discover_projects(self.output_root)
        output = status.render_status(projects)

        self.assertIn("broken", projects)
        self.assertTrue(projects["broken"]["warnings"])
        self.assertIn("Malformed artifact", output)

    def test_status_recommends_graphify_run_when_approved_plan_exists_without_run(self):
        pid = "approved_plan"
        self.write_artifact("project_inventories", f"{pid}_inventory.json", {"project_id": pid})
        self.write_artifact(
            "graphify_plans",
            f"{pid}_plan.json",
            {"project_id": pid, "approval_status": "APPROVED_FOR_GRAPHIFY_EXECUTION"},
        )

        projects = status.discover_projects(self.output_root)
        rec = status.get_recommendation(pid, projects[pid])

        self.assertIn("graphify-run", rec)
        self.assertIn("--confirm", rec)

    def test_status_recommends_graphify_intake_when_successful_run_exists_without_intake(self):
        pid = "successful_run"
        self.write_artifact("project_inventories", f"{pid}_inventory.json", {"project_id": pid})
        self.write_artifact(
            "graphify_plans",
            f"{pid}_plan.json",
            {"project_id": pid, "approval_status": "APPROVED_FOR_GRAPHIFY_EXECUTION"},
        )
        self.write_artifact(
            "graphify_runs",
            f"{pid}_20260525_120000.json",
            {
                "project_id": pid,
                "execution_status": "SUCCEEDED",
                "started_at": "2026-05-25T12:00:00",
            },
        )

        projects = status.discover_projects(self.output_root)
        rec = status.get_recommendation(pid, projects[pid])

        self.assertIn("graphify-intake", rec)

    def test_status_reports_handoff_ready_with_approved_packet_and_handoff(self):
        pid = "handoff_ready"
        self.write_artifact("project_inventories", f"{pid}_inventory.json", {"project_id": pid})
        self.write_artifact(
            "graphify_plans",
            f"{pid}_plan.json",
            {"project_id": pid, "approval_status": "APPROVED_FOR_GRAPHIFY_EXECUTION"},
        )
        self.write_artifact(
            "graphify_runs",
            f"{pid}_20260525_120000.json",
            {
                "project_id": pid,
                "execution_status": "SUCCEEDED",
                "started_at": "2026-05-25T12:00:00",
            },
        )
        self.write_artifact(
            "graphify_intake_reports",
            f"{pid}_20260525_121000_intake.json",
            {"project_id": pid, "intake_status": "SUCCESS", "intake_timestamp": "2026-05-25T12:10:00"},
        )
        self.write_artifact("graph_summaries", f"{pid}_summary.json", {"project_id": pid})
        packet_path = self.write_artifact(
            "context_packets",
            f"{pid}_task_20260525_122000.json",
            {
                "project_id": pid,
                "task_name": "task",
                "created_at": "2026-05-25T12:20:00",
                "human_approval_status": "APPROVED_FOR_CONTEXT_USE",
            },
        )
        self.write_artifact(
            "handoff_manifests",
            f"{pid}_task_20260525_122000_gemini.json",
            {
                "project_id": pid,
                "target_agent": "gemini",
                "source_packet": str(packet_path),
                "created_at": "2026-05-25T12:30:00",
                "execution_status": "NOT_EXECUTED",
            },
        )

        projects = status.discover_projects(self.output_root)
        output = status.render_status(projects)
        rec = status.get_recommendation(pid, projects[pid])

        self.assertIn("HANDOFF_READY", rec)
        self.assertIn("Handoffs: 1 (gemini: 1)", output)

    def test_status_project_filter(self):
        # Create two projects
        inv_dir = self.output_root / "project_inventories"
        inv_dir.mkdir(parents=True, exist_ok=True)
        with open(inv_dir / "p1_inventory.json", "w") as f:
            json.dump({"project_id": "p1"}, f)
        with open(inv_dir / "p2_inventory.json", "w") as f:
            json.dump({"project_id": "p2"}, f)
            
        projects = status.discover_projects(self.output_root, target_project_id="p1")
        self.assertIn("p1", projects)
        self.assertNotIn("p2", projects)

    def test_status_malformed_artifact(self):
        inv_dir = self.output_root / "project_inventories"
        inv_dir.mkdir(parents=True, exist_ok=True)
        # Malformed JSON
        with open(inv_dir / "bad_inventory.json", "w") as f:
            f.write("{ invalid json")
            
        projects = status.discover_projects(self.output_root)
        self.assertIn("bad", projects)
        self.assertTrue(any("Malformed artifact" in w for w in projects["bad"]["warnings"]))

    def test_freeze_report(self):
        pid = "freeze_test"
        inv_dir = self.output_root / "project_inventories"
        inv_dir.mkdir(parents=True, exist_ok=True)
        with open(inv_dir / f"{pid}_inventory.json", "w") as f:
            json.dump({"project_id": pid}, f)
            
        # Ensure REQUIRED_FOLDERS exist for audit inside freeze-report
        for folder in audit_repo_context_lane.REQUIRED_FOLDERS:
            (self.output_root / folder).mkdir(parents=True, exist_ok=True)

        projects = status.discover_projects(self.output_root)
        report_path = status.generate_freeze_report(self.output_root, projects)
        self.assertTrue(Path(report_path).exists())
        
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("# Repo Context Lane Freeze Report", content)
            self.assertIn("freeze_test", content)
            self.assertIn("FINAL STATE", content)

    def test_audit_still_passes(self):
        # Ensure REQUIRED_FOLDERS exist
        for folder in audit_repo_context_lane.REQUIRED_FOLDERS:
            (self.output_root / folder).mkdir(parents=True, exist_ok=True)
            
        audit, counts = audit_repo_context_lane.audit_lane(self.output_root)
        self.assertEqual(len(audit["errors"]), 0)

if __name__ == "__main__":
    unittest.main()
