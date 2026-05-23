import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import yaml
import re

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTRACTS_DIR = BASE_DIR / "contracts" / "quant"
SCHEMA_PATH = CONTRACTS_DIR / "human_write_approval_schema.yaml"
APPROVALS_DIR = BASE_DIR / "scratch" / "quant_approvals"
REPORTS_RI_DIR = BASE_DIR / "reports" / "quant" / "research_ideas"

def load_human_write_approval_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def compute_file_hash(path):
    path = Path(path)
    if not path.exists():
        return "FILE_NOT_FOUND"
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return f"sha256:{sha256_hash.hexdigest()}"

def compute_approval_id(record):
    # Deterministic ID based on critical fields
    seed = f"{record.get('operator_name')}-{record.get('created_at')}-{record.get('target_command')}"
    h = hashlib.sha256(seed.encode()).hexdigest()[:8]
    return f"HAF-WRITE-{h.upper()}"

def parse_human_write_approval_file(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Approval file not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple YAML frontmatter parser for .md or full YAML for .yaml
    if path.suffix == '.md':
        # Look for YAML frontmatter between ---
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            return yaml.safe_load(match.group(1))
        else:
            # Fallback: try to find key-value pairs in the markdown text
            data = {}
            lines = content.split('\n')
            for line in lines:
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip('- ').strip('* ').strip()
                    val = val.strip('`').strip()
                    if key and val:
                        # Convert boolean strings
                        if val.lower() == 'true': val = True
                        elif val.lower() == 'false': val = False
                        data[key] = val
            return data
    else:
        return yaml.safe_load(content)

def validate_human_write_approval(record):
    schema = load_human_write_approval_schema()
    
    # 1. Required Fields
    for field in schema.get('required_fields', []):
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    # 2. Allowed Values
    allowed = schema.get('allowed_values', {})
    for key, values in allowed.items():
        if key in record and record[key] not in values:
            raise ValueError(f"Invalid value for {key}: {record[key]}. Allowed: {values}")

    # 3. Safety Boundary (Must be False)
    safety_boundary = schema.get('safety_boundary', {}).get('must_be_false', [])
    for flag in safety_boundary:
        if record.get(flag) is not False:
            raise ValueError(f"Safety flag {flag} MUST be explicitly False.")

    # 4. Forbidden Actions (All must be present)
    mandatory_forbidden = schema.get('forbidden_actions_mandatory', [])
    actual_forbidden = record.get('forbidden_actions', [])
    for action in mandatory_forbidden:
        if action not in actual_forbidden:
            raise ValueError(f"Mandatory forbidden action missing from approval: {action}")

    # 5. Target Command Restriction (Idea Intake Write only)
    target = record.get('target_command', '')
    if not target.startswith("ws quant idea-intake-write"):
        raise ValueError(f"Unsupported target command: {target}. Only idea-intake-write is allowed.")

    # 6. Path Constraints
    path_constraints = schema.get('path_constraints', {})
    
    source_file = record.get('source_input_file', '')
    allowed_inputs = path_constraints.get('allowed_input_folders', [])
    if not any(source_file.startswith(folder) for folder in allowed_inputs):
        raise ValueError(f"Source input file must be within approved folders: {allowed_inputs}")

    output_dir = record.get('intended_output_directory', '')
    allowed_outputs = path_constraints.get('allowed_output_folders', [])
    if not any(output_dir.startswith(folder) for folder in allowed_outputs):
        raise ValueError(f"Intended output directory must be within approved folders: {allowed_outputs}")

    # 7. Expiry
    expires_at_str = record.get('expires_at')
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expires_at:
            raise ValueError(f"Approval has expired: {expires_at_str}")
    except Exception as e:
        if "expired" in str(e): raise
        raise ValueError(f"Invalid expiry timestamp: {expires_at_str}")

    # 8. Operator Confirmation
    if not record.get('operator_confirmation'):
        raise ValueError("Operator confirmation is missing.")

    return True

def evaluate_write_approval(record, future_write_enabled=False):
    """
    Final gate for write execution.
    ALWAYS returns blocked if future_write_enabled is False.
    """
    try:
        validate_human_write_approval(record)
    except Exception as e:
        return {"status": "REJECTED", "reason": str(e), "allowed": False}

    if not future_write_enabled:
        return {
            "status": "BLOCKED", 
            "reason": "Write mode is designed but not currently enabled in this workstation milestone.", 
            "allowed": False
        }

    if record.get('approval_status') == 'approved_for_single_local_write':
        return {"status": "APPROVED", "reason": "All gates passed.", "allowed": True}
    
    return {"status": "PENDING", "reason": f"Approval status is {record.get('approval_status')}.", "allowed": False}

def build_blocked_example_approval(operator_name="Operator-01"):
    now = datetime.now(timezone.utc)
    created_at = now.isoformat()
    expires_at = (now.replace(hour=now.hour + 1)).isoformat() # 1 hour expiry
    
    source_file = "scratch/quant_ideas/example_vwap_research_paper_idea.md"
    # Note: In a real run, we would compute the actual hash of the file.
    # For the example, we'll use a placeholder or compute it if it exists.
    source_hash = compute_file_hash(BASE_DIR / source_file)
    
    record = {
        "approval_id": "HAF-WRITE-EXAMPLE-BLOCKED",
        "approval_type": "research_idea_intake_write",
        "target_command": 'ws quant idea-intake-write --title "VWAP Research" --idea-file ' + source_file + ' --write',
        "target_command_safety_class": "GUARDED_WRITE",
        "source_input_file": source_file,
        "source_input_hash": source_hash,
        "dry_run_command": 'ws quant idea-intake-dry-run --title "VWAP Research" --idea-file ' + source_file,
        "dry_run_output_hash": "sha256:dry_run_result_hash_placeholder",
        "intended_output_directory": "reports/quant/research_ideas/",
        "intended_output_filename": "RI-EXAMPLE.json",
        "intended_artifact_type": "research_idea_json",
        "operator_name": operator_name,
        "operator_confirmation": "I have verified the dry-run and input hash.",
        "reason_for_write": "Example intake for vwap research idea.",
        "approval_scope": "single_local_write_only",
        "approval_status": "pending_review",
        "expires_at": expires_at,
        "created_at": created_at,
        "forbidden_actions": [
            "run_backtest", "generate_signal", "approve_strategy", 
            "paper_trade", "live_trade", "broker_execution", "download_data"
        ],
        "safety_financial_advice_generated": False,
        "safety_trading_signal_generated": False,
        "safety_bot_logic_generated": False,
        "safety_live_trading_logic_generated": False,
        "safety_backtest_run": False,
        "safety_broker_logic_generated": False,
        "safety_live_trading_authorized": False
    }
    record["approval_id"] = compute_approval_id(record)
    return record

def write_human_write_approval(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = APPROVALS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['approval_id']}.yaml"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Approval file already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(record, f, sort_keys=False)

    return {"status": "written", "path": str(file_path)}

if __name__ == "__main__":
    # Self-test / Example generation
    example = build_blocked_example_approval()
    result = evaluate_write_approval(example)
    print(f"Example Approval ID: {example['approval_id']}")
    print(f"Evaluation Result: {json.dumps(result, indent=2)}")
