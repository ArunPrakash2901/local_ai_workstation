import json
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "pre_backtest_readiness"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "pre_backtest_readiness_schema.yaml"

def load_pre_backtest_readiness_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_pre_backtest_readiness(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('readiness_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['readiness_status']}")
    
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

def compute_readiness_id(strategy_candidate_id):
    return "RDY-" + strategy_candidate_id.replace("CAN-", "")

def evaluate_strategy_candidate_readiness(candidate_record, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    rdy_id = compute_readiness_id(candidate_record['strategy_candidate_id'])
    
    def check_def(field_value):
        return field_value != "UNKNOWN" and str(field_value).strip() != ""

    req_data = check_def(candidate_record.get('data_requirements', 'UNKNOWN'))
    univ = check_def(candidate_record.get('universe_definition', 'UNKNOWN'))
    tframe = check_def(candidate_record.get('timeframe_definition', 'UNKNOWN'))
    feats = check_def(candidate_record.get('feature_requirements', 'UNKNOWN'))
    cost = check_def(candidate_record.get('transaction_cost_assumptions', 'UNKNOWN'))
    slip = check_def(candidate_record.get('slippage_assumptions', 'UNKNOWN'))
    exec_assum = check_def(candidate_record.get('execution_assumptions', 'UNKNOWN'))
    risk = check_def(candidate_record.get('risk_controls_required', 'UNKNOWN'))
    bias = False # Manually verified later
    val = check_def(candidate_record.get('validation_requirements', 'UNKNOWN'))
    fail = check_def(candidate_record.get('known_failure_modes', 'UNKNOWN'))

    is_complete = all([req_data, univ, tframe, feats, cost, slip, exec_assum, risk, val, fail])
    status = "ready_for_human_backtest_review" if is_complete else "needs_more_detail"

    record = {
        "readiness_id": rdy_id,
        "linked_strategy_candidate_id": candidate_record['strategy_candidate_id'],
        "readiness_status": status,
        "required_data_complete": req_data,
        "universe_defined": univ,
        "timeframe_defined": tframe,
        "feature_requirements_defined": feats,
        "cost_model_defined": cost,
        "slippage_model_defined": slip,
        "execution_assumptions_defined": exec_assum,
        "risk_controls_defined": risk,
        "bias_checks_defined": bias,
        "validation_checks_defined": val,
        "failure_modes_defined": fail,
        "human_review_required": True,
        "blocking_issues": "UNKNOWN" if not is_complete else "NONE",
        "warnings": "UNKNOWN",
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_pre_backtest_readiness(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['readiness_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Readiness record already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
