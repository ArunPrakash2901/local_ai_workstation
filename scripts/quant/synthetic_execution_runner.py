import json
import hashlib
import csv
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "synthetic_execution_runs"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "synthetic_execution_run_schema.yaml"

def load_synthetic_execution_run_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_synthetic_execution_run(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    safety_rules = [
        ('synthetic_fixture', True),
        ('real_market_data_used', False),
        ('real_strategy_logic_used', False),
        ('candidate_strategy_executed', False),
        ('execution_allowed_for_real_candidate', False),
        ('safety_financial_advice_generated', False),
        ('safety_trading_signal_generated', False),
        ('safety_bot_logic_generated', False),
        ('safety_live_trading_logic_generated', False)
    ]
    for flag, expected in safety_rules:
        if record.get(flag) is not expected:
            raise ValueError(f"Safety violation: {flag} MUST be {expected}.")

    return True

def load_synthetic_csv_fixture(path_str, max_size_bytes=1048576):
    path = Path(path_str)
    if not path.is_absolute():
        path = (BASE_DIR / path_str).resolve()
    
    if (BASE_DIR / "scratch" / "quant_data_imports").resolve() not in path.parents:
         raise ValueError(f"Fixture must be within scratch/quant_data_imports/. Got: {path_str}")

    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path_str}")

    if path.stat().st_size > max_size_bytes:
        raise ValueError(f"Fixture too large.")

    rows = []
    with open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            
    return rows

def run_synthetic_execution_simulation(rows, initial_capital=10000):
    # Deterministic toy exposure rule: passive long synthetic fixture
    # This just computes the equity curve from price returns
    
    equity_curve = [initial_capital]
    for i in range(1, len(rows)):
        prev_close = float(rows[i-1]['close'])
        curr_close = float(rows[i]['close'])
        ret = (curr_close - prev_close) / prev_close
        equity_curve.append(equity_curve[-1] * (1 + ret))
        
    final_equity = equity_curve[-1]
    total_ret = (final_equity - initial_capital) / initial_capital
    
    return {
        "equity_curve": equity_curve,
        "metrics": {
            "total_return": total_ret,
            "final_equity": final_equity
        }
    }

def compute_synthetic_run_id(candidate_id, fixture_path):
    combined = f"{candidate_id}_{fixture_path}_{datetime.now(timezone.utc).isoformat()}".encode('utf-8')
    return "SYN-" + hashlib.sha256(combined).hexdigest()[:12]

def build_synthetic_execution_run(candidate_record=None, fixture_path=None, preflight_record=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = candidate_record.get('strategy_candidate_id', 'UNKNOWN') if candidate_record else 'UNKNOWN'
    pre_id = preflight_record.get('preflight_id', 'UNKNOWN') if preflight_record else 'UNKNOWN'
    imp_id = preflight_record.get('linked_manual_dataset_import_id', 'UNKNOWN') if preflight_record else 'UNKNOWN'
    
    run_id = compute_synthetic_run_id(cand_id, fixture_path)
    
    rows = load_synthetic_csv_fixture(fixture_path)
    sim_result = run_synthetic_execution_simulation(rows)
    
    record = {
        "synthetic_run_id": run_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_manual_dataset_import_id": imp_id,
        "linked_preflight_id": pre_id,
        "run_status": "synthetic_smoke_test_only",
        "synthetic_fixture": True,
        "real_market_data_used": False,
        "real_strategy_logic_used": False,
        "candidate_strategy_executed": False,
        "execution_allowed_for_real_candidate": False,
        "input_fixture_path": str(fixture_path),
        "row_count": len(rows),
        "columns_used": list(rows[0].keys()) if rows else [],
        "initial_capital": 10000,
        "toy_exposure_rule": "passive long synthetic fixture for arithmetic validation",
        "equity_curve": sim_result["equity_curve"],
        "metrics": sim_result["metrics"],
        "limitations": "Synthetic arithmetic only. Not a performance result.",
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_synthetic_execution_run(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['synthetic_run_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Run record already exists: {file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
