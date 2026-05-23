import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "synthetic_result_reviews"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "synthetic_result_review_schema.yaml"

def load_synthetic_result_review_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_synthetic_result_review(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    safety_rules = [
        ('real_market_data_used', False),
        ('real_strategy_logic_used', False),
        ('candidate_strategy_executed', False),
        ('acceptable_for_strategy_evaluation', False),
        ('safety_financial_advice_generated', False),
        ('safety_trading_signal_generated', False),
        ('safety_bot_logic_generated', False),
        ('safety_live_trading_logic_generated', False)
    ]
    for flag, expected in safety_rules:
        if record.get(flag) is not expected:
            raise ValueError(f"Safety violation: {flag} MUST be {expected}.")

    return True

def compute_synthetic_review_id(run_id):
    return "SRV-" + run_id.replace("SYN-", "")

def build_synthetic_result_review(synthetic_run_record, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    run_id = synthetic_run_record.get('synthetic_run_id', 'UNKNOWN')
    rev_id = compute_synthetic_review_id(run_id)
    
    # Validation checks
    syn_fixture = synthetic_run_record.get('synthetic_fixture') is True
    real_data = synthetic_run_record.get('real_market_data_used') is True
    real_logic = synthetic_run_record.get('real_strategy_logic_used') is True
    cand_exec = synthetic_run_record.get('candidate_strategy_executed') is True
    
    if real_data or real_logic or cand_exec:
        raise ValueError("Review refused: record contains real-world execution flags.")
        
    record = {
        "synthetic_review_id": rev_id,
        "linked_synthetic_run_id": run_id,
        "review_status": "valid_synthetic_plumbing_test",
        "synthetic_fixture_confirmed": syn_fixture,
        "real_market_data_used": False,
        "real_strategy_logic_used": False,
        "candidate_strategy_executed": False,
        "metrics_present": "metrics" in synthetic_run_record,
        "limitations_present": "limitations" in synthetic_run_record,
        "forbidden_interpretations_absent": True,
        "acceptable_for_engine_plumbing_validation": True,
        "acceptable_for_strategy_evaluation": False,
        "blocking_issues": ["NONE"],
        "warnings": ["Synthetic result only. No alpha evaluation permitted."],
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_synthetic_result_review(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['synthetic_review_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Review record already exists: {file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
