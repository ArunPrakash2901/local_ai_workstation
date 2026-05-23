import argparse
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.quant.synthetic_execution_runner import (
    load_synthetic_execution_run_schema,
    validate_synthetic_execution_run,
    build_synthetic_execution_run,
    write_synthetic_execution_run,
    REPORTS_DIR as SYN_DIR
)
from scripts.quant.synthetic_result_review import (
    load_synthetic_result_review_schema,
    validate_synthetic_result_review,
    build_synthetic_result_review,
    write_synthetic_result_review,
    REPORTS_DIR as SRV_DIR
)

def print_safety_banner():
    print("\n[SAFETY BOUNDARY ENFORCED]")
    print("financial_advice_generated: false")
    print("trading_signal_generated: false")
    print("bot_logic_generated: false")
    print("live_trading_logic_generated: false")
    print("real_strategy_backtest_run: false")
    print("candidate_strategy_executed: false")
    print("synthetic_fixture_only: true")
    print("-" * 30)

def load_json_record(filepath):
    if not filepath or not Path(filepath).exists():
        raise FileNotFoundError(f"Record not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def cmd_schema_check(args):
    print_safety_banner()
    try:
        s_schema = load_synthetic_execution_run_schema()
        r_schema = load_synthetic_result_review_schema()
        if args.json:
            print(json.dumps({
                "synthetic_run": s_schema.get("version"),
                "synthetic_review": r_schema.get("version")
            }))
        else:
            print("[OK] Synthetic Execution Run Schema Loaded.")
            print("[OK] Synthetic Result Review Schema Loaded.")
    except Exception as e:
        print(f"[FAIL] Schema load failed: {str(e)}")
        sys.exit(1)

def cmd_run_synthetic(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        
        # Preflight is optional for this CLI command but recommended
        preflight_record = None
        if args.preflight_file:
            preflight_record = load_json_record(args.preflight_file)

        schema = load_synthetic_execution_run_schema()
        record = build_synthetic_execution_run(
            candidate_record=cand_record,
            fixture_path=args.fixture,
            preflight_record=preflight_record
        )
        
        validate_synthetic_execution_run(record, schema)
        result = write_synthetic_execution_run(record, SYN_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Synthetic Run ID: {record['synthetic_run_id']}")
            print(f"Metrics: {record['metrics']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Synthetic Run Failed: {str(e)}")
        sys.exit(1)

def cmd_review_synthetic(args):
    print_safety_banner()
    try:
        run_record = load_json_record(args.synthetic_run_file)
        
        schema = load_synthetic_result_review_schema()
        record = build_synthetic_result_review(run_record)
        
        validate_synthetic_result_review(record, schema)
        result = write_synthetic_result_review(record, SRV_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Synthetic Review ID: {record['synthetic_review_id']}")
            print(f"Status: {record['review_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Synthetic Review Failed: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Q27-Q29 Synthetic Execution Simulation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True)
    p_schema.add_argument("--json", action="store_true")

    # run-synthetic
    p_run = subparsers.add_parser("run-synthetic")
    p_run.add_argument("--candidate-file", required=True)
    p_run.add_argument("--fixture", required=True)
    p_run.add_argument("--preflight-file", required=False)
    p_run.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_run.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_run.add_argument("--json", action="store_true")

    # review-synthetic
    p_rev = subparsers.add_parser("review-synthetic")
    p_rev.add_argument("--synthetic-run-file", required=True)
    p_rev.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_rev.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_rev.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "run-synthetic":
        cmd_run_synthetic(args)
    elif args.command == "review-synthetic":
        cmd_review_synthetic(args)

if __name__ == "__main__":
    main()
