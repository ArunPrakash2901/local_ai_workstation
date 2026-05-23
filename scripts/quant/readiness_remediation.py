import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "quant" / "readiness_gap_reports"
SCHEMA_PATH = BASE_DIR / "contracts" / "quant" / "readiness_gap_report_schema.yaml"

def load_readiness_gap_report_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_readiness_gap_report(record, schema):
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    forbidden_statuses = schema.get('forbidden_statuses', [])
    if record.get('recommended_next_status') in forbidden_statuses:
        raise ValueError(f"Forbidden status found: {record['recommended_next_status']}")
    
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

def compute_gap_report_id(strategy_candidate_id, readiness_id):
    combined = f"{strategy_candidate_id}_{readiness_id}".encode('utf-8')
    return "GAP-" + hashlib.sha256(combined).hexdigest()[:12]

def build_gap_report(candidate_record, readiness_record, cand_path="UNKNOWN", rdy_path="UNKNOWN", dry_run=True):
    now = datetime.now(timezone.utc).isoformat()
    cand_id = candidate_record.get('strategy_candidate_id', 'UNKNOWN')
    rdy_id = readiness_record.get('readiness_id', 'UNKNOWN')
    gap_id = compute_gap_report_id(cand_id, rdy_id)
    
    unknowns = []
    for k, v in candidate_record.items():
        if v == "UNKNOWN" or v == "":
            unknowns.append(k)

    status_observed = readiness_record.get('readiness_status', 'UNKNOWN')
    next_status = "revise_candidate" if len(unknowns) > 0 else "needs_more_detail"

    record = {
        "gap_report_id": gap_id,
        "linked_strategy_candidate_id": cand_id,
        "linked_readiness_id": rdy_id,
        "source_candidate_file": str(cand_path),
        "source_readiness_file": str(rdy_path),
        "readiness_status_observed": status_observed,
        "missing_fields": unknowns,
        "incomplete_fields": [],
        "unknown_fields": unknowns,
        "blocking_issues": readiness_record.get('blocking_issues', 'UNKNOWN'),
        "warnings": "Multiple UNKNOWN fields detected." if unknowns else "NONE",
        "remediation_actions": ["Provide a candidate revision note clarifying UNKNOWN fields."],
        "required_human_inputs": unknowns,
        "required_data_clarifications": "data_requirements" in unknowns or "universe_definition" in unknowns or "timeframe_definition" in unknowns,
        "required_risk_clarifications": "risk_controls_required" in unknowns,
        "required_execution_clarifications": "execution_assumptions" in unknowns or "transaction_cost_assumptions" in unknowns or "slippage_assumptions" in unknowns,
        "required_validation_clarifications": "validation_requirements" in unknowns or "known_failure_modes" in unknowns,
        "recommended_next_status": next_status,
        "human_review_required": True,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False
    }
    return record

def write_gap_report(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = REPORTS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['gap_report_id']}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Gap Report already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)

    return {"status": "written", "path": str(file_path)}
