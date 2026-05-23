import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "backtest_results"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "backtest_result_manifest_schema.yaml"

def load_backtest_result_manifest_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_backtest_result_manifest(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('result_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['result_status']}")
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    if record.get('synthetic_fixture') and not record.get('backtest_run'):
        # It's a valid combination if we just didn't run it
        pass
    elif record.get('backtest_run'):
        if not record.get('synthetic_fixture') or record.get('strategy_logic_used'):
             raise ValueError("Real backtests and strategy logic are strictly prohibited in this milestone.")

    return True

def compute_result_manifest_id(plan_id):
    if plan_id == "UNKNOWN":
        return "RES-UNKNOWN-" + datetime.now().strftime("%Y%m%d%H%M%S")
    return "RES-" + plan_id.replace("BTP-", "")

def build_synthetic_smoke_result_manifest(smoke_result, backtest_plan_record=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    plan_id = backtest_plan_record['backtest_plan_id'] if backtest_plan_record else "UNKNOWN"
    cand_id = backtest_plan_record['linked_strategy_candidate_id'] if backtest_plan_record else "UNKNOWN"
    
    res_id = compute_result_manifest_id(plan_id)
    
    if not smoke_result.get("is_synthetic_fixture"):
        raise ValueError("Refusing to build manifest for non-synthetic smoke result.")
        
    record = {
        "result_manifest_id": res_id,
        "linked_backtest_plan_id": plan_id,
        "linked_strategy_candidate_id": cand_id,
        "result_status": "synthetic_smoke_test_only",
        "data_source_type": "synthetic_fixture",
        "synthetic_fixture": True,
        "backtest_run": True,
        "strategy_logic_used": False,
        "metrics": smoke_result.get("metrics", {}),
        "artifacts": ["none"],
        "limitations": "This is a synthetic mathematical smoke test only. No strategy logic was used.",
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_backtest_result_manifest(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['result_manifest_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Result Manifest already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
