import json
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "backtest_handoffs"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "backtest_handoff_manifest_schema.yaml"

def load_backtest_handoff_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_backtest_handoff(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('handoff_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['handoff_status']}")
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    if record.get('forbidden_next_actions'):
        must_forbid = ['run_backtest_without_human_approval', 'generate_trading_signal', 'place_order', 'paper_trade', 'live_trade']
        for act in must_forbid:
            if act not in record['forbidden_next_actions']:
                raise ValueError(f"Missing mandatory forbidden action: {act}")

    return True

def compute_handoff_id(strategy_candidate_id):
    return "HOF-" + strategy_candidate_id.replace("CAN-", "")

def build_backtest_handoff_from_readiness(candidate_record, readiness_record, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    hof_id = compute_handoff_id(candidate_record['strategy_candidate_id'])
    
    status = "ready_for_human_backtest_review" if readiness_record['readiness_status'] == 'ready_for_human_backtest_review' else "blocked"
    
    record = {
        "handoff_id": hof_id,
        "linked_strategy_candidate_id": candidate_record['strategy_candidate_id'],
        "linked_readiness_id": readiness_record['readiness_id'],
        "handoff_status": status,
        "intended_backtest_scope": "UNKNOWN",
        "required_datasets": candidate_record.get('data_requirements', 'UNKNOWN'),
        "required_features": candidate_record.get('feature_requirements', 'UNKNOWN'),
        "cost_model": candidate_record.get('transaction_cost_assumptions', 'UNKNOWN'),
        "slippage_model": candidate_record.get('slippage_assumptions', 'UNKNOWN'),
        "validation_protocol": candidate_record.get('validation_requirements', 'UNKNOWN'),
        "bias_checks": "UNKNOWN",
        "risk_checks": candidate_record.get('risk_controls_required', 'UNKNOWN'),
        "expected_artifacts": "UNKNOWN",
        "allowed_next_actions": ["human_review", "request_more_detail", "prepare_backtest_plan"],
        "forbidden_next_actions": ["run_backtest_without_human_approval", "generate_trading_signal", "place_order", "paper_trade", "live_trade"],
        "human_approval_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_backtest_handoff(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['handoff_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Handoff already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
