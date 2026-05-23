#!/usr/bin/env python3
"""Learning Review Packet Checklist State Layer v1."""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

def get_utc_now() -> str:
    return datetime.now().strftime('%Y%m%dT%H%M%SZ')

def load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def append_audit(path: Path, entry: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def extract_checklist_items(packet_path: Path) -> List[str]:
    if not packet_path.is_file():
        return []
    
    content = packet_path.read_text(encoding="utf-8")
    
    # Try to find the "## 6. Required Human Checks" section
    section_match = re.search(r"## 6\. Required Human Checks\n(.*?)(?:\n##|$)", content, re.DOTALL)
    if section_match:
        items_raw = section_match.group(1).strip()
        items = re.findall(r"- \[ \] (.*)", items_raw)
        if items:
            return [i.strip() for i in items]
            
    return []

def get_fallback_items(state: Dict[str, Any]) -> List[str]:
    next_task = state.get("next_learning_task", "the next task")
    current_state = state.get("current_state", "the current state")
    return [
        "Verify the learner has completed the current task.",
        f"Verify the '{next_task}' task is actually done.",
        "Verify outputs or artifacts exist.",
        "Verify no unresolved blockers remain.",
        f"Decide whether current_state should remain {current_state}.",
        "Decide whether a future advancement phase is appropriate."
    ]

def main():
    parser = argparse.ArgumentParser(description="Learning Review Packet Checklist State Layer v1")
    parser.add_argument("stronghold_id", help="Stronghold ID")
    parser.add_argument("--packet-id", required=True, help="Packet ID")
    parser.add_argument("--dry-run-init", action="store_true", help="Preview checklist initialization")
    parser.add_argument("--init-checklist", action="store_true", help="Initialize checklist state")
    parser.add_argument("--show", action="store_true", help="Show checklist state")
    parser.add_argument("--json", action="store_true", help="Output as pure JSON")
    
    args = parser.parse_args()
    
    modes = [args.dry_run_init, args.init_checklist, args.show]
    if sum(modes) != 1:
        error_msg = "Error: Exactly one mode must be provided: --dry-run-init, --init-checklist, or --show."
        if args.json:
            print(json.dumps({"error": error_msg, "status": "FAILED"}))
        else:
            print(error_msg)
        sys.exit(1)

    ws_home = Path(os.environ.get("WS_HOME", "D:\\_ai_brain" if os.name == 'nt' else "/mnt/d/_ai_brain"))
    stronghold_dir = ws_home / "strongholds" / "learning" / args.stronghold_id
    
    if not stronghold_dir.is_dir():
        error_msg = f"Error: Stronghold directory not found: {stronghold_dir}"
        if args.json:
            print(json.dumps({"error": error_msg, "status": "FAILED"}))
        else:
            print(error_msg)
        sys.exit(1)

    # Locate packet
    packet_dir = stronghold_dir / "review_packets"
    packet_path = None
    if packet_dir.is_dir():
        for f in packet_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            if f"Packet ID: {args.packet_id}" in content:
                packet_path = f
                break
                
    if not packet_path:
        error_msg = f"Error: Packet ID {args.packet_id} not found in {packet_dir}"
        if args.json:
            print(json.dumps({"error": error_msg, "status": "FAILED"}))
        else:
            print(error_msg)
        sys.exit(1)

    checklist_dir = stronghold_dir / "review_checklists"
    checklist_path = checklist_dir / f"{args.packet_id}_checklist.json"
    audit_path = checklist_dir / "checklist_audit.jsonl"
    
    safety_boundary = [
        "review packet was not modified",
        "state.json was not modified",
        "current_state was not modified",
        "next_learning_task was not modified",
        "advancement remains manual"
    ]

    if args.dry_run_init:
        items_extracted = extract_checklist_items(packet_path)
        source_type = "packet" if items_extracted else "fallback"
        
        if not items_extracted:
            state = load_json(stronghold_dir / "state.json") or {}
            items_extracted = get_fallback_items(state)
            
        plan = {
            "status": "DRY_RUN",
            "stronghold_id": args.stronghold_id,
            "packet_id": args.packet_id,
            "packet_path": str(packet_path),
            "checklist_path": str(checklist_path),
            "audit_path": str(audit_path),
            "item_source": source_type,
            "item_count": len(items_extracted),
            "items": items_extracted,
            "safety_boundary": safety_boundary
        }
        
        if args.json:
            print(json.dumps(plan, indent=2))
        else:
            print(f"DRY-RUN Initialization Preview for {args.packet_id}")
            print("-" * 40)
            print(f"Stronghold: {args.stronghold_id}")
            print(f"Packet Path: {packet_path}")
            print(f"Checklist Path: {checklist_path}")
            print(f"Audit Path: {audit_path}")
            print(f"Item Source: {source_type}")
            print("\nExtracted Items:")
            for i, item in enumerate(items_extracted, 1):
                print(f"{i}. [ ] {item}")
            print("\nSafety Boundary:")
            for s in safety_boundary:
                print(f"- {s}")
            print("\nDRY-RUN ONLY: No files were written.")

    elif args.init_checklist:
        if checklist_path.is_file():
            error_msg = f"Error: Checklist state already exists for {args.packet_id} at {checklist_path}"
            if args.json:
                print(json.dumps({"error": error_msg, "status": "FAILED"}))
            else:
                print(error_msg)
            sys.exit(1)
            
        items_text = extract_checklist_items(packet_path)
        source_type = "packet" if items_text else "fallback"
        
        if not items_text:
            state = load_json(stronghold_dir / "state.json") or {}
            items_text = get_fallback_items(state)
            
        now = get_utc_now()
        checklist_id = f"CHECKLIST-{now}"
        
        items = []
        for i, text in enumerate(items_text, 1):
            items.append({
                "item_id": f"ITEM-{i:03d}",
                "text": text,
                "status": "PENDING",
                "source": source_type,
                "created_at_utc": now
            })
            
        checklist_data = {
            "checklist_id": checklist_id,
            "packet_id": args.packet_id,
            "packet_path": str(packet_path),
            "stronghold_id": args.stronghold_id,
            "source": "learning_review_checklist_state_v1",
            "created_at_utc": now,
            "updated_at_utc": now,
            "status": "INITIALIZED",
            "items": items,
            "warnings": [],
            "safety_boundary": safety_boundary
        }
        
        write_json(checklist_path, checklist_data)
        
        audit_entry = {
            "audit_id": f"AUDIT-{now}",
            "timestamp_utc": now,
            "stronghold_id": args.stronghold_id,
            "packet_id": args.packet_id,
            "checklist_id": checklist_id,
            "action": "INIT_CHECKLIST",
            "checklist_path": str(checklist_path),
            "packet_path": str(packet_path),
            "item_count": len(items),
            "confirmation_status": "CHECKLIST_INITIALIZED",
            "safety_boundary": safety_boundary
        }
        
        append_audit(audit_path, audit_entry)
        
        if args.json:
            print(json.dumps({
                "status": "SUCCESS",
                "checklist_id": checklist_id,
                "checklist_path": str(checklist_path),
                "audit_path": str(audit_path),
                "item_count": len(items)
            }, indent=2))
        else:
            print(f"Checklist initialized for {args.packet_id}")
            print(f"ID: {checklist_id}")
            print(f"Path: {checklist_path}")
            print(f"Items: {len(items)}")
            print("Audit record appended to checklist_audit.jsonl")

    elif args.show:
        if not checklist_path.is_file():
            error_msg = f"Error: No checklist state found for {args.packet_id}"
            if args.json:
                print(json.dumps({"error": error_msg, "status": "FAILED"}))
            else:
                print(error_msg)
            sys.exit(1)
            
        checklist_data = load_json(checklist_path)
        if not checklist_data:
            error_msg = f"Error: Could not load checklist data from {checklist_path}"
            if args.json:
                print(json.dumps({"error": error_msg, "status": "FAILED"}))
            else:
                print(error_msg)
            sys.exit(1)
            
        if args.json:
            print(json.dumps(checklist_data, indent=2))
        else:
            items = checklist_data.get("items", [])
            pending_count = len([i for i in items if i.get("status") == "PENDING"])
            
            print(f"Checklist State for {args.packet_id}")
            print("-" * 40)
            print(f"Checklist ID: {checklist_data.get('checklist_id')}")
            print(f"Status:       {checklist_data.get('status')}")
            print(f"Created At:   {checklist_data.get('created_at_utc')}")
            print(f"Updated At:   {checklist_data.get('updated_at_utc')}")
            print(f"Item Count:   {len(items)}")
            print(f"Pending:      {pending_count}")
            print("\nItems:")
            for item in items:
                status_box = "[ ]" if item.get("status") == "PENDING" else "[X]"
                print(f"{item.get('item_id')}: {status_box} {item.get('text')}")
            
            if checklist_data.get("warnings"):
                print("\nWarnings:")
                for w in checklist_data["warnings"]:
                    print(f"- {w}")
            
            print("\nSafety Boundary:")
            for s in checklist_data.get("safety_boundary", []):
                print(f"- {s}")

if __name__ == "__main__":
    main()
