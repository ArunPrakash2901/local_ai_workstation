import argparse
import sys
import json
from pathlib import Path
from write_approval_prepare import (
    validate_approved_source_input_path,
    build_approval_draft_record,
    write_approval_draft,
    build_evidence_pack,
    write_evidence_pack
)

def main():
    parser = argparse.ArgumentParser(description="Prepare a draft human write approval for Quant research.")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")
    
    # prepare-idea-intake-approval
    prep_parser = subparsers.add_subparsers(dest="subcommand", help="Action to perform")
    idea_parser = subparsers.add_parser("prepare-idea-intake-approval", help="Prepare an idea intake approval")
    idea_parser.add_argument("--title", required=True, help="Title of the research idea")
    idea_parser.add_argument("--source-type", required=True, help="Source type (e.g., human_note)")
    idea_parser.add_argument("--idea-file", required=True, help="Path to the idea markdown file")
    idea_parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run only (default)")
    idea_parser.add_argument("--write-draft", action="store_true", help="Write the draft approval and evidence pack")
    idea_parser.add_argument("--operator", default="Operator-01", help="Operator name")
    idea_parser.add_argument("--force", action="store_true", help="Overwrite existing draft/evidence")

    args = parser.parse_args()

    if args.command == "prepare-idea-intake-approval":
        # Note: If no subcommands are used, parser.parse_args() might put it in args.command
        pass
    elif not args.command:
        # Fallback if someone just runs the script with args directly (if subparsers not used correctly)
        # But here I used subparsers.
        pass

    # Handle the specific command
    # Re-parsing because of how I set up subparsers above might be tricky if not careful.
    # Let's fix the parser structure.
    
def fix_parser():
    parser = argparse.ArgumentParser(description="Prepare a draft human write approval for Quant research.")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")
    
    idea_parser = subparsers.add_parser("prepare-idea-intake-approval", help="Prepare an idea intake approval")
    idea_parser.add_argument("--title", required=True, help="Title of the research idea")
    idea_parser.add_argument("--source-type", required=True, help="Source type (e.g., human_note)")
    idea_parser.add_argument("--idea-file", required=True, help="Path to the idea markdown file")
    idea_parser.add_argument("--dry-run", action="store_true", default=False, help="Dry run only")
    idea_parser.add_argument("--write-draft", action="store_true", help="Write the draft approval and evidence pack")
    idea_parser.add_argument("--operator", default="Operator-01", help="Operator name")
    idea_parser.add_argument("--force", action="store_true", help="Overwrite existing draft/evidence")
    
    return parser

def run():
    parser = fix_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Default to dry-run if neither is specified or if --dry-run is True
    is_dry_run = True
    if args.write_draft and not args.dry_run:
        is_dry_run = False

    try:
        if args.command == "prepare-idea-intake-approval":
            validate_approved_source_input_path(args.idea_file)
            
            record = build_approval_draft_record(
                title=args.title,
                source_type=args.source_type,
                idea_file=args.idea_file,
                operator_name=args.operator
            )
            
            evidence = build_evidence_pack(record)
            
            draft_result = write_approval_draft(record, dry_run=is_dry_run, force=args.force)
            evidence_result = write_evidence_pack(evidence, record["approval_id"], dry_run=is_dry_run, force=args.force)
            
            print("--- Preparation Result ---")
            print(f"Approval ID: {record['approval_id']}")
            print(f"Draft Status: {draft_result['status']}")
            print(f"Draft Path: {draft_result['path']}")
            print(f"Evidence Status: {evidence_result['status']}")
            print(f"Evidence Path: {evidence_result['path']}")
            print("\n--- Safety Frame ---")
            print("approval_granted: false")
            print("write_mode_enabled: false")
            print("artifact_written_to_reports: false")
            print("financial_advice_generated: false")
            print("trading_signal_generated: false")
            print("bot_logic_generated: false")
            print("live_trading_logic_generated: false")
            print("real_backtest_run: false")
            
            if is_dry_run:
                print("\n[DRY RUN] No files were written. Use --write-draft to create artifacts in scratch/.")
            else:
                print("\n[SUCCESS] Draft approval and evidence pack written to scratch/quant_approvals/.")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run()
