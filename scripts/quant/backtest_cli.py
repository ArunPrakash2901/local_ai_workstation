import argparse
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.quant.backtest_plan import (
    load_backtest_plan_schema,
    validate_backtest_plan,
    build_backtest_plan_from_handoff,
    write_backtest_plan,
    REPORTS_DIR as PLAN_DIR
)
from scripts.quant.backtest_engine import (
    validate_synthetic_price_fixture,
    run_synthetic_no_strategy_smoke_test,
    compute_basic_result_metrics
)
from scripts.quant.backtest_result_manifest import (
    load_backtest_result_manifest_schema,
    validate_backtest_result_manifest,
    build_synthetic_smoke_result_manifest,
    write_backtest_result_manifest,
    REPORTS_DIR as RES_DIR
)

def print_safety_banner():
    print("\n[SAFETY BOUNDARY ENFORCED]")
    print("financial_advice_generated: false")
    print("trading_signal_generated: false")
    print("bot_logic_generated: false")
    print("live_trading_logic_generated: false")
    print("real_strategy_backtest_run: false")
    print("-" * 30)

def cmd_schema_check(args):
    print_safety_banner()
    try:
        p_schema = load_backtest_plan_schema()
        r_schema = load_backtest_result_manifest_schema()
        if args.json:
            print(json.dumps({
                "plan": p_schema.get("version"),
                "result": r_schema.get("version")
            }))
        else:
            print("[OK] Backtest Plan Schema Loaded.")
            print("[OK] Backtest Result Manifest Schema Loaded.")
    except Exception as e:
        print(f"[FAIL] Schema load failed: {str(e)}")
        sys.exit(1)

def load_json_record(filepath):
    if not filepath or not Path(filepath).exists():
        raise FileNotFoundError(f"Record not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def cmd_plan_draft(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        rdy_record = load_json_record(args.readiness_file)
        
        # Load handoff if exists; else mock it for dry run evaluation purposes
        hof_record = {"handoff_id": "UNKNOWN"}
        if args.handoff_file and Path(args.handoff_file).exists():
             hof_record = load_json_record(args.handoff_file)

        schema = load_backtest_plan_schema()
        record = build_backtest_plan_from_handoff(
            candidate_record=cand_record,
            readiness_record=rdy_record,
            handoff_record=hof_record
        )
        
        validate_backtest_plan(record, schema)
        result = write_backtest_plan(record, PLAN_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Plan ID: {record['backtest_plan_id']}")
            print(f"Status: {record['plan_status']}")
            print(f"Path: {result['path']}")
            if record['plan_status'] == 'blocked':
                 print("[WARNING] Candidate readiness is incomplete. Plan is BLOCKED.")
            if args.dry_run:
                print("Run with --write to save.")
                
    except Exception as e:
        print(f"[FAIL] Plan Draft Failed: {str(e)}")
        sys.exit(1)

def cmd_synthetic_smoke(args):
    print_safety_banner()
    print("synthetic_fixture_only: true\n")
    try:
        fixture_data = load_json_record(args.fixture)
        validate_synthetic_price_fixture(fixture_data)
        
        # Run skeleton engine
        smoke_result = run_synthetic_no_strategy_smoke_test(fixture_data['rows'])
        metrics = compute_basic_result_metrics(smoke_result['equity_curve'])
        smoke_result['metrics'] = metrics
        
        # Manifest
        schema = load_backtest_result_manifest_schema()
        manifest = build_synthetic_smoke_result_manifest(smoke_result)
        validate_backtest_result_manifest(manifest, schema)
        
        result = write_backtest_result_manifest(manifest, RES_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Synthetic Result ID: {manifest['result_manifest_id']}")
            print(f"Metrics: {metrics}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Synthetic Smoke Test Failed: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Q9-Q11 Backtest Skeleton")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True)
    p_schema.add_argument("--json", action="store_true")

    # plan-draft
    p_plan = subparsers.add_parser("plan-draft")
    p_plan.add_argument("--candidate-file", required=True)
    p_plan.add_argument("--readiness-file", required=True)
    p_plan.add_argument("--handoff-file", required=False)
    p_plan.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_plan.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_plan.add_argument("--json", action="store_true")

    # synthetic-smoke
    p_smoke = subparsers.add_parser("synthetic-smoke")
    p_smoke.add_argument("--fixture", required=True)
    p_smoke.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_smoke.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_smoke.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "plan-draft":
        cmd_plan_draft(args)
    elif args.command == "synthetic-smoke":
        cmd_synthetic_smoke(args)

if __name__ == "__main__":
    main()
