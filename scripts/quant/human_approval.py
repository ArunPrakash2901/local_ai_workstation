import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "human_approvals"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "human_backtest_approval_schema.yaml"

def load_human_backtest_approval_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_human_backtest_approval(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('approval_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['approval_status']}")
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    if record.get('approval_status') == "approved_for_single_backtest_plan":
        raise ValueError("Cannot default to approved status. Must remain pending in this milestone.")

    return True

def compute_approval_id(candidate_id):
    return "APP-" + candidate_id.replace("CAN-", "")

def build_pending_human_backtest_approval(candidate_record=None, readiness_record=None, handoff_record=None, backtest_plan_record=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = candidate_record.get('strategy_candidate_id', 'UNKNOWN') if candidate_record else 'UNKNOWN'
    app_id = compute_approval_id(cand_id)
    
    record = {
        "approval_id": app_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_readiness_id": readiness_record.get('readiness_id', 'UNKNOWN') if readiness_record else "UNKNOWN",
        "linked_handoff_id": handoff_record.get('handoff_id', 'UNKNOWN') if handoff_record else "UNKNOWN",
        "linked_backtest_plan_id": backtest_plan_record.get('backtest_plan_id', 'UNKNOWN') if backtest_plan_record else "UNKNOWN",
        "approval_status": "pending",
        "reviewer": "UNKNOWN",
        "review_timestamp": "UNKNOWN",
        "approval_scope": "single_backtest_plan_only",
        "approval_notes": "Pending human authorization.",
        "required_conditions": ["Readiness gate must be passed", "Backtest plan must be complete"],
        "forbidden_actions": ["paper_trading", "live_trading", "strategy_execution"],
        "expires_at": "UNKNOWN",
        "human_signature_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_human_backtest_approval(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['approval_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Approval Stub already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
