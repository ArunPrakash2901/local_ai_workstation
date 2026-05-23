import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "strategy_candidates"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "strategy_candidate_schema.yaml"

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
    r"\bexecute now\b"
]

def load_strategy_candidate_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def check_safety_flags(record, flags):
    for flag in flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

def check_forbidden_statuses(record, schema):
    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('candidate_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['candidate_status']}")

def check_forbidden_phrases(content):
    content = str(content).lower()
    for pattern in FORBIDDEN_PHRASES:
        if re.search(pattern, content):
            raise ValueError(f"Forbidden phrase found: matches '{pattern}'")

def validate_strategy_candidate(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    check_forbidden_statuses(record, schema)
    
    safety_flags = [
        'safety_financial_advice_generated',
        'safety_trading_signal_generated',
        'safety_bot_logic_generated',
        'safety_live_trading_logic_generated'
    ]
    check_safety_flags(record, safety_flags)

    text_fields = ['signal_concepts', 'title', 'proposed_edge_mechanism', 'entry_logic_conceptual', 'exit_logic_conceptual']
    for tf in text_fields:
        check_forbidden_phrases(record.get(tf, ''))

    return True

def compute_strategy_candidate_id(title, note_text):
    combined = f"{title}_{note_text}".encode('utf-8')
    return "CAN-" + hashlib.sha256(combined).hexdigest()[:12]

def build_strategy_candidate_from_inputs(idea_record=None, paper_record=None, replication_plan_record=None, note_text=None, title="UNKNOWN", source_type="manual_note", dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    note_content = note_text if note_text else "UNKNOWN"
    check_forbidden_phrases(note_content)
    check_forbidden_phrases(title)
    
    can_id = compute_strategy_candidate_id(title, note_content)
    
    record = {
        "strategy_candidate_id": can_id,
        "linked_idea_id": idea_record['idea_id'] if idea_record else "UNKNOWN",
        "linked_hypothesis_id": "UNKNOWN",
        "linked_paper_id": paper_record['paper_id'] if paper_record else "UNKNOWN",
        "linked_replication_plan_id": replication_plan_record['replication_plan_id'] if replication_plan_record else "UNKNOWN",
        "title": title,
        "source_type": source_type,
        "source_references": "UNKNOWN",
        "candidate_status": "draft",
        "strategy_family": "UNKNOWN",
        "market_or_asset_class": "UNKNOWN",
        "universe_definition": "UNKNOWN",
        "timeframe_definition": "UNKNOWN",
        "proposed_edge_mechanism": note_content,
        "signal_concepts": "UNKNOWN",
        "entry_logic_conceptual": "UNKNOWN",
        "exit_logic_conceptual": "UNKNOWN",
        "position_sizing_conceptual": "UNKNOWN",
        "risk_controls_required": "UNKNOWN",
        "data_requirements": "UNKNOWN",
        "feature_requirements": "UNKNOWN",
        "execution_assumptions": "UNKNOWN",
        "transaction_cost_assumptions": "UNKNOWN",
        "slippage_assumptions": "UNKNOWN",
        "validation_requirements": "UNKNOWN",
        "known_failure_modes": "UNKNOWN",
        "known_unknowns": "UNKNOWN",
        "human_owner": "OPERATOR",
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_strategy_candidate(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['strategy_candidate_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Candidate already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
