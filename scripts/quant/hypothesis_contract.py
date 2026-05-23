import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "research_ideas"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "hypothesis_contract_schema.yaml"

def load_hypothesis_contract_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_hypothesis_contract(record, schema):
    # Check required fields
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field in hypothesis contract: {field}")

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

    return True

def compute_hypothesis_id(idea_id):
    return "HYP-" + idea_id.replace("RI-", "")

def build_hypothesis_contract_from_idea(idea_record):
    now = datetime.now(timezone.utc).isoformat()
    hyp_id = compute_hypothesis_id(idea_record['idea_id'])
    
    contract = {
        "hypothesis_id": hyp_id,
        "linked_idea_id": idea_record['idea_id'],
        "hypothesis_statement": f"Draft hypothesis derived from: {idea_record['title']}",
        "falsifiable_claim": "UNKNOWN",
        "expected_mechanism": idea_record.get('proposed_edge_mechanism', "UNKNOWN"),
        "required_data": idea_record.get('required_data', "UNKNOWN"),
        "data_availability_status": "UNKNOWN",
        "test_design": "UNKNOWN",
        "validation_checks": idea_record.get('required_validation', "UNKNOWN"),
        "risk_checks": idea_record.get('known_risks', "UNKNOWN"),
        "execution_considerations": "UNKNOWN",
        "failure_conditions": "UNKNOWN",
        "assumptions": "UNKNOWN",
        "unknowns": idea_record.get('known_unknowns', "UNKNOWN"),
        "human_review_required": True,
        "review_status": "draft",
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return contract

def write_hypothesis_contract(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['hypothesis_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Contract already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
