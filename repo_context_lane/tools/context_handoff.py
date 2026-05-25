import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .packet_review import review_packet

HANDOFF_TEMPLATES = {
    "codex": """# Codex Context Handoff: {task_name} ({project_id})

## Context-Only Approval Reference
- **Source Packet**: `{packet_path}`
- **Approved At**: {approved_at}
- **Approval Scope**: {approval_scope}

## Selected Candidate Files/Modules
{candidates_list}

## Safety Boundaries & Constraints
- **Scope**: CONTEXT_ONLY. This is for research and reasoning only.
- **DO NOT**: Inspect large, raw, or private files outside this list.
- **DO NOT**: Run applications, tests, or install packages.
- **DO NOT**: Execute Graphify or any repository mutation tools.
- **DO NOT**: Create branches, commit, push, or merge.
- **DO NOT**: Modify any files.

## Suggested Prompt
Review the listed files to understand the architecture for "{task_name}". 
Provide a summary of the current state and a proposed high-level implementation plan.
Do not generate code changes in this session.

## Expected Output
1. Summary of files inspected.
2. Proposed implementation plan.
3. Identified risks and unknowns.
""",
    "gemini": """# Gemini Context Handoff: {task_name} ({project_id})

## Context Approval
This context has been approved for **{approval_scope}** use only.
- **Packet**: `{packet_path}`
- **Approved At**: {approved_at}

## Repository Context (Selected Candidates)
{candidates_list}

## Bounded Execution Policy
Your goal is to perform deep reasoning and research on the provided context for the task: "{task_name}".
You must strictly adhere to the following safety boundaries:
- **NO MUTATION**: Do not modify any files, branches, or repository state.
- **NO EXECUTION**: Do not run any code, scripts, or external tools (Graphify, npm, pip, etc.).
- **NO DATA LEAKAGE**: Do not inspect files outside the approved candidate list.

## Requested Analysis
Please analyze the provided files and explain the relationships between the modules as they pertain to "{task_name}".
Provide a detailed technical breakdown and a list of any missing information or uncertainties.
""",
    "local": """# Local Model Handoff: {task_name} ({project_id})

## APPROVED CONTEXT ONLY
Task: {task_name}
Project: {project_id}
Approval: {approval_scope} ({approved_at})

## Approved Files
{candidates_list_short}

## STRICT CONSTRAINTS
- RESEARCH ONLY.
- NO FILE MODIFICATIONS.
- NO CODE EXECUTION.
- NO GIT OPERATIONS.
- DO NOT SCAN OUTSIDE APPROVED LIST.

## Task
Summarize how these files relate to "{task_name}". List risks.
"""
}

def generate_handoff(packet_path: Path, target: str, output_root: Path, dry_run: bool = True) -> Tuple[bool, str, Dict[str, Any]]:
    if target not in HANDOFF_TEMPLATES:
        return False, f"Invalid target: {target}. Must be one of: {', '.join(HANDOFF_TEMPLATES.keys())}", {}

    # 1. Load and validate packet
    if not packet_path.exists():
        return False, f"Packet not found: {packet_path}", {}

    try:
        with open(packet_path, "r", encoding="utf-8") as f:
            packet_data = json.load(f)
    except Exception as e:
        return False, f"Failed to load packet JSON: {e}", {}

    # 2. Check approval status and scope
    status = packet_data.get("human_approval_status")
    scope = packet_data.get("approval_scope")
    if status != "APPROVED_FOR_CONTEXT_USE":
        return False, f"Packet is not approved for context use (Status: {status})", packet_data
    if scope != "CONTEXT_ONLY":
        return False, f"Packet has invalid approval scope (Scope: {scope})", packet_data

    # 3. Re-run safety review
    is_valid, issues, _ = review_packet(packet_path, output_root)
    if not is_valid:
        return False, f"Packet failed safety re-validation: {', '.join(issues)}", packet_data

    # 4. Prepare handoff data
    project_id = packet_data.get("project_id", "unknown")
    task_name = packet_data.get("task_name", "unknown")
    approved_at = packet_data.get("approved_at", "unknown")
    candidates = packet_data.get("candidates", [])
    
    candidates_list = ""
    candidates_list_short = ""
    for c in candidates:
        path = c.get("path")
        reason = c.get("reason")
        candidates_list += f"- `{path}`: {reason}\n"
        candidates_list_short += f"- `{path}`\n"

    template = HANDOFF_TEMPLATES[target]
    handoff_content = template.format(
        project_id=project_id,
        task_name=task_name,
        packet_path=packet_path.name,
        approved_at=approved_at,
        approval_scope=scope,
        candidates_list=candidates_list,
        candidates_list_short=candidates_list_short
    )

    handoff_id = f"{packet_path.stem}_{target}"
    manifest = {
        "handoff_id": handoff_id,
        "project_id": project_id,
        "task_name": task_name,
        "target_agent": target,
        "source_packet": str(packet_path),
        "source_packet_approved_at": approved_at,
        "created_at": datetime.datetime.now().isoformat(),
        "handoff_status": "DRAFT_NOT_EXECUTED",
        "execution_status": "NOT_EXECUTED",
        "approval_scope": scope,
        "candidates": candidates,
        "safety_verified": True
    }

    if not dry_run:
        handoff_dir = output_root / "handoffs"
        manifest_dir = output_root / "handoff_manifests"
        report_dir = output_root / "review_reports"
        
        handoff_dir.mkdir(parents=True, exist_ok=True)
        manifest_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        handoff_path = handoff_dir / f"{handoff_id}.md"
        manifest_path = manifest_dir / f"{handoff_id}.json"
        report_path = report_dir / f"{handoff_id}_review.md"

        with open(handoff_path, "w", encoding="utf-8") as f:
            f.write(handoff_content)
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Handoff Review Report: {handoff_id}\n\n")
            f.write(f"- **Target**: {target}\n")
            f.write(f"- **Status**: `{manifest['handoff_status']}`\n")
            f.write(f"- **Execution**: `{manifest['execution_status']}`\n\n")
            f.write("## Safety Verification\n")
            f.write("- [x] Source packet is APPROVED_FOR_CONTEXT_USE.\n")
            f.write("- [x] Approval scope is CONTEXT_ONLY.\n")
            f.write("- [x] Candidate files re-validated against risky paths.\n")
            f.write("- [x] Explicit 'DO NOT' constraints included in prompt.\n")

        return True, f"Handoff artifacts created for {target}.", manifest

    return True, "Handoff dry-run successful.", manifest
