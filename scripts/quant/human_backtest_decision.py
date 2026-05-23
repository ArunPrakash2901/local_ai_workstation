import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "human_backtest_decisions"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "human_backtest_decision_packet_schema.yaml"

def load_human_backtest_decision_packet_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_human_backtest_decision_packet(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('decision_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['decision_status']}")
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    if record.get('decision_status') == "approved_for_single_backtest_plan":
        raise ValueError("Cannot auto-approve. Must remain pending in this milestone.")

    if record.get('forbidden_next_actions'):
        must_forbid = ['generate_trading_signal', 'place_order', 'paper_trade', 'live_trade', 'broker_execution']
        for act in must_forbid:
            if act not in record['forbidden_next_actions']:
                raise ValueError(f"Missing mandatory forbidden action: {act}")

    return True

def compute_decision_packet_id(candidate_id):
    return "DEC-" + candidate_id.replace("CAN-", "")

def build_human_backtest_decision_packet(candidate_record=None, readiness_record=None, data_req_record=None, mapping_record=None, plan_record=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = candidate_record.get('strategy_candidate_id', 'UNKNOWN') if candidate_record else 'UNKNOWN'
    dec_id = compute_decision_packet_id(cand_id)
    
    status = "pending_human_review"
    blocking = []
    
    if not readiness_record or readiness_record.get('readiness_status') != 'ready_for_human_backtest_review':
        status = "blocked"
        blocking.append("Readiness gate not passed.")
        
    if not mapping_record or mapping_record.get('mapping_status') not in ['ready_for_human_dataset_review']:
        status = "blocked"
        blocking.append("Dataset mapping not ready.")
    
    record = {
        "decision_packet_id": dec_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_readiness_id": readiness_record.get('readiness_id', 'UNKNOWN') if readiness_record else 'UNKNOWN',
        "linked_data_requirement_id": data_req_record.get('data_requirement_id', 'UNKNOWN') if data_req_record else 'UNKNOWN',
        "linked_dataset_mapping_id": mapping_record.get('mapping_id', 'UNKNOWN') if mapping_record else 'UNKNOWN',
        "linked_backtest_plan_id": plan_record.get('backtest_plan_id', 'UNKNOWN') if plan_record else 'UNKNOWN',
        "decision_status": status,
        "reviewer": "UNKNOWN",
        "decision_required": "Should we invest compute resources to run this backtest?",
        "decision_options": ["approve", "reject", "defer"],
        "recommended_decision": "defer" if status == "blocked" else "UNKNOWN",
        "reasons_to_approve_later": ["If data is acquired and readiness gaps are filled."],
        "reasons_to_reject_or_defer": blocking if blocking else ["UNKNOWN"],
        "blocking_issues": blocking if blocking else ["NONE"],
        "safety_summary": "All safety flags active. No real data or execution allowed.",
        "allowed_next_actions": ["human_review"],
        "forbidden_next_actions": ["generate_trading_signal", "place_order", "paper_trade", "live_trade", "broker_execution"],
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_human_backtest_decision_packet(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['decision_packet_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Decision Packet already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
