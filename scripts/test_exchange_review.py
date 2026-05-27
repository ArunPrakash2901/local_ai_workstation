#!/usr/bin/env python3
"""Validation for Exchange Lane operator review queue commands."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
LANE_ROOT = ROOT / "exchange_lane"

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

exchange_packet = load_module("exchange_packet", LANE_ROOT / "tools" / "exchange_packet.py")
exchange_import_result = load_module("exchange_import_result", LANE_ROOT / "tools" / "exchange_import_result.py")
exchange_review = load_module("exchange_review", LANE_ROOT / "tools" / "exchange_review.py")


class TestExchangeReview(unittest.TestCase):
    def setUp(self):
        self.tmp_root = ROOT / "test_exchange_review_root"
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)
        self.tmp_root.mkdir(parents=True)
        (self.tmp_root / "exchange_lane").mkdir()
        (self.tmp_root / "exchange_lane" / "result_packets").mkdir()
        (self.tmp_root / "exchange_lane" / "result_validations").mkdir()
        (self.tmp_root / "exchange_lane" / "loop_decisions").mkdir()

    def tearDown(self):
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)

    def create_result(self, result_id: str, status: str = "IMPORTED_PENDING_REVIEW"):
        data = {
            "result_id": result_id,
            "result_status": status,
            "adapter_id": "codex_cli",
            "imported_at": "2026-05-27T12:00:00Z",
            "trusted": False,
        }
        path = self.tmp_root / "exchange_lane" / "result_packets" / f"{result_id}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def create_validation(self, result_id: str, status: str = "VALIDATED_PASSED"):
        data = {
            "result_id": result_id,
            "validation_id": f"val_{result_id}",
            "validation_status": status,
        }
        path = self.tmp_root / "exchange_lane" / "result_validations" / f"val_{result_id}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def create_decision(self, result_id: str, decision: str = "COMPLETED_PENDING_DAILY_REVIEW"):
        data = {
            "result_id": result_id,
            "validation_id": f"val_{result_id}",
            "loop_decision_id": f"dec_{result_id}",
            "decision": decision,
        }
        path = self.tmp_root / "exchange_lane" / "loop_decisions" / f"dec_{result_id}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_review_list_finds_pending(self):
        self.create_result("res1")
        self.create_result("res2", status="ACCEPTED_FOR_SUMMARY")
        
        items = exchange_review.review_list(self.tmp_root / "exchange_lane")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["result_id"], "res1")
        self.assertEqual(items[0]["recommended_action"], "validate or review result")

    def test_review_list_finds_blocked_needs_operator(self):
        self.create_result("res1", status="ACCEPTED_FOR_SUMMARY")
        self.create_validation("res1")
        self.create_decision("res1", decision="BLOCKED_NEEDS_OPERATOR")
        
        items = exchange_review.review_list(self.tmp_root / "exchange_lane")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["loop_decision"], "BLOCKED_NEEDS_OPERATOR")
        self.assertEqual(items[0]["recommended_action"], "manual decision required")

    def test_review_accept_promotion(self):
        self.create_result("res1")
        root = self.tmp_root / "exchange_lane"
        
        exchange_review.review_accept(root, "res1", "summary")
        
        res = json.loads((root / "result_packets" / "res1.json").read_text(encoding="utf-8"))
        self.assertEqual(res["result_status"], "ACCEPTED_FOR_SUMMARY")
        self.assertEqual(res["promotion_status"], "VALIDATED_FOR_SUMMARY")
        self.assertEqual(res["reviewed_by"], "operator")

    def test_review_accept_refuses_without_confirm_cli(self):
        self.create_result("res1")
        root = self.tmp_root / "exchange_lane"
        
        # Test CLI side
        with contextlib.redirect_stdout(io.StringIO()):
            rc = exchange_review.main(["review-accept", "--root", str(root), "--result-id", "res1", "--scope", "summary"])
            self.assertEqual(rc, 1)

    def test_review_reject_refuses_without_confirm_cli(self):
        self.create_result("res1")
        root = self.tmp_root / "exchange_lane"
        
        # Test CLI side
        with contextlib.redirect_stdout(io.StringIO()):
            rc = exchange_review.main(["review-reject", "--root", str(root), "--result-id", "res1", "--reason", "test"])
            self.assertEqual(rc, 1)

    def test_review_reject(self):
        self.create_result("res1")
        root = self.tmp_root / "exchange_lane"
        
        exchange_review.review_reject(root, "res1", "bad output")
        
        res = json.loads((root / "result_packets" / "res1.json").read_text(encoding="utf-8"))
        self.assertEqual(res["result_status"], "REJECTED_BY_POLICY")
        self.assertEqual(res["rejection_reason"], "bad output")

    def test_review_checkpoint_writes_report(self):
        self.create_result("res1")
        root = self.tmp_root / "exchange_lane"
        
        report_path = exchange_review.review_checkpoint(root)
        self.assertTrue(report_path.exists())
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("# Exchange Review Checkpoint", content)
        self.assertIn("- IMPORTED_PENDING_REVIEW: 1", content)


if __name__ == "__main__":
    unittest.main()
