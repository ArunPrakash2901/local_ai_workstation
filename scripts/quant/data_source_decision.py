import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "data_source_decisions"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "data_source_decision_schema.yaml"

def load_data_source_decision_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_data_source_decision(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('decision_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['decision_status']}")
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    if record.get('local_dataset_path') and record.get('local_dataset_path') != "UNKNOWN":
        path = Path(record['local_dataset_path'])
        # Path existence check (without reading)
        if not path.is_absolute():
            # Assume repo-relative
            path = BASE_DIR / path
        if not path.exists():
            if record.get('local_file_exists') is not False:
                raise ValueError(f"local_dataset_path {record['local_dataset_path']} does not exist, but local_file_exists is not False.")
    
    return True

def parse_data_source_decision_note_file(path):
    path = Path(path).resolve()
    base_dir = Path(__file__).resolve().parent.parent.parent
    if (base_dir / "scratch" / "quant_data_sources").resolve() not in path.parents:
         raise ValueError(f"Decision note must be within scratch/quant_data_sources/. Got: {path}")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Decision note not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def compute_data_source_decision_id(candidate_id):
    return "DSD-" + candidate_id.replace("CAN-", "")

def build_data_source_decision(data_requirement_record=None, strategy_candidate_record=None, decision_note_text=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = strategy_candidate_record.get('strategy_candidate_id', 'UNKNOWN') if strategy_candidate_record else 'UNKNOWN'
    dsd_id = compute_data_source_decision_id(cand_id)
    
    dtr_id = data_requirement_record.get('data_requirement_id', 'UNKNOWN') if data_requirement_record else 'UNKNOWN'
    
    # Stub values, to be filled by human or note parser
    record = {
        "data_source_decision_id": dsd_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_data_requirement_id": dtr_id,
        "decision_status": "draft",
        "candidate_data_sources": ["local_existing_dataset", "future_yfinance_adapter", "manual_csv_import"],
        "selected_data_source": "UNKNOWN",
        "selected_data_source_type": "unknown",
        "api_required": False,
        "credentials_required": False,
        "download_required": False,
        "local_dataset_required": False,
        "local_dataset_path": "UNKNOWN",
        "source_limitations": "UNKNOWN",
        "licensing_notes": "UNKNOWN",
        "reliability_notes": "UNKNOWN",
        "cost_notes": "UNKNOWN",
        "reason_for_selection": "UNKNOWN",
        "reason_for_rejection_of_alternatives": "UNKNOWN",
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_data_source_decision(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['data_source_decision_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Decision record already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
