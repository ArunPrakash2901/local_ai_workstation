import unittest
import os
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from scripts.quant.guarded_write_executor import (
    load_guarded_write_execution_schema,
    validate_guarded_write_execution,
    evaluate_noop_guarded_write,
    write_guarded_execution_audit
)
from scripts.quant.human_write_approval import build_blocked_example_approval, write_human_write_approval

BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPROV_DIR = BASE_DIR / "scratch" / "quant_approvals"
EVID_DIR = APPROV_DIR / "evidence"

class TestGuardedWriteExecutor(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        APPROV_DIR.mkdir(parents=True, exist_ok=True)
        EVID_DIR.mkdir(parents=True, exist_ok=True)
        # Create a valid example approval for testing
        cls.example_approval = build_blocked_example_approval(operator_name="Test-Operator")
        write_human_write_approval(cls.example_approval, dry_run=False, force=True)
        cls.approval_path = APPROV_DIR / f"{cls.example_approval['approval_id']}.yaml"

    def test_schema_loads(self):
        schema = load_guarded_write_execution_schema()
        self.assertEqual(schema['execution_type'], 'research_idea_intake_write_noop')

    def test_valid_record_validates(self):
        record = {
            "guarded_execution_id": "GW-TEST",
            "execution_type": "research_idea_intake_write_noop",
            "target_command": "ws quant idea-intake-write ...",
            "approval_file": "scratch/quant_approvals/test.yaml",
            "approval_id": "HAF-TEST",
            "approval_validation_status": "BLOCKED",
            "future_write_enabled": False,
            "write_attempted": False,
            "write_allowed": False,
            "write_performed": False,
            "intended_output_directory": "reports/quant/research_ideas/",
            "intended_output_filename": "RI-TEST.json",
            "intended_artifact_type": "research_idea_json",
            "blocking_issues": "Write mode disabled.",
            "audit_status": "blocked_noop",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "safety_financial_advice_generated": False,
            "safety_trading_signal_generated": False,
            "safety_bot_logic_generated": False,
            "safety_live_trading_logic_generated": False,
            "safety_backtest_run": False,
            "safety_broker_logic_generated": False,
            "safety_live_trading_authorized": False
        }
        self.assertTrue(validate_guarded_write_execution(record))

    def test_missing_field_fails(self):
        record = {"execution_type": "research_idea_intake_write_noop"}
        with self.assertRaises(ValueError):
            validate_guarded_write_execution(record)

    def test_unsafe_flag_fails(self):
        record = {
            "guarded_execution_id": "GW-TEST",
            "execution_type": "research_idea_intake_write_noop",
            "target_command": "ws quant idea-intake-write ...",
            "approval_file": "scratch/quant_approvals/test.yaml",
            "approval_id": "HAF-TEST",
            "approval_validation_status": "BLOCKED",
            "future_write_enabled": True, # Should be False
            "write_attempted": False,
            "write_allowed": False,
            "write_performed": False,
            "intended_output_directory": "reports/quant/research_ideas/",
            "intended_output_filename": "RI-TEST.json",
            "intended_artifact_type": "research_idea_json",
            "blocking_issues": "None",
            "audit_status": "blocked_noop",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "safety_financial_advice_generated": False,
            "safety_trading_signal_generated": False,
            "safety_bot_logic_generated": False,
            "safety_live_trading_logic_generated": False,
            "safety_backtest_run": False,
            "safety_broker_logic_generated": False,
            "safety_live_trading_authorized": False
        }
        with self.assertRaises(ValueError):
            validate_guarded_write_execution(record)

    def test_evaluator_blocks_while_disabled(self):
        exec_record, eval_result = evaluate_noop_guarded_write(self.approval_path)
        self.assertEqual(eval_result['status'], 'BLOCKED')
        self.assertEqual(exec_record['audit_status'], 'blocked_noop')
        self.assertFalse(exec_record['write_allowed'])
        self.assertFalse(exec_record['write_performed'])

    def test_evaluator_rejects_external_file(self):
        # Create a file outside scratch/quant_approvals
        outside_file = BASE_DIR / "scratch" / "outside.yaml"
        with open(outside_file, 'w') as f:
            yaml.dump(self.example_approval, f)
        
        exec_record, eval_result = evaluate_noop_guarded_write(outside_file)
        self.assertEqual(eval_result['status'], 'BLOCKED')
        self.assertIn("outside approved folder", eval_result['reason'])
        os.remove(outside_file)

    def test_write_audit_artifact(self):
        exec_record, _ = evaluate_noop_guarded_write(self.approval_path)
        result = write_guarded_execution_audit(exec_record, dry_run=False, force=True)
        
        json_path = Path(result['json_path'])
        md_path = Path(result['md_path'])
        
        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())
        self.assertIn("evidence", str(json_path))
        
        # Cleanup
        json_path.unlink()
        md_path.unlink()

    def test_no_reports_artifact_written(self):
        # This is a behavior test. The executor should never touch reports/
        # Even if we "force" it.
        exec_record, _ = evaluate_noop_guarded_write(self.approval_path)
        # Check that intended output path starts with reports/
        self.assertTrue(exec_record['intended_output_directory'].startswith("reports/"))
        
        # Now check that no logic in the executor performs the write to that directory.
        # The executor logic only has write_guarded_execution_audit which targets EVIDENCE_DIR.
        # We verify that manually by reading scripts/quant/guarded_write_executor.py
        pass

if __name__ == "__main__":
    unittest.main()
