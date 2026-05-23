import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "backtest_eligibility_reports"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "backtest_eligibility_report_schema.yaml"

def load_backtest_eligibility_report_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_backtest_eligibility_report(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('eligibility_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['eligibility_status']}")
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    return True

def compute_eligibility_report_id(candidate_id):
    return "ELG-" + candidate_id.replace("CAN-", "")

def build_backtest_eligibility_report(strategy_candidate_record=None, readiness_record=None, data_source_decision_record=None, backtest_plan_record=None, approval_validation_record=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = strategy_candidate_record.get('strategy_candidate_id', 'UNKNOWN') if strategy_candidate_record else 'UNKNOWN'
    elg_id = compute_eligibility_report_id(cand_id)
    
    rdy_stat = readiness_record.get('readiness_status', 'UNKNOWN') if readiness_record else 'MISSING'
    dsd_stat = data_source_decision_record.get('decision_status', 'UNKNOWN') if data_source_decision_record else 'MISSING'
    btp_stat = backtest_plan_record.get('plan_status', 'UNKNOWN') if backtest_plan_record else 'MISSING'
    vld_stat = approval_validation_record.get('validation_status', 'UNKNOWN') if approval_validation_record else 'MISSING'
    
    blocking = []
    if rdy_stat != 'ready_for_human_backtest_review': blocking.append(f"Readiness gate is {rdy_stat}.")
    if dsd_stat != 'selected_for_future_data_adapter_review': blocking.append(f"Data source gate is {dsd_stat}.")
    if btp_stat not in ['ready_for_human_backtest_review', 'draft']: blocking.append(f"Backtest plan gate is {btp_stat}.")
    if vld_stat != 'valid_for_single_backtest_plan_review': blocking.append(f"Approval validation gate is {vld_stat}.")
    
    status = "ready_for_future_single_backtest_execution" if not blocking else "blocked"
    if not blocking and vld_stat == 'pending_human_completion':
         status = "pending_human_approval"

    record = {
        "eligibility_report_id": elg_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_readiness_id": readiness_record.get('readiness_id', 'UNKNOWN') if readiness_record else 'UNKNOWN',
        "linked_data_source_decision_id": data_source_decision_record.get('data_source_decision_id', 'UNKNOWN') if data_source_decision_record else 'UNKNOWN',
        "linked_backtest_plan_id": backtest_plan_record.get('backtest_plan_id', 'UNKNOWN') if backtest_plan_record else 'UNKNOWN',
        "linked_approval_validation_id": approval_validation_record.get('approval_validation_id', 'UNKNOWN') if approval_validation_record else 'UNKNOWN',
        "eligibility_status": status,
        "readiness_status": rdy_stat,
        "data_source_status": dsd_stat,
        "backtest_plan_status": btp_stat,
        "approval_validation_status": vld_stat,
        "blocking_issues": blocking if blocking else ["NONE"],
        "allowed_next_actions": ["human_review"],
        "forbidden_next_actions": ["generate_trading_signal", "place_order", "paper_trade", "live_trade", "broker_execution"],
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_backtest_eligibility_report(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['eligibility_report_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Eligibility report already exists: {file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
