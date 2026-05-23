import argparse
import sys
import json
from pathlib import Path

# Adjust path for local imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.quant.idea_intake import (
    load_research_idea_schema,
    validate_research_idea_record,
    build_research_idea_record,
    write_research_idea_record,
    REPORTS_DIR
)

from scripts.quant.hypothesis_contract import (
    load_hypothesis_contract_schema,
    validate_hypothesis_contract,
    build_hypothesis_contract_from_idea,
    write_hypothesis_contract
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
        idea_schema = load_research_idea_schema()
        hyp_schema = load_hypothesis_contract_schema()
        if args.json:
            print(json.dumps({"idea_schema_version": idea_schema.get("version"), "hypothesis_schema_version": hyp_schema.get("version")}))
        else:
            print("[OK] Research Idea Schema Loaded.")
            print("[OK] Hypothesis Contract Schema Loaded.")
    except Exception as e:
        print(f"[FAIL] Schema load failed: {str(e)}")
        sys.exit(1)

def validate_idea_file_path(file_path_str):
    path = Path(file_path_str).resolve()
    base_dir = Path(__file__).resolve().parent.parent.parent
    
    scratch_dir = (base_dir / "scratch" / "quant_ideas").resolve()
    reports_dir = (base_dir / "reports" / "quant" / "research_ideas" / "inputs").resolve()

    if scratch_dir not in path.parents and reports_dir not in path.parents:
        raise ValueError(f"Path must be within scratch/quant_ideas/ or reports/quant/research_ideas/inputs/. Got: {file_path_str}")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Idea file not found or is not a file: {file_path_str}")

    if path.stat().st_size > 50 * 1024:
        raise ValueError(f"Idea file exceeds maximum allowed size of 50KB: {file_path_str}")

    return path

def cmd_idea_intake(args):
    print_safety_banner()
    try:
        if args.raw_idea and args.idea_file:
            raise ValueError("Cannot provide both --raw-idea and --idea-file. Choose one.")
        if not args.raw_idea and not args.idea_file:
            raise ValueError("Must provide either --raw-idea or --idea-file.")

        raw_idea_text = args.raw_idea
        if args.idea_file:
            validated_path = validate_idea_file_path(args.idea_file)
            with open(validated_path, 'r', encoding='utf-8') as f:
                raw_idea_text = f.read()

        schema = load_research_idea_schema()
        
        record = build_research_idea_record(
            title=args.title,
            source_type=args.source_type,
            raw_idea_text=raw_idea_text
        )
        
        validate_research_idea_record(record, schema)
        
        result = write_research_idea_record(record, REPORTS_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Idea ID: {record['idea_id']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")
                
    except Exception as e:
        print(f"[FAIL] Idea Intake Failed: {str(e)}")
        sys.exit(1)

def cmd_hypothesis_draft(args):
    print_safety_banner()
    try:
        if not Path(args.idea_file).exists():
            raise FileNotFoundError(f"Idea file not found: {args.idea_file}")
            
        with open(args.idea_file, 'r', encoding='utf-8') as f:
            idea_record = json.load(f)
            
        schema = load_hypothesis_contract_schema()
        contract = build_hypothesis_contract_from_idea(idea_record)
        
        validate_hypothesis_contract(contract, schema)
        
        result = write_hypothesis_contract(contract, REPORTS_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Hypothesis ID: {contract['hypothesis_id']}")
            print(f"Linked Idea: {contract['linked_idea_id']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Hypothesis Draft Failed: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Idea Intake & Hypothesis Generation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True, help="Default dry-run behavior")
    p_schema.add_argument("--json", action="store_true")

    # idea-intake
    p_intake = subparsers.add_parser("idea-intake")
    p_intake.add_argument("--title", required=True)
    p_intake.add_argument("--source-type", required=True)
    p_intake.add_argument("--raw-idea", required=False)
    p_intake.add_argument("--idea-file", required=False)
    p_intake.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_intake.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_intake.add_argument("--json", action="store_true")

    # hypothesis-draft
    p_draft = subparsers.add_parser("hypothesis-draft")
    p_draft.add_argument("--idea-file", required=True)
    p_draft.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_draft.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_draft.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "idea-intake":
        cmd_idea_intake(args)
    elif args.command == "hypothesis-draft":
        cmd_hypothesis_draft(args)

if __name__ == "__main__":
    main()
