import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "backtest_data_requirements"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "backtest_data_requirement_schema.yaml"

def load_backtest_data_requirement_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_backtest_data_requirement(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('requirement_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['requirement_status']}")
    
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

def compute_data_requirement_id(candidate_id):
    return "DTR-" + candidate_id.replace("CAN-", "")

def build_backtest_data_requirement(candidate_record, readiness_record=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = candidate_record.get('strategy_candidate_id', 'UNKNOWN')
    dtr_id = compute_data_requirement_id(cand_id)
    
    rdy_id = readiness_record.get('readiness_id', 'UNKNOWN') if readiness_record else 'UNKNOWN'
    
    # Extract fields from candidate
    dataset = candidate_record.get('data_requirements', 'UNKNOWN')
    universe = candidate_record.get('universe_definition', 'UNKNOWN')
    timeframe = candidate_record.get('timeframe_definition', 'UNKNOWN')
    
    status = "needs_data_mapping"
    if dataset == "UNKNOWN" or universe == "UNKNOWN" or timeframe == "UNKNOWN":
        status = "blocked_missing_candidate_detail"
        
    record = {
        "data_requirement_id": dtr_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_readiness_id": rdy_id,
        "requirement_status": status,
        "required_datasets": dataset,
        "required_columns": "UNKNOWN",
        "required_frequency": timeframe,
        "required_time_range": "UNKNOWN",
        "required_universe": universe,
        "corporate_actions_required": "UNKNOWN",
        "adjusted_prices_required": "UNKNOWN",
        "volume_required": "UNKNOWN",
        "transaction_cost_data_required": "UNKNOWN",
        "slippage_assumption_required": "UNKNOWN",
        "benchmark_required": "UNKNOWN",
        "data_quality_checks": "UNKNOWN",
        "missing_data_policy": "UNKNOWN",
        "survivorship_bias_policy": "UNKNOWN",
        "lookahead_bias_policy": "UNKNOWN",
        "timezone_calendar_requirements": "UNKNOWN",
        "known_gaps": "Extracted from candidate draft.",
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_backtest_data_requirement(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['data_requirement_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Data Requirement already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
