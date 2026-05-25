import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml
import os

from scripts.quant.human_write_approval import (
    load_human_write_approval_schema,
    parse_human_write_approval_file,
    evaluate_write_approval
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTRACTS_DIR = BASE_DIR / "contracts" / "quant"
SCHEMA_PATH = CONTRACTS_DIR / "guarded_write_execution_schema.yaml"
TEMPLATE_PATH = CONTRACTS_DIR / "guarded_write_execution_template.md"
EVIDENCE_DIR = BASE_DIR / "scratch" / "quant_approvals" / "evidence"

def load_guarded_write_execution_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate_guarded_write_execution(record):
    schema = load_guarded_write_execution_schema()
    
    # 1. Required Fields
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required execution field: {field}")

    # 2. Allowed Values
    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for execution {key}: {record[key]}. Allowed: {values}")

    # 3. Safety Boundary (Must be False)
    safety_boundary = schema.get('safety_boundary', {}).get('must_be_false', [])
    for flag in safety_boundary:
        if record.get(flag) is not False:
            raise ValueError(f"Execution safety flag {flag} MUST be explicitly False.")

    return True

def compute_guarded_execution_id(record):
    seed = f"{record.get('approval_id')}-{record.get('created_at')}-{record.get('target_command')}"
    h = hashlib.sha256(seed.encode()).hexdigest()[:8]
    return f"GW-NOOP-{h.upper()}"

def evaluate_noop_guarded_write(approval_file, future_write_enabled=False, dry_run=True):
    """
    Evaluates a no-op guarded write execution.
    Returns a execution record and evaluation result.
    """
    approval_file = Path(approval_file)
    # Security Check: Reject if outside approved folder
    try:
        abs_approval = approval_file.resolve()
        approved_root = (BASE_DIR / "scratch" / "quant_approvals").resolve()
        if not str(abs_approval).startswith(str(approved_root)):
             # Return empty record with error status
             return {"audit_status": "invalid", "blocking_issues": "Approval file outside approved folder."}, {"status": "BLOCKED", "reason": "Approval file outside approved folder.", "allowed": False}
    except Exception as e:
        return {"audit_status": "invalid", "blocking_issues": str(e)}, {"status": "BLOCKED", "reason": f"Invalid path: {e}", "allowed": False}

    try:
        approval_record = parse_human_write_approval_file(approval_file)
        eval_result = evaluate_write_approval(approval_record, future_write_enabled=future_write_enabled)
    except Exception as e:
        eval_result = {"status": "INVALID", "reason": str(e), "allowed": False}

    now = datetime.now(timezone.utc).isoformat()
    
    # Map status to audit_status
    audit_status = "blocked_noop"
    if eval_result["status"] == "INVALID" or eval_result["status"] == "REJECTED":
        audit_status = "invalid"
    elif eval_result["status"] == "APPROVED" and not future_write_enabled:
        audit_status = "future_ready_but_disabled"

    exec_record = {
        "guarded_execution_id": "PENDING",
        "execution_type": "research_idea_intake_write_noop",
        "target_command": approval_record.get("target_command", "UNKNOWN"),
        "approval_file": str(approval_file),
        "approval_id": approval_record.get("approval_id", "UNKNOWN"),
        "approval_validation_status": eval_result["status"],
        "future_write_enabled": False, # Explicitly False in this milestone
        "write_attempted": False,
        "write_allowed": False,
        "write_performed": False,
        "intended_output_directory": approval_record.get("intended_output_directory", "UNKNOWN"),
        "intended_output_filename": approval_record.get("intended_output_filename", "UNKNOWN"),
        "intended_artifact_type": approval_record.get("intended_artifact_type", "UNKNOWN"),
        "blocking_issues": eval_result.get("reason", "None"),
        "audit_status": audit_status,
        "created_at": now,
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False,
        "safety_backtest_run": False,
        "safety_broker_logic_generated": False,
        "safety_live_trading_authorized": False
    }
    
    exec_record["guarded_execution_id"] = compute_guarded_execution_id(exec_record)
    
    return exec_record, eval_result

def render_execution_audit_markdown(record):
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")
    
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()
    
    rendered = template
    for key, value in record.items():
        placeholder = "{{" + f" {key} " + "}}"
        rendered = rendered.replace(placeholder, str(value))
    
    # Add YAML frontmatter
    frontmatter = "---\n" + yaml.dump(record, sort_keys=False) + "---\n\n"
    return frontmatter + rendered

def write_guarded_execution_audit(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = EVIDENCE_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"AUDIT-{record['guarded_execution_id']}.json"
    md_path = output_dir / f"AUDIT-{record['guarded_execution_id']}.md"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Audit file already exists: {file_path}.")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2)
    
    # Write Markdown
    md_content = render_execution_audit_markdown(record)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return {"status": "written", "json_path": str(file_path), "md_path": str(md_path)}

if __name__ == "__main__":
    # Internal dev test
    test_approval = BASE_DIR / "scratch" / "quant_approvals" / "example_idea_intake_write_approval_draft.md"
    if test_approval.exists():
        rec, res = evaluate_noop_guarded_write(test_approval)
        print(json.dumps(rec, indent=2))
        print(f"Eval: {res['status']}")
    else:
        print("Example approval not found for internal test.")
