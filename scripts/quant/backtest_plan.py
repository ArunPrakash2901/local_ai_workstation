import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "backtest_plans"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "backtest_plan_schema.yaml"

def load_backtest_plan_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_backtest_plan(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('plan_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['plan_status']}")
    
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

def compute_backtest_plan_id(handoff_id):
    if handoff_id == "UNKNOWN":
        return "BTP-UNKNOWN-" + datetime.now().strftime("%Y%m%d%H%M%S")
    return "BTP-" + handoff_id.replace("HOF-", "")

def build_backtest_plan_from_handoff(candidate_record=None, readiness_record=None, handoff_record=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    hof_id = handoff_record['handoff_id'] if handoff_record else "UNKNOWN"
    plan_id = compute_backtest_plan_id(hof_id)
    
    status = "blocked"
    if readiness_record and readiness_record.get('readiness_status') == 'ready_for_human_backtest_review':
        status = "draft"
    
    record = {
        "backtest_plan_id": plan_id,
        "linked_strategy_candidate_id": candidate_record['strategy_candidate_id'] if candidate_record else "UNKNOWN",
        "linked_readiness_id": readiness_record['readiness_id'] if readiness_record else "UNKNOWN",
        "linked_handoff_id": hof_id,
        "plan_status": status,
        "plan_scope": "UNKNOWN",
        "dataset_requirements": handoff_record.get('required_datasets', 'UNKNOWN') if handoff_record else "UNKNOWN",
        "feature_requirements": handoff_record.get('required_features', 'UNKNOWN') if handoff_record else "UNKNOWN",
        "universe_definition": candidate_record.get('universe_definition', 'UNKNOWN') if candidate_record else "UNKNOWN",
        "timeframe_definition": candidate_record.get('timeframe_definition', 'UNKNOWN') if candidate_record else "UNKNOWN",
        "initial_capital_assumption": "UNKNOWN",
        "position_sizing_assumption": candidate_record.get('position_sizing_conceptual', 'UNKNOWN') if candidate_record else "UNKNOWN",
        "cost_model": handoff_record.get('cost_model', 'UNKNOWN') if handoff_record else "UNKNOWN",
        "slippage_model": handoff_record.get('slippage_model', 'UNKNOWN') if handoff_record else "UNKNOWN",
        "execution_model": candidate_record.get('execution_assumptions', 'UNKNOWN') if candidate_record else "UNKNOWN",
        "rebalance_frequency": "UNKNOWN",
        "validation_protocol": handoff_record.get('validation_protocol', 'UNKNOWN') if handoff_record else "UNKNOWN",
        "bias_checks": handoff_record.get('bias_checks', 'UNKNOWN') if handoff_record else "UNKNOWN",
        "risk_checks": handoff_record.get('risk_checks', 'UNKNOWN') if handoff_record else "UNKNOWN",
        "expected_outputs": "UNKNOWN",
        "human_approval_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_backtest_plan(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['backtest_plan_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Plan already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
