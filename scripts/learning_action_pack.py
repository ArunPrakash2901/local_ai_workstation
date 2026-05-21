#!/usr/bin/env python3
"""Learning Dry-Run Action Pack v1 - Core Logic."""

import json
import sys
import os
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime

@dataclass
class LearningAction:
    action_id: str
    action_type: str
    title: str
    rationale: str
    proposed_effect: str
    safety_class: str
    requires_confirmation: bool = True
    status: str = "DRY_RUN_ONLY"
    evidence: str = ""
    warnings: list[str] = field(default_factory=list)

def generate_action_id(stronghold_id: str, action_type: str, evidence: str) -> str:
    """Generate a deterministic action ID."""
    prefix_map = {
        "CREATE_STUDY_TASK_DRY_RUN": "LT",
        "SUMMARIZE_SESSION_DRY_RUN": "LS",
        "PROPOSE_NEXT_LESSON_DRY_RUN": "LN",
        "MARK_REVIEW_NEEDED_DRY_RUN": "LR",
        "ASSESS_ADVANCEMENT_READINESS_DRY_RUN": "LA",
        "DETECT_STALE_LEARNING_ARTIFACTS_DRY_RUN": "LD",
    }
    prefix = prefix_map.get(action_type, "LX")
    # Use MD5 for a short stable hash
    payload = f"{stronghold_id}:{action_type}:{evidence}".encode("utf-8")
    h = hashlib.md5(payload).hexdigest()[:8].upper()
    return f"{prefix}-{h}"

def get_learning_strongholds(strongholds_dir: Path):
    learning_dir = strongholds_dir / "learning"
    if not learning_dir.is_dir():
        return []
    return [d for d in learning_dir.iterdir() if d.is_dir() and (d / "state.json").is_file()]

def load_state(stronghold_dir: Path):
    state_path = stronghold_dir / "state.json"
    if not state_path.is_file():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None

def generate_actions(stronghold_dir: Path, state: dict):
    actions = []
    sid = stronghold_dir.name
    
    # 1. CREATE_STUDY_TASK_DRY_RUN
    next_task = state.get("next_learning_task", "None")
    evidence_1 = f"next_learning_task: {next_task}"
    actions.append(LearningAction(
        action_id=generate_action_id(sid, "CREATE_STUDY_TASK_DRY_RUN", evidence_1),
        action_type="CREATE_STUDY_TASK_DRY_RUN",
        title=f"Propose Study Task: {next_task}",
        rationale=f"Next task in syllabus is: {next_task}",
        proposed_effect=f"Would create a new study session for: {next_task}",
        safety_class="DRY_RUN_ONLY",
        evidence=evidence_1
    ))

    # 2. SUMMARIZE_SESSION_DRY_RUN
    last_session = state.get("last_tutor_session_path", "None")
    evidence_2 = f"last_tutor_session_path: {last_session}"
    actions.append(LearningAction(
        action_id=generate_action_id(sid, "SUMMARIZE_SESSION_DRY_RUN", evidence_2),
        action_type="SUMMARIZE_SESSION_DRY_RUN",
        title="Propose Session Summary",
        rationale=f"Last session completed: {Path(last_session).name if last_session != 'None' else 'None'}",
        proposed_effect="Would generate a summary artifact for the last learning session.",
        safety_class="DRY_RUN_ONLY",
        evidence=evidence_2
    ))

    # 3. PROPOSE_NEXT_LESSON_DRY_RUN
    evidence_3 = f"current_state: {state.get('current_state')}"
    actions.append(LearningAction(
        action_id=generate_action_id(sid, "PROPOSE_NEXT_LESSON_DRY_RUN", evidence_3),
        action_type="PROPOSE_NEXT_LESSON_DRY_RUN",
        title="Suggest Next Lesson Step",
        rationale="Based on current progress and last assessment.",
        proposed_effect="Would update the next_learning_task field in state.json.",
        safety_class="DRY_RUN_ONLY",
        evidence=evidence_3
    ))

    # 4. MARK_REVIEW_NEEDED_DRY_RUN
    last_decision = state.get("last_learning_decision")
    needs_review = last_decision == "REVIEW_CURRENT_TASK"
    evidence_4 = f"last_learning_decision: {last_decision}"
    actions.append(LearningAction(
        action_id=generate_action_id(sid, "MARK_REVIEW_NEEDED_DRY_RUN", evidence_4),
        action_type="MARK_REVIEW_NEEDED_DRY_RUN",
        title="Propose Topic Review",
        rationale="Last decision indicated a review is required." if needs_review else "Topic appears stable, but periodic review is recommended.",
        proposed_effect="Would flag the current topic for a review session.",
        safety_class="DRY_RUN_ONLY",
        evidence=evidence_4
    ))

    # 5. ASSESS_ADVANCEMENT_READINESS_DRY_RUN
    last_completed = state.get("last_completed_learning_task", "None")
    evidence_5 = f"last_completed_learning_task: {last_completed}"
    actions.append(LearningAction(
        action_id=generate_action_id(sid, "ASSESS_ADVANCEMENT_READINESS_DRY_RUN", evidence_5),
        action_type="ASSESS_ADVANCEMENT_READINESS_DRY_RUN",
        title="Generate Advancement Checklist",
        rationale=f"Last completed task: {last_completed}. Checking if advancement to next module is safe.",
        proposed_effect="Would generate a markdown checklist of evidence for advancement.",
        safety_class="PURE_READ",
        evidence=evidence_5
    ))

    # 6. DETECT_STALE_LEARNING_ARTIFACTS_DRY_RUN
    # Simple check for files older than 7 days in sessions or assessments
    stale_count = 0
    for folder in ["sessions", "assessments"]:
        p = stronghold_dir / folder
        if p.is_dir():
            for f in p.iterdir():
                if f.is_file() and (datetime.now().timestamp() - f.stat().st_mtime) > 7 * 24 * 3600:
                    stale_count += 1
    
    evidence_6 = f"Stale file count: {stale_count}"
    actions.append(LearningAction(
        action_id=generate_action_id(sid, "DETECT_STALE_LEARNING_ARTIFACTS_DRY_RUN", evidence_6),
        action_type="DETECT_STALE_LEARNING_ARTIFACTS_DRY_RUN",
        title=f"Identify {stale_count} Stale Artifacts",
        rationale=f"Found {stale_count} files older than 7 days.",
        proposed_effect="Would list or archive stale learning session artifacts.",
        safety_class="PURE_READ",
        evidence=evidence_6
    ))

    return actions

def main():
    if "--dry-run" not in sys.argv:
        print("Error: This tool currently only supports --dry-run mode.")
        sys.exit(1)

    ws_home = Path(os.environ.get("WS_HOME", "/mnt/d/_ai_brain"))
    strongholds_dir = ws_home / "strongholds"
    
    stronghold_id = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            stronghold_id = arg
            break
            
    if not stronghold_id:
        print("Error: No stronghold ID provided.")
        sys.exit(1)
        
    stronghold_dir = strongholds_dir / "learning" / stronghold_id
    if not stronghold_dir.is_dir():
        # Try finding it in strongholds directly if it's a full path or absolute
        try:
            p = Path(stronghold_id)
            if p.is_dir() and (p / "state.json").is_file():
                stronghold_dir = p
            else:
                print(f"Error: Stronghold not found at {stronghold_dir}")
                sys.exit(1)
        except Exception:
            print(f"Error: Stronghold not found at {stronghold_dir}")
            sys.exit(1)

    state = load_state(stronghold_dir)
    if not state:
        if "--json" in sys.argv:
            print(json.dumps({"error": f"Could not load state.json for {stronghold_id}"}))
        else:
            print(f"Error: Could not load state.json for {stronghold_id}")
        sys.exit(1)
        
    if state.get("type") != "learning":
        if "--json" in sys.argv:
            print(json.dumps({"error": f"Stronghold {stronghold_id} is not of type 'learning'"}))
        else:
            print(f"Error: Stronghold {stronghold_id} is not of type 'learning'")
        sys.exit(1)

    actions = generate_actions(stronghold_dir, state)
    
    if "--json" in sys.argv:
        print(json.dumps([asdict(a) for a in actions], indent=2))
        return

    print(f"Learning Dry-Run Action Pack v1 for: {state.get('title')}")
    print("=" * 60)
    for action in actions:
        print(f"Action ID:       {action.action_id}")
        print(f"Type:            {action.action_type}")
        print(f"Title:           {action.title}")
        print(f"Rationale:       {action.rationale}")
        print(f"Proposed Effect: {action.proposed_effect}")
        print(f"Safety Class:    {action.safety_class}")
        print(f"Status:          {action.status}")
        if action.evidence:
            print(f"Evidence:        {action.evidence}")
        if action.warnings:
            print(f"Warnings:        {', '.join(action.warnings)}")
        print("-" * 60)

if __name__ == "__main__":
    main()
else:
    # Allow importing for reuse in confirmation core
    pass
