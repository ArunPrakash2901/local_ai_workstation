import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "research_ideas"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "research_idea_schema.yaml"

FORBIDDEN_PHRASES = [
    r"\bguaranteed profit\b",
    r"\blive trading\b",
    r"\bbroker execution\b",
    r"\bbuy advice\b",
    r"\bsell advice\b",
    r"\bhold advice\b",
    r"\bdirect buy\b",
    r"\bdirect sell\b"
]

def load_research_idea_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_research_idea_record(record, schema):
    # Check required fields
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    # Check allowed values
    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    # Check forbidden statuses
    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('review_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['review_status']}")

    # Check safety flags
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    for flag in safety_flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    # Check forbidden phrasing in text fields
    text_fields = ['raw_idea_text', 'title', 'proposed_edge_mechanism']
    for tf in text_fields:
        content = str(record.get(tf, '')).lower()
        for pattern in FORBIDDEN_PHRASES:
            if re.search(pattern, content):
                raise ValueError(f"Forbidden phrase found in {tf}: matches '{pattern}'")
    
    return True

def compute_idea_id(title, source_reference):
    combined = f"{title}_{source_reference}".encode('utf-8')
    return "RI-" + hashlib.sha256(combined).hexdigest()[:12]

def build_research_idea_record(title, source_type, raw_idea_text, source_reference="MANUAL", **kwargs):
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "idea_id": compute_idea_id(title, source_reference),
        "title": title,
        "source_type": source_type,
        "source_reference": source_reference,
        "source_url": kwargs.get('source_url', 'UNKNOWN'),
        "source_artifact": kwargs.get('source_artifact', 'UNKNOWN'),
        "source_workflow_id": kwargs.get('source_workflow_id', 'UNKNOWN'),
        "source_topic_ids": kwargs.get('source_topic_ids', 'UNKNOWN'),
        "raw_idea_text": raw_idea_text,
        "idea_category": kwargs.get('idea_category', 'UNKNOWN'),
        "market_or_asset_class": kwargs.get('market_or_asset_class', 'UNKNOWN'),
        "timeframe_hypothesis": kwargs.get('timeframe_hypothesis', 'UNKNOWN'),
        "proposed_edge_mechanism": kwargs.get('proposed_edge_mechanism', 'UNKNOWN'),
        "required_data": kwargs.get('required_data', 'UNKNOWN'),
        "required_validation": kwargs.get('required_validation', 'UNKNOWN'),
        "known_risks": kwargs.get('known_risks', 'UNKNOWN'),
        "known_unknowns": kwargs.get('known_unknowns', 'UNKNOWN'),
        "human_owner": kwargs.get('human_owner', 'OPERATOR'),
        "review_status": kwargs.get('review_status', 'needs_human_review'),
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_research_idea_record(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['idea_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Record already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
