import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "dataset_mapping_stubs"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "dataset_mapping_stub_schema.yaml"

def load_dataset_mapping_stub_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_dataset_mapping_stub(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('mapping_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['mapping_status']}")
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    if not record.get('proposed_local_dataset_path') or record.get('proposed_local_dataset_path') == 'UNKNOWN':
        if record.get('local_file_exists') is not False:
            raise ValueError("If local dataset path is missing, local_file_exists must be false.")

    return True

def compute_mapping_id(data_req_id):
    return "MAP-" + data_req_id.replace("DTR-", "")

def build_dataset_mapping_stub(data_requirement_record, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    dtr_id = data_requirement_record.get('data_requirement_id', 'UNKNOWN')
    cand_id = data_requirement_record.get('linked_strategy_candidate_id', 'UNKNOWN')
    map_id = compute_mapping_id(dtr_id)
    
    dataset = data_requirement_record.get('required_datasets', 'UNKNOWN')
    
    # We do not attempt to find real data paths yet.
    record = {
        "mapping_id": map_id,
        "linked_data_requirement_id": dtr_id,
        "linked_strategy_candidate_id": cand_id,
        "mapping_status": "needs_source_decision",
        "required_dataset": dataset,
        "proposed_local_dataset_path": "UNKNOWN",
        "proposed_source_name": "UNKNOWN",
        "source_status": "UNKNOWN",
        "local_file_exists": False,
        "schema_known": "UNKNOWN",
        "freshness_known": "UNKNOWN",
        "data_quality_known": "UNKNOWN",
        "gaps": "Manual dataset mapping required.",
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_dataset_mapping_stub(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['mapping_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Dataset Mapping Stub already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
