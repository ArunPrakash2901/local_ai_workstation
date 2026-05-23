import json
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "backtest_execution_preflights"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "backtest_execution_preflight_schema.yaml"

def load_backtest_execution_preflight_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_backtest_execution_preflight(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('preflight_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['preflight_status']}")
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    if record.get('execution_allowed') is not False:
         # Check all gates
         if not record.get('all_gates_valid'):
             raise ValueError("execution_allowed MUST be false unless all gates explicitly pass")

    return True

def compute_preflight_id(candidate_id):
    return "PRE-" + candidate_id.replace("CAN-", "")

def build_backtest_execution_preflight(strategy_candidate_record=None, readiness_record=None, backtest_plan_record=None, approval_validation_record=None, eligibility_report_record=None, manual_dataset_import_record=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = strategy_candidate_record.get('strategy_candidate_id', 'UNKNOWN') if strategy_candidate_record else 'UNKNOWN'
    pre_id = compute_preflight_id(cand_id)
    
    ds_val = manual_dataset_import_record.get('import_status') == 'valid_for_human_dataset_review' if manual_dataset_import_record else False
    app_val = approval_validation_record.get('validation_status') == 'valid_for_single_backtest_plan_review' if approval_validation_record else False
    elg_val = eligibility_report_record.get('eligibility_status') == 'ready_for_future_single_backtest_execution' if eligibility_report_record else False
    
    all_v = ds_val and app_val and elg_val
    
    blocking = []
    if not ds_val: blocking.append("Dataset import is invalid or missing.")
    if not app_val: blocking.append("Human approval validation failed or is missing.")
    if not elg_val: blocking.append("Master eligibility report is blocked or missing.")
    
    status = "blocked"
    # Even if all gates pass, this milestone DOES NOT grant final approved_for_execution status 
    # unless an explicit future approval exists. We stay PENDING at best.
    if all_v:
        status = "ready_for_future_single_backtest_execution"
        
    record = {
        "preflight_id": pre_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_readiness_id": readiness_record.get('readiness_id', 'UNKNOWN') if readiness_record else "UNKNOWN",
        "linked_backtest_plan_id": backtest_plan_record.get('backtest_plan_id', 'UNKNOWN') if backtest_plan_record else "UNKNOWN",
        "linked_approval_validation_id": approval_validation_record.get('approval_validation_id', 'UNKNOWN') if approval_validation_record else "UNKNOWN",
        "linked_eligibility_report_id": eligibility_report_record.get('eligibility_report_id', 'UNKNOWN') if eligibility_report_record else "UNKNOWN",
        "linked_manual_dataset_import_id": manual_dataset_import_record.get('import_id', 'UNKNOWN') if manual_dataset_import_record else "UNKNOWN",
        "preflight_status": status,
        "all_gates_valid": all_v,
        "dataset_import_valid": ds_val,
        "approval_valid": app_val,
        "eligibility_valid": elg_val,
        "backtest_runner_available": False,
        "execution_allowed": False, # Explicitly false for this milestone
        "blocking_issues": blocking if blocking else ["Backtest runner engine not available."],
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

def write_backtest_execution_preflight(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['preflight_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Preflight record already exists: {file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
