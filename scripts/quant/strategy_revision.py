import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REVISION_DIR = BASE_DIR / "reports" / "quant" / "strategy_candidate_revisions"
CANDIDATE_DIR = BASE_DIR / "reports" / "quant" / "strategy_candidates"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "strategy_candidate_revision_schema.yaml"

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
    r"\bimmediate backtest\b",
    r"\bexecute now\b",
    r"\bpaper trading\b"
]

def load_strategy_candidate_revision_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_strategy_candidate_revision(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('revision_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['revision_status']}")
    
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

def compute_revision_id(candidate_id, note_text):
    combined = f"{candidate_id}_{note_text}".encode('utf-8')
    return "REV-" + hashlib.sha256(combined).hexdigest()[:12]

def check_forbidden_phrases(content):
    content = str(content).lower()
    for pattern in FORBIDDEN_PHRASES:
        if re.search(pattern, content):
            raise ValueError(f"Forbidden phrase found: matches '{pattern}'")

def apply_candidate_revision(candidate_record, gap_report_record=None, revision_note_text=None, cand_path="UNKNOWN", dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    note_content = revision_note_text if revision_note_text else "UNKNOWN"
    check_forbidden_phrases(note_content)
    
    cand_id = candidate_record.get('strategy_candidate_id', 'UNKNOWN')
    rev_id = compute_revision_id(cand_id, note_content)
    
    # We do a naive merge for this milestone: if note contains key-value pairs, we'd update. 
    # Since we are taking a raw note, we append it to 'human_supplied_clarifications' 
    # and mark the candidate as needing human review to structurally parse it later.
    
    revised_candidate = candidate_record.copy()
    revised_candidate['strategy_candidate_id'] = f"{cand_id}-R1" # New ID for safety
    revised_candidate['human_review_required'] = True
    revised_candidate['candidate_status'] = 'needs_human_review'
    
    # We aren't doing complex NLP extraction. We leave fields UNKNOWN but capture the note.
    # A real system would use a parser or form here.
    
    record = {
        "revision_id": rev_id,
        "linked_strategy_candidate_id": cand_id,
        "source_candidate_file": str(cand_path),
        "source_gap_report_id": gap_report_record.get('gap_report_id', 'UNKNOWN') if gap_report_record else "UNKNOWN",
        "revision_status": "draft",
        "revised_fields": ["none_automatically_parsed"],
        "unchanged_fields": ["all"],
        "human_supplied_clarifications": note_content,
        "still_unknown_fields": gap_report_record.get('unknown_fields', []) if gap_report_record else [],
        "remaining_blocking_issues": "UNKNOWN",
        "revision_summary": "Manual revision note attached. Awaiting human parsing.",
        "candidate_record_after_revision": revised_candidate,
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_strategy_candidate_revision(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REVISION_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['revision_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Revision record already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}

def write_revised_strategy_candidate(revised_candidate_record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = CANDIDATE_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{revised_candidate_record['strategy_candidate_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": revised_candidate_record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Revised candidate already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(revised_candidate_record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
