import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "paper_replications"
PAPER_SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "research_paper_schema.yaml"
PLAN_SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "paper_replication_plan_schema.yaml"

FORBIDDEN_PHRASES = [
    r"\bguaranteed profit\b",
    r"\blive trading\b",
    r"\breal-money execution\b",
    r"\bbroker execution\b",
    r"\bbuy advice\b",
    r"\bsell advice\b",
    r"\bhold advice\b",
    r"\bdirect buy\b",
    r"\bdirect sell\b"
]

def load_research_paper_schema():
    if not PAPER_SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {PAPER_SCHEMA_PATH}")
    with open(PAPER_SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_replication_plan_schema():
    if not PLAN_SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {PLAN_SCHEMA_PATH}")
    with open(PLAN_SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def check_safety_flags(record, flags):
    for flag in flags:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

def check_forbidden_statuses(record, schema):
    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('review_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['review_status']}")

def check_forbidden_phrases(content):
    content = str(content).lower()
    for pattern in FORBIDDEN_PHRASES:
        if re.search(pattern, content):
            raise ValueError(f"Forbidden phrase found: matches '{pattern}'")

def validate_research_paper_record(record, schema):
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

    text_fields = ['abstract_or_summary', 'title', 'methodology_summary', 'core_claims']
    for tf in text_fields:
        check_forbidden_phrases(record.get(tf, ''))

    return True

def validate_replication_plan(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field in replication plan: {field}")

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
    return True

def compute_paper_id(title, local_note_file):
    combined = f"{title}_{local_note_file}".encode('utf-8')
    return "PPR-" + hashlib.sha256(combined).hexdigest()[:12]

def parse_paper_note_file(path):
    path = Path(path).resolve()
    base_dir = Path(__file__).resolve().parent.parent.parent
    scratch_dir = (base_dir / "scratch" / "quant_papers").resolve()
    
    if scratch_dir not in path.parents:
         raise ValueError(f"Paper note must be within scratch/quant_papers/. Got: {path}")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Paper note not found: {path}")

    if path.stat().st_size > 100 * 1024:
        raise ValueError(f"Paper note exceeds maximum allowed size of 100KB: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    check_forbidden_phrases(content)
    return content

def build_research_paper_record(title, source_type, local_note_file, **kwargs):
    now = datetime.now(timezone.utc).isoformat()
    content = parse_paper_note_file(local_note_file)
    record = {
        "paper_id": compute_paper_id(title, local_note_file),
        "title": title,
        "authors": kwargs.get('authors', 'UNKNOWN'),
        "year": kwargs.get('year', 'UNKNOWN'),
        "source_url": kwargs.get('source_url', 'UNKNOWN'),
        "source_type": source_type,
        "source_reference": kwargs.get('source_reference', 'UNKNOWN'),
        "local_note_file": local_note_file,
        "abstract_or_summary": content,
        "core_claims": "UNKNOWN",
        "claimed_market": "UNKNOWN",
        "claimed_asset_class": "UNKNOWN",
        "claimed_timeframe": "UNKNOWN",
        "claimed_edge_mechanism": "UNKNOWN",
        "claimed_results": "UNKNOWN",
        "data_used_in_paper": "UNKNOWN",
        "methodology_summary": "UNKNOWN",
        "assumptions": "UNKNOWN",
        "limitations": "UNKNOWN",
        "replication_relevance": "UNKNOWN",
        "human_owner": kwargs.get('human_owner', 'OPERATOR'),
        "review_status": kwargs.get('review_status', 'needs_human_review'),
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def compute_replication_plan_id(paper_id):
    return "REP-" + paper_id.replace("PPR-", "")

def build_replication_plan_from_inputs(idea_record=None, hypothesis_record=None, paper_record=None, dry_run=True):
    if paper_record is None:
        raise ValueError("paper_record is required to build a replication plan.")
    
    now = datetime.now(timezone.utc).isoformat()
    plan_id = compute_replication_plan_id(paper_record['paper_id'])
    
    plan = {
        "replication_plan_id": plan_id,
        "linked_idea_id": idea_record['idea_id'] if idea_record else "UNKNOWN",
        "linked_hypothesis_id": hypothesis_record['hypothesis_id'] if hypothesis_record else "UNKNOWN",
        "linked_paper_id": paper_record['paper_id'],
        "replication_objective": f"Replicate claims from {paper_record['title']}",
        "claim_to_replicate": paper_record.get('core_claims', "UNKNOWN"),
        "falsifiable_replication_question": "UNKNOWN",
        "required_data": paper_record.get('data_used_in_paper', "UNKNOWN"),
        "data_availability_status": "UNKNOWN",
        "universe_definition": "UNKNOWN",
        "timeframe_definition": "UNKNOWN",
        "methodology_steps": paper_record.get('methodology_summary', "UNKNOWN"),
        "expected_outputs": "UNKNOWN",
        "validation_checks": "UNKNOWN",
        "bias_checks": "UNKNOWN",
        "risk_checks": "UNKNOWN",
        "execution_considerations": "UNKNOWN",
        "transaction_cost_considerations": "UNKNOWN",
        "failure_conditions": "UNKNOWN",
        "assumptions": paper_record.get('assumptions', "UNKNOWN"),
        "unknowns": "UNKNOWN",
        "implementation_readiness": "not_ready",
        "human_review_required": True,
        "review_status": "draft",
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return plan

def write_research_paper_record(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['paper_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Record already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}

def write_replication_plan(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['replication_plan_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Plan already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
