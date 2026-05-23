import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
COMPLETION_DIR = BASE_DIR / "reports" / "quant" / "candidate_detail_completions"
CANDIDATE_DIR = BASE_DIR / "reports" / "quant" / "strategy_candidates"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "candidate_detail_completion_schema.yaml"

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

def load_candidate_detail_completion_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_candidate_detail_completion(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('completion_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['completion_status']}")
    
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

def parse_completion_note_file(path):
    path = Path(path).resolve()
    base_dir = Path(__file__).resolve().parent.parent.parent
    approved_dirs = [
        (base_dir / "scratch" / "quant_strategy_candidates").resolve()
    ]
    
    is_approved = any(ad in path.parents for ad in approved_dirs)
    if not is_approved:
         raise ValueError(f"Completion note must be within scratch/quant_strategy_candidates/. Got: {path}")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Completion note not found: {path}")

    if path.stat().st_size > 100 * 1024:
        raise ValueError(f"Completion note exceeds maximum allowed size of 100KB")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    check_forbidden_phrases(content)
    return content

def compute_completion_id(candidate_id, note_text):
    combined = f"{candidate_id}_{note_text}".encode('utf-8')
    return "CMP-" + hashlib.sha256(combined).hexdigest()[:12]

def build_candidate_detail_completion(candidate_record, completion_note_text=None, cand_path="UNKNOWN", dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    note_content = completion_note_text if completion_note_text else "UNKNOWN"
    check_forbidden_phrases(note_content)
    cand_id = candidate_record.get('strategy_candidate_id', 'UNKNOWN')
    cmp_id = compute_completion_id(cand_id, note_content)
    
    # In a real system, we'd parse the note. Here we just capture it.
    record = {
        "completion_id": cmp_id,
        "linked_strategy_candidate_id": cand_id,
        "source_candidate_file": str(cand_path),
        "completion_status": "draft",
        "human_supplied_universe_definition": "UNKNOWN",
        "human_supplied_timeframe_definition": "UNKNOWN",
        "human_supplied_feature_requirements": "UNKNOWN",
        "human_supplied_cost_model": "UNKNOWN",
        "human_supplied_slippage_model": "UNKNOWN",
        "human_supplied_execution_assumptions": "UNKNOWN",
        "human_supplied_validation_requirements": "UNKNOWN",
        "human_supplied_risk_controls": "UNKNOWN",
        "human_supplied_failure_modes": "UNKNOWN",
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

def apply_completion_to_candidate(candidate_record, completion_record, dry_run=True):
    revised = candidate_record.copy()
    # Apply R2 suffix
    orig_id = candidate_record['strategy_candidate_id']
    if "-R" in orig_id:
        base_id = orig_id.split("-R")[0]
        revised['strategy_candidate_id'] = f"{base_id}-R2"
    else:
        revised['strategy_candidate_id'] = f"{orig_id}-R2"
        
    revised['human_review_required'] = True
    revised['candidate_status'] = 'needs_human_review'
    # We'd typically merge human_supplied fields here. 
    # For Milestone Q18, we just mark as revised.
    return revised

def write_candidate_detail_completion(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = COMPLETION_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['completion_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Completion record already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}

def write_completed_candidate(revised_candidate_record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = CANDIDATE_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{revised_candidate_record['strategy_candidate_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": revised_candidate_record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Completed candidate already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(revised_candidate_record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
