import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SPEC_DIR = BASE_DIR / "reports" / "quant" / "candidate_concrete_specs"
CANDIDATE_DIR = BASE_DIR / "reports" / "quant" / "strategy_candidates"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "candidate_concrete_spec_schema.yaml"

FORBIDDEN_PHRASES = [
    r"\bguaranteed profit\b",
    r"\blive trading\b",
    r"\breal-money execution\b",
    r"\bbroker execution\b",
    r"\bbuy advice\b",
    r"\bsell advice\b",
    r"\bhold advice\b",
    r"\bdirect buy\b",
    r"\bdirect sell\b",
    r"\bimmediate backtesting\b",
    r"\bpaper trading\b"
]

def load_candidate_concrete_spec_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_candidate_concrete_spec(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('concrete_spec_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['concrete_spec_status']}")
    
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

def check_forbidden_phrases(content):
    content = str(content).lower()
    for pattern in FORBIDDEN_PHRASES:
        if re.search(pattern, content):
            raise ValueError(f"Forbidden phrase found: matches '{pattern}'")

def parse_concrete_spec_note_file(path):
    path = Path(path).resolve()
    base_dir = Path(__file__).resolve().parent.parent.parent
    if (base_dir / "scratch" / "quant_strategy_candidates").resolve() not in path.parents:
         raise ValueError(f"Spec note must be within scratch/quant_strategy_candidates/. Got: {path}")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Spec note not found: {path}")

    if path.stat().st_size > 100 * 1024:
        raise ValueError(f"Spec note exceeds maximum allowed size of 100KB")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    check_forbidden_phrases(content)
    return content

def compute_concrete_spec_id(candidate_id, note_text):
    combined = f"{candidate_id}_{note_text}".encode('utf-8')
    return "SPC-" + hashlib.sha256(combined).hexdigest()[:12]

def build_candidate_concrete_spec(candidate_record, note_text=None, cand_path="UNKNOWN", dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    note_content = note_text if note_text else "UNKNOWN"
    check_forbidden_phrases(note_content)
    cand_id = candidate_record.get('strategy_candidate_id', 'UNKNOWN')
    spec_id = compute_concrete_spec_id(cand_id, note_content)
    
    record = {
        "concrete_spec_id": spec_id,
        "linked_strategy_candidate_id": cand_id,
        "source_candidate_file": str(cand_path),
        "concrete_spec_status": "draft",
        "concrete_universe": "UNKNOWN",
        "concrete_tickers": [],
        "concrete_timeframe": "UNKNOWN",
        "concrete_bar_frequency": "UNKNOWN",
        "concrete_required_columns": [],
        "concrete_feature_requirements": "UNKNOWN",
        "concrete_entry_logic_description": "UNKNOWN",
        "concrete_exit_logic_description": "UNKNOWN",
        "concrete_position_sizing_description": "UNKNOWN",
        "concrete_cost_model_description": "UNKNOWN",
        "concrete_slippage_model_description": "UNKNOWN",
        "concrete_execution_assumptions": "UNKNOWN",
        "concrete_validation_requirements": "UNKNOWN",
        "concrete_risk_controls": "UNKNOWN",
        "concrete_failure_modes": "UNKNOWN",
        "fields_completed": [],
        "fields_still_unknown": ["all_manually_supplied_in_note"],
        "reviewer": "OPERATOR",
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def apply_concrete_spec_to_candidate(candidate_record, concrete_spec_record, dry_run=True):
    revised = candidate_record.copy()
    orig_id = candidate_record['strategy_candidate_id']
    if "-R" in orig_id:
        base_id = orig_id.split("-R")[0]
        revised['strategy_candidate_id'] = f"{base_id}-R3"
    else:
        revised['strategy_candidate_id'] = f"{orig_id}-R3"
        
    revised['human_review_required'] = True
    revised['candidate_status'] = 'needs_human_review'
    return revised

def write_candidate_concrete_spec(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = SPEC_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['concrete_spec_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Concrete spec record already exists: {file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}

def write_concretized_candidate(revised_candidate_record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = CANDIDATE_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{revised_candidate_record['strategy_candidate_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": revised_candidate_record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Concretized candidate already exists: {file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(revised_candidate_record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
