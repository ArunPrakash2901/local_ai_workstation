import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yaml
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTRACTS_DIR = BASE_DIR / "contracts" / "quant"
SCHEMA_PATH = CONTRACTS_DIR / "human_write_approval_schema.yaml"
TEMPLATE_PATH = CONTRACTS_DIR / "human_write_approval_template.md"
APPROVALS_DIR = BASE_DIR / "scratch" / "quant_approvals"
EVIDENCE_DIR = APPROVALS_DIR / "evidence"

def compute_file_sha256(path):
    path = Path(path)
    if not path.exists():
        return "FILE_NOT_FOUND"
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return f"sha256:{sha256_hash.hexdigest()}"

def validate_approved_source_input_path(path):
    path = Path(path)
    # Resolve against BASE_DIR to handle both relative and absolute paths
    try:
        if path.is_absolute():
            abs_path = path.resolve()
        else:
            abs_path = (BASE_DIR / path).resolve()
    except Exception as e:
        raise ValueError(f"Invalid path: {path}. {e}")

    # Check for path traversal outside BASE_DIR
    try:
        rel_path = abs_path.relative_to(BASE_DIR.resolve())
    except ValueError:
        raise ValueError(f"Path outside project root is forbidden: {path}")
    
    # Check if within scratch/quant_ideas/
    if not str(rel_path.as_posix()).startswith("scratch/quant_ideas/"):
        raise ValueError(f"Source input path must be within scratch/quant_ideas/: {path}")

    # Check file size (max 50KB)
    if abs_path.exists() and abs_path.stat().st_size > 50 * 1024:
        raise ValueError(f"Source input file exceeds 50KB limit: {abs_path.stat().st_size} bytes")

    return True

def build_dry_run_command_record(title, source_type, idea_file):
    return {
        "command": f"ws quant idea-intake-dry-run --title \"{title}\" --source-type {source_type} --idea-file {idea_file}",
        "title": title,
        "source_type": source_type,
        "idea_file": idea_file
    }

def build_approval_draft_record(title, source_type, idea_file, operator_name="Operator-01"):
    now = datetime.now(timezone.utc)
    created_at = now.isoformat()
    expires_at = (now + timedelta(hours=1)).isoformat()
    
    source_input_hash = compute_file_sha256(BASE_DIR / idea_file)
    dry_run_cmd = build_dry_run_command_record(title, source_type, idea_file)
    
    # Placeholder for dry-run output hash
    dry_run_output_hash = "sha256:dry_run_evidence_placeholder"
    
    # Intended future command
    target_command = f"ws quant idea-intake-write --title \"{title}\" --source-type {source_type} --idea-file {idea_file} --write"

    record = {
        "approval_id": "DRAFT-ID-PENDING", # Will be computed later
        "approval_type": "research_idea_intake_write",
        "target_command": target_command,
        "target_command_safety_class": "GUARDED_WRITE",
        "source_input_file": str(idea_file),
        "source_input_hash": source_input_hash,
        "dry_run_command": dry_run_cmd["command"],
        "dry_run_output_hash": dry_run_output_hash,
        "intended_output_directory": "reports/quant/research_ideas/",
        "intended_output_filename": f"RI-{hashlib.sha256(title.encode()).hexdigest()[:8].upper()}.json",
        "intended_artifact_type": "research_idea_json",
        "operator_name": operator_name,
        "operator_confirmation": "PENDING_REVIEW",
        "reason_for_write": f"Intake of research idea: {title}",
        "approval_scope": "single_local_write_only",
        "approval_status": "draft",
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
    
    # Deterministic ID based on critical fields
    seed = f"{operator_name}-{created_at}-{target_command}"
    h = hashlib.sha256(seed.encode()).hexdigest()[:8]
    record["approval_id"] = f"HAF-DRAFT-{h.upper()}"
    
    return record

def render_approval_draft_markdown(record):
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")
    
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Simple template substitution
    rendered = template
    for key, value in record.items():
        placeholder = "{{" + f" {key} " + "}}"
        # Handle lists (forbidden_actions)
        if isinstance(value, list):
            # This is a bit hacky for markdown template, but works for the specified template
            # The template has a loop block: {% for action in forbidden_actions %}\n- {{ action }}\n{% endfor %}
            # We'll just replace the whole block if we find it, or just the placeholder if it's there.
            if "{% for action in forbidden_actions %}" in rendered:
                block_start = rendered.find("{% for action in forbidden_actions %}")
                block_end = rendered.find("{% endfor %}") + len("{% endfor %}")
                actions_str = "\n".join([f"- {a}" for action in value for a in [action]]) # wait, that's wrong
                actions_str = "\n".join([f"- {a}" for a in value])
                rendered = rendered[:block_start] + actions_str + rendered[block_end:]
        else:
            rendered = rendered.replace(placeholder, str(value))
    
    # Also add the YAML frontmatter
    frontmatter = "---\n" + yaml.dump(record, sort_keys=False) + "---\n\n"
    return frontmatter + rendered

def write_approval_draft(record, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = APPROVALS_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"{record['approval_id']}.md"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "record": record}

    if file_path.exists() and not force:
        raise FileExistsError(f"Draft approval already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)
    
    content = render_approval_draft_markdown(record)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {"status": "written", "path": str(file_path)}

def build_evidence_pack(record):
    """
    Builds the hash evidence pack for Q49.
    """
    evidence = {
        "source_input_file": record["source_input_file"],
        "source_input_sha256": record["source_input_hash"],
        "dry_run_command": record["dry_run_command"],
        "dry_run_output_text": "DRY_RUN_OUTPUT_PLACEHOLDER_CAPTURED_BY_OPERATOR",
        "dry_run_output_sha256": record["dry_run_output_hash"],
        "prepared_at": record["created_at"],
        "intended_future_command": record["target_command"],
        "intended_output_directory": record["intended_output_directory"],
        "intended_artifact_type": record["intended_artifact_type"],
        "safety_flags": {
            "safety_financial_advice_generated": record["safety_financial_advice_generated"],
            "safety_trading_signal_generated": record["safety_trading_signal_generated"],
            "safety_bot_logic_generated": record["safety_bot_logic_generated"],
            "safety_live_trading_logic_generated": record["safety_live_trading_logic_generated"],
            "safety_backtest_run": record["safety_backtest_run"],
            "safety_broker_logic_generated": record["safety_broker_logic_generated"],
            "safety_live_trading_authorized": record["safety_live_trading_authorized"]
        }
    }
    return evidence

def write_evidence_pack(evidence, approval_id, output_dir=None, dry_run=True, force=False):
    if output_dir is None:
        output_dir = EVIDENCE_DIR
    
    output_dir = Path(output_dir)
    file_path = output_dir / f"EVIDENCE-{approval_id}.json"

    if dry_run:
        return {"status": "dry_run", "path": str(file_path), "evidence": evidence}

    if file_path.exists() and not force:
        raise FileExistsError(f"Evidence pack already exists: {file_path}. Use force=True to overwrite.")

    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(evidence, f, indent=2)

    return {"status": "written", "path": str(file_path)}
