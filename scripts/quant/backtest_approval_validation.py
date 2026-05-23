import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "backtest_approval_validations"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "backtest_approval_validation_schema.yaml"

def load_backtest_approval_validation_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_backtest_approval_validation(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('validation_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['validation_status']}")
    
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

def compute_approval_validation_id(approval_input_id):
    if approval_input_id == "UNKNOWN":
        return "VLD-UNKNOWN-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return "VLD-" + approval_input_id.replace("API-", "")

def build_backtest_approval_validation(approval_input_record=None, strategy_candidate_record=None, readiness_record=None, backtest_plan_record=None, data_source_decision_record=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    api_id = approval_input_record.get('approval_input_id', 'UNKNOWN') if approval_input_record else 'UNKNOWN'
    vld_id = compute_approval_validation_id(api_id)
    
    blocking = []
    
    # 1. Approval Input checks
    exp_app = False
    rev_pres = False
    scope_val = False
    exp_val = False
    forb_abs = False
    
    if approval_input_record:
        exp_app = approval_input_record.get('explicit_approval_for_single_backtest', False)
        rev_pres = approval_input_record.get('reviewer', 'UNKNOWN') != 'UNKNOWN' and bool(approval_input_record.get('reviewer'))
        scope_val = approval_input_record.get('approved_scope') == 'single_backtest_only'
        exp_val = approval_input_record.get('expires_at', 'UNKNOWN') != 'UNKNOWN'
        
        must_forbid = ['paper_trading', 'live_trading', 'broker_execution']
        input_forb = approval_input_record.get('forbidden_actions', [])
        forb_abs = all(act in input_forb for act in must_forbid)
    else:
        blocking.append("Missing approval input artifact.")

    if not exp_app: blocking.append("Explicit human approval is false.")
    if not rev_pres: blocking.append("Reviewer is unknown or blank.")
    if not scope_val: blocking.append("Approval scope is invalid or too broad.")
    if not exp_val: blocking.append("Expiration date is missing.")
    if not forb_abs: blocking.append("Mandatory forbidden actions (trading) are missing.")

    # 2. Technical Gates
    rdy_alw = False
    btp_alw = False
    dsd_alw = False
    
    if readiness_record:
        rdy_alw = readiness_record.get('readiness_status') == 'ready_for_human_backtest_review'
    if not rdy_alw: blocking.append("Readiness gate not passed.")
        
    if backtest_plan_record:
        btp_alw = backtest_plan_record.get('plan_status') in ['ready_for_human_backtest_review', 'draft']
    if not btp_alw: blocking.append("Backtest plan is blocked or invalid.")
        
    if data_source_decision_record:
        dsd_alw = data_source_decision_record.get('decision_status') == 'selected_for_future_data_adapter_review'
    if not dsd_alw: blocking.append("Data source decision is not finalized.")

    status = "valid_for_single_backtest_plan_review" if not blocking else "blocked"
    if not approval_input_record:
        status = "pending_human_completion"

    record = {
        "approval_validation_id": vld_id,
        "linked_approval_input_id": api_id,
        "linked_strategy_candidate_id": strategy_candidate_record.get('strategy_candidate_id', 'UNKNOWN') if strategy_candidate_record else 'UNKNOWN',
        "linked_readiness_id": readiness_record.get('readiness_id', 'UNKNOWN') if readiness_record else 'UNKNOWN',
        "linked_backtest_plan_id": backtest_plan_record.get('backtest_plan_id', 'UNKNOWN') if backtest_plan_record else 'UNKNOWN',
        "validation_status": status,
        "explicit_approval_present": exp_app,
        "reviewer_present": rev_pres,
        "approval_scope_valid": scope_val,
        "expiration_valid": exp_val,
        "forbidden_actions_absent": forb_abs,
        "readiness_allows_review": rdy_alw,
        "backtest_plan_allows_review": btp_alw,
        "data_source_allows_review": dsd_alw,
        "blocking_issues": blocking if blocking else ["NONE"],
        "warnings": "NONE",
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_backtest_approval_validation(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['approval_validation_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Validation record already exists: {file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
