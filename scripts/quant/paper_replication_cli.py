import argparse
import sys
import json
from pathlib import Path

# Adjust path for local imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.quant.paper_replication import (
    load_research_paper_schema,
    load_replication_plan_schema,
    validate_research_paper_record,
    validate_replication_plan,
    build_research_paper_record,
    build_replication_plan_from_inputs,
    write_research_paper_record,
    write_replication_plan,
    REPORTS_DIR
)

def print_safety_banner():
    print("\n[SAFETY BOUNDARY ENFORCED]")
    print("financial_advice_generated: false")
    print("trading_signal_generated: false")
    print("bot_logic_generated: false")
    print("live_trading_logic_generated: false")
    print("-" * 30)

def cmd_schema_check(args):
    print_safety_banner()
    try:
        paper_schema = load_research_paper_schema()
        plan_schema = load_replication_plan_schema()
        if args.json:
            print(json.dumps({"paper_schema_version": paper_schema.get("version"), "plan_schema_version": plan_schema.get("version")}))
        else:
            print("[OK] Research Paper Schema Loaded.")
            print("[OK] Replication Plan Schema Loaded.")
    except Exception as e:
        print(f"[FAIL] Schema load failed: {str(e)}")
        sys.exit(1)

def cmd_paper_intake(args):
    print_safety_banner()
    try:
        schema = load_research_paper_schema()
        
        # We need a title for the deterministic ID. If not provided, try to extract from file path.
        title = args.title if args.title else Path(args.paper_note).stem
        
        record = build_research_paper_record(
            title=title,
            source_type=args.source_type,
            local_note_file=args.paper_note
        )
        
        validate_research_paper_record(record, schema)
        
        result = write_research_paper_record(record, REPORTS_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Paper ID: {record['paper_id']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")
                
    except Exception as e:
        print(f"[FAIL] Paper Intake Failed: {str(e)}")
        sys.exit(1)

def cmd_replication_plan_draft(args):
    print_safety_banner()
    try:
        if not Path(args.paper_file).exists():
            raise FileNotFoundError(f"Paper file not found: {args.paper_file}")
            
        with open(args.paper_file, 'r', encoding='utf-8') as f:
            paper_record = json.load(f)
            
        idea_record = None
        if args.idea_file:
            if not Path(args.idea_file).exists():
                 raise FileNotFoundError(f"Idea file not found: {args.idea_file}")
            with open(args.idea_file, 'r', encoding='utf-8') as f:
                idea_record = json.load(f)

        schema = load_replication_plan_schema()
        plan = build_replication_plan_from_inputs(idea_record=idea_record, paper_record=paper_record)
        
        validate_replication_plan(plan, schema)
        
        result = write_replication_plan(plan, REPORTS_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Replication Plan ID: {plan['replication_plan_id']}")
            print(f"Linked Paper: {plan['linked_paper_id']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Replication Plan Draft Failed: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Paper Replication Scaffold")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True, help="Default dry-run behavior")
    p_schema.add_argument("--json", action="store_true")

    # paper-intake
    p_intake = subparsers.add_parser("paper-intake")
    p_intake.add_argument("--paper-note", required=True)
    p_intake.add_argument("--title", required=False)
    p_intake.add_argument("--source-type", default="manual_note", required=False)
    p_intake.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_intake.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_intake.add_argument("--json", action="store_true")

    # replication-plan-draft
    p_draft = subparsers.add_parser("replication-plan-draft")
    p_draft.add_argument("--paper-file", required=True)
    p_draft.add_argument("--idea-file", required=False)
    p_draft.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_draft.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_draft.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "paper-intake":
        cmd_paper_intake(args)
    elif args.command == "replication-plan-draft":
        cmd_replication_plan_draft(args)

if __name__ == "__main__":
    main()
