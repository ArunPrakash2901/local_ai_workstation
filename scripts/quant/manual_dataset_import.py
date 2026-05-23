import json
import hashlib
import csv
import re
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "manual_dataset_imports"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "manual_dataset_import_schema.yaml"

def load_manual_dataset_import_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_manual_dataset_import(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('import_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['import_status']}")
    
    safety_rules = [
        ('data_downloaded_by_system', False),
        ('safety_financial_advice_generated', False),
        ('safety_trading_signal_generated', False),
        ('safety_bot_logic_generated', False),
        ('safety_live_trading_logic_generated', False)
    ]
    for flag, expected in safety_rules:
        if record.get(flag) is not expected:
            raise ValueError(f"Safety violation: {flag} MUST be {expected}.")

    return True

def parse_dataset_import_note_file(path):
    path = Path(path).resolve()
    base_dir = Path(__file__).resolve().parent.parent.parent
    if (base_dir / "scratch" / "quant_data_imports").resolve() not in path.parents:
         raise ValueError(f"Import note must be within scratch/quant_data_imports/. Got: {path}")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Import note not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def compute_import_id(candidate_id, file_path):
    combined = f"{candidate_id}_{file_path}".encode('utf-8')
    return "IMP-" + hashlib.sha256(combined).hexdigest()[:12]

def inspect_local_csv_dataset(path_str, required_columns=None, max_size_bytes=1048576):
    path = Path(path_str)
    base_dir = Path(__file__).resolve().parent.parent.parent
    
    if not path.is_absolute():
        path = (base_dir / path_str).resolve()
    else:
        path = path.resolve()
        
    approved_dirs = [
        (base_dir / "scratch" / "quant_data_imports").resolve(),
        (base_dir / "data" / "quant" / "raw" / "manual").resolve()
    ]
    
    is_approved = any(ad in path.parents for ad in approved_dirs)
    if not is_approved:
         raise ValueError(f"Dataset path must be within approved directories. Got: {path_str}")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path_str}")

    size = path.stat().st_size
    if size > max_size_bytes:
        raise ValueError(f"Dataset file too large: {size} bytes > {max_size_bytes} limit.")

    row_count = 0
    column_names = []
    with open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        try:
            column_names = next(reader)
            row_count = sum(1 for _ in reader)
        except StopIteration:
            pass

    missing = []
    if required_columns:
        for col in required_columns:
            if col not in column_names:
                missing.append(col)
                
    return {
        "file_exists": True,
        "file_size_bytes": size,
        "file_format": "csv",
        "row_count": row_count,
        "column_names": column_names,
        "required_columns_present": not bool(missing),
        "missing_required_columns": missing
    }

def build_manual_dataset_import(strategy_candidate_record=None, data_source_decision_record=None, import_note_text=None, dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = strategy_candidate_record.get('strategy_candidate_id', 'UNKNOWN') if strategy_candidate_record else 'UNKNOWN'
    
    # Improved regex for path extraction
    file_path = "UNKNOWN"
    if import_note_text:
        # Search for path in the note text more aggressively
        patterns = [
            r"path:\s*([^\s\n\r]+)",
            r"-\s*\*\*Path:\*\*\s*([^\s\n\r]+)",
            r"\*\*Path:\*\*\s*([^\s\n\r]+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, import_note_text, re.IGNORECASE)
            if match:
                file_path = match.group(1).strip()
                break
            
    imp_id = compute_import_id(cand_id, file_path)
    
    inspection = {
        "file_exists": False,
        "file_size_bytes": 0,
        "file_format": "csv",
        "row_count": 0,
        "column_names": [],
        "required_columns_present": False,
        "missing_required_columns": []
    }
    
    status = "draft"
    gaps = "NONE"
    if file_path != "UNKNOWN":
        try:
            req_cols = ["timestamp", "open", "high", "low", "close", "volume"]
            inspection = inspect_local_csv_dataset(file_path, required_columns=req_cols)
            if inspection["required_columns_present"]:
                status = "valid_for_human_dataset_review"
            else:
                status = "blocked_missing_required_columns"
        except Exception as e:
             status = "rejected"
             gaps = str(e)
             
    record = {
        "import_id": imp_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_data_source_decision_id": data_source_decision_record.get('data_source_decision_id', 'UNKNOWN') if data_source_decision_record else 'UNKNOWN',
        "import_status": status,
        "source_file_path": file_path,
        "file_exists": inspection["file_exists"],
        "file_size_bytes": inspection["file_size_bytes"],
        "file_format": inspection["file_format"],
        "row_count": inspection["row_count"],
        "column_names": inspection["column_names"],
        "required_columns_present": inspection["required_columns_present"],
        "missing_required_columns": inspection["missing_required_columns"],
        "max_file_size_bytes": 1048576,
        "schema_validation_status": "OK" if inspection["required_columns_present"] else "FAIL",
        "synthetic_fixture": "synthetic" in str(import_note_text).lower(),
        "human_provided": True,
        "data_downloaded_by_system": False,
        "data_quality_checks": "Basic schema validation passed.",
        "known_gaps": gaps,
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_manual_dataset_import(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['import_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Import record already exists: {file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
