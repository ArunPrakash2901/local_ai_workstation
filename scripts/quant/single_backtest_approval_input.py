import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "single_backtest_approval_inputs"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "single_backtest_approval_input_schema.yaml"

def load_single_backtest_approval_input_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_single_backtest_approval_input(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('approval_input_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['approval_input_status']}")
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    if record.get('forbidden_actions'):
        must_forbid = ['paper_trading', 'live_trading', 'broker_execution']
        for act in must_forbid:
            if act not in record['forbidden_actions']:
                 raise ValueError(f"Missing mandatory forbidden action in approval input: {act}")

    return True

def parse_approval_input_note_file(path):
    path = Path(path).resolve()
    base_dir = Path(__file__).resolve().parent.parent.parent
    if (base_dir / "scratch" / "quant_approvals").resolve() not in path.parents:
         raise ValueError(f"Approval note must be within scratch/quant_approvals/. Got: {path}")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Approval note not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    bad_phrases = [r"\bpaper trading approved\b", r"\blive trading approved\b", r"\bcapital approved\b"]
    for pattern in bad_phrases:
        if re.search(pattern, content.lower()):
            raise ValueError(f"Safety violation in approval note: {pattern}")
            
    return content

def compute_approval_input_id(candidate_id):
    return "API-" + candidate_id.replace("CAN-", "")

def build_single_backtest_approval_input(candidate_record=None, readiness_record=None, data_req_record=None, mapping_record=None, decision_record=None, plan_record=None, note_text=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = candidate_record.get('strategy_candidate_id', 'UNKNOWN') if candidate_record else 'UNKNOWN'
    api_id = compute_approval_input_id(cand_id)
    
    record = {
        "approval_input_id": api_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_readiness_id": readiness_record.get('readiness_id', 'UNKNOWN') if readiness_record else "UNKNOWN",
        "linked_data_requirement_id": data_req_record.get('data_requirement_id', 'UNKNOWN') if data_req_record else "UNKNOWN",
        "linked_dataset_mapping_id": mapping_record.get('mapping_id', 'UNKNOWN') if mapping_record else "UNKNOWN",
        "linked_data_source_decision_id": decision_record.get('data_source_decision_id', 'UNKNOWN') if decision_record else "UNKNOWN",
        "linked_backtest_plan_id": plan_record.get('backtest_plan_id', 'UNKNOWN') if plan_record else "UNKNOWN",
        "approval_input_status": "draft",
        "reviewer": "UNKNOWN",
        "reviewer_statement": "UNKNOWN",
        "approved_scope": "single_backtest_only",
        "explicit_approval_for_single_backtest": False,
        "approval_conditions": ["UNKNOWN"],
        "forbidden_actions": ["paper_trading", "live_trading", "broker_execution"],
        "expires_at": "UNKNOWN",
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_single_backtest_approval_input(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['approval_input_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Approval Input already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
