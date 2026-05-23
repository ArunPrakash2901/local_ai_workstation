import argparse
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.quant.pre_backtest_readiness import (
    evaluate_strategy_candidate_readiness,
    validate_pre_backtest_readiness,
    load_pre_backtest_readiness_schema,
    write_pre_backtest_readiness,
    REPORTS_DIR as RDY_DIR
)
from scripts.quant.backtest_plan import (
    load_backtest_plan_schema,
    validate_backtest_plan,
    build_backtest_plan_from_handoff,
    write_backtest_plan,
    REPORTS_DIR as PLAN_DIR
)
from scripts.quant.backtest_approval_validation import (
    load_backtest_approval_validation_schema,
    validate_backtest_approval_validation,
    build_backtest_approval_validation,
    write_backtest_approval_validation,
    REPORTS_DIR as VLD_DIR
)
from scripts.quant.backtest_eligibility import (
    load_backtest_eligibility_report_schema,
    validate_backtest_eligibility_report,
    build_backtest_eligibility_report,
    write_backtest_eligibility_report,
    REPORTS_DIR as ELG_DIR
)

def print_safety_banner():
    print("\n[SAFETY BOUNDARY ENFORCED]")
    print("financial_advice_generated: false")
    print("trading_signal_generated: false")
    print("bot_logic_generated: false")
    print("live_trading_logic_generated: false")
    print("backtest_run: false")
    print("approval_granted: false")
    print("data_downloaded: false")
    print("-" * 30)

def load_json_record(filepath):
    if not filepath or not Path(filepath).exists():
        raise FileNotFoundError(f"Record not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def cmd_schema_check(args):
    print_safety_banner()
    try:
        v_schema = load_backtest_approval_validation_schema()
        e_schema = load_backtest_eligibility_report_schema()
        if args.json:
            print(json.dumps({
                "approval_vld": v_schema.get("version"),
                "eligibility": e_schema.get("version")
            }))
        else:
            print("[OK] Approval Validation Schema Loaded.")
            print("[OK] Eligibility Report Schema Loaded.")
    except Exception as e:
        print(f"[FAIL] Schema load failed: {str(e)}")
        sys.exit(1)

def cmd_readiness_recheck(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        schema = load_pre_backtest_readiness_schema()
        
        record = evaluate_strategy_candidate_readiness(cand_record)
        validate_pre_backtest_readiness(record, schema)
        
        # ID logic to avoid overwrite
        if not record['readiness_id'].endswith("-R2"):
             record['readiness_id'] = record['readiness_id'] + "-R2"
        
        result = write_pre_backtest_readiness(record, RDY_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Readiness Recheck ID: {record['readiness_id']}")
            print(f"Status: {record['readiness_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Readiness Recheck Failed: {str(e)}")
        sys.exit(1)

def cmd_plan_rebuild(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        rdy_record = load_json_record(args.readiness_file)
        dsd_record = load_json_record(args.data_source_decision_file) if args.data_source_decision_file else None
        
        schema = load_backtest_plan_schema()
        # Mock handoff since we are rebuilding from R2 directly
        hof_record = {"handoff_id": "UNKNOWN"}
        
        record = build_backtest_plan_from_handoff(
            candidate_record=cand_record,
            readiness_record=rdy_record,
            handoff_record=hof_record
        )
        
        # Override plan ID to denote rebuild
        if not record['backtest_plan_id'].endswith("-R2"):
             record['backtest_plan_id'] = record['backtest_plan_id'] + "-R2"

        # Apply DSD logic: if no data, block plan
        if not dsd_record or dsd_record.get('decision_status') != 'selected_for_future_data_adapter_review':
             record['plan_status'] = "blocked"

        validate_backtest_plan(record, schema)
        result = write_backtest_plan(record, PLAN_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Plan Rebuild ID: {record['backtest_plan_id']}")
            print(f"Status: {record['plan_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Plan Rebuild Failed: {str(e)}")
        sys.exit(1)

def cmd_approval_validate(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        rdy_record = load_json_record(args.readiness_file)
        btp_record = load_json_record(args.backtest_plan_file)
        dsd_record = load_json_record(args.data_source_decision_file)
        
        # Optional input
        api_record = None
        if args.approval_input_file and Path(args.approval_input_file).exists():
             api_record = load_json_record(args.approval_input_file)

        schema = load_backtest_approval_validation_schema()
        record = build_backtest_approval_validation(
            approval_input_record=api_record,
            strategy_candidate_record=cand_record,
            readiness_record=rdy_record,
            backtest_plan_record=btp_record,
            data_source_decision_record=dsd_record
        )
        
        validate_backtest_approval_validation(record, schema)
        result = write_backtest_approval_validation(record, VLD_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Validation ID: {record['approval_validation_id']}")
            print(f"Status: {record['validation_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Approval Validation Failed: {str(e)}")
        sys.exit(1)

def cmd_eligibility_report(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        rdy_record = load_json_record(args.readiness_file)
        btp_record = load_json_record(args.backtest_plan_file)
        dsd_record = load_json_record(args.data_source_decision_file)
        vld_record = load_json_record(args.approval_validation_file)

        schema = load_backtest_eligibility_report_schema()
        record = build_backtest_eligibility_report(
            strategy_candidate_record=cand_record,
            readiness_record=rdy_record,
            data_source_decision_record=dsd_record,
            backtest_plan_record=btp_record,
            approval_validation_record=vld_record
        )
        
        validate_backtest_eligibility_report(record, schema)
        result = write_backtest_eligibility_report(record, ELG_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Eligibility Report ID: {record['eligibility_report_id']}")
            print(f"Final Status: {record['eligibility_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Eligibility Report Failed: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Q21-Q23 Backtest Eligibility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True)
    p_schema.add_argument("--json", action="store_true")

    # readiness-recheck
    p_rdy = subparsers.add_parser("readiness-recheck")
    p_rdy.add_argument("--candidate-file", required=True)
    p_rdy.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_rdy.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_rdy.add_argument("--json", action="store_true")

    # plan-rebuild
    p_btp = subparsers.add_parser("plan-rebuild")
    p_btp.add_argument("--candidate-file", required=True)
    p_btp.add_argument("--readiness-file", required=True)
    p_btp.add_argument("--data-source-decision-file", required=True)
    p_btp.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_btp.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_btp.add_argument("--json", action="store_true")

    # approval-validate
    p_vld = subparsers.add_parser("approval-validate")
    p_vld.add_argument("--candidate-file", required=True)
    p_vld.add_argument("--readiness-file", required=True)
    p_vld.add_argument("--backtest-plan-file", required=True)
    p_vld.add_argument("--data-source-decision-file", required=True)
    p_vld.add_argument("--approval-input-file", required=False)
    p_vld.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_vld.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_vld.add_argument("--json", action="store_true")

    # eligibility-report
    p_elg = subparsers.add_parser("eligibility-report")
    p_elg.add_argument("--candidate-file", required=True)
    p_elg.add_argument("--readiness-file", required=True)
    p_elg.add_argument("--backtest-plan-file", required=True)
    p_elg.add_argument("--data-source-decision-file", required=True)
    p_elg.add_argument("--approval-validation-file", required=True)
    p_elg.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_elg.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_elg.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "readiness-recheck":
        cmd_readiness_recheck(args)
    elif args.command == "plan-rebuild":
        cmd_plan_rebuild(args)
    elif args.command == "approval-validate":
        cmd_approval_validate(args)
    elif args.command == "eligibility-report":
        cmd_eligibility_report(args)

if __name__ == "__main__":
    main()
