import argparse
import sys
import json
from pathlib import Path

from scripts.quant.guarded_write_executor import (
    load_guarded_write_execution_schema,
    validate_guarded_write_execution,
    evaluate_noop_guarded_write,
    write_guarded_execution_audit
)

def main():
    parser = argparse.ArgumentParser(description="Guarded Write No-Op Executor CLI (Q52)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # schema-check
    schema_parser = subparsers.add_parser("schema-check", help="Check the guarded write execution schema.")
    schema_parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run only (default).")

    # noop-execute
    noop_parser = subparsers.add_parser("noop-execute", help="Run a no-op guarded write execution.")
    noop_parser.add_argument("--approval-file", required=True, help="Path to the Human Approval Form (.md or .yaml).")
    noop_parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run (don't write audit files).")
    noop_parser.add_argument("--write-audit", action="store_true", help="Write a blocked audit file to evidence folder.")

    args = parser.parse_args()

    if args.command == "schema-check":
        try:
            schema = load_guarded_write_execution_schema()
            print("Guarded Write Execution Schema loaded successfully.")
            print(f"Version: {schema.get('version')}")
            print(f"Required Fields: {len(schema.get('required_fields', []))}")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.command == "noop-execute":
        dry_run = not args.write_audit
        try:
            exec_record, eval_result = evaluate_noop_guarded_write(args.approval_file)
            
            # Print evaluation summary
            print("--- Guarded Write No-Op Evaluation ---")
            print(f"Approval ID: {exec_record['approval_id']}")
            print(f"Approval Validation Status: {exec_record['approval_validation_status']}")
            print(f"Audit Status: {exec_record['audit_status']}")
            print(f"Future Write Enabled: {exec_record['future_write_enabled']}")
            print(f"Write Allowed: {exec_record['write_allowed']}")
            print(f"Write Performed: {exec_record['write_performed']}")
            print(f"Intended Artifact Written to Reports: false")
            print(f"Financial Advice Generated: {exec_record['safety_financial_advice_generated']}")
            print(f"Trading Signal Generated: {exec_record['safety_trading_signal_generated']}")
            print(f"Bot Logic Generated: {exec_record['safety_bot_logic_generated']}")
            print(f"Live Trading Logic Generated: {exec_record['safety_live_trading_logic_generated']}")
            print(f"Real Backtest Run: {exec_record['safety_backtest_run']}")
            
            if exec_record['blocking_issues'] != "None":
                print(f"Blocking Issues: {exec_record['blocking_issues']}")

            if args.write_audit:
                result = write_guarded_execution_audit(exec_record, dry_run=False)
                print(f"Audit file written: {result['json_path']}")
                print(f"Audit report written: {result['md_path']}")
            else:
                print("Dry-run: No audit files written.")
            
            sys.exit(0)
        except Exception as e:
            print(f"Execution Error: {e}")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
