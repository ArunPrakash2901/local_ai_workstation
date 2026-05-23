import argparse
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.quant.readiness_remediation import (
    load_readiness_gap_report_schema,
    validate_readiness_gap_report,
    build_gap_report,
    write_gap_report,
    REPORTS_DIR as GAP_DIR
)
from scripts.quant.strategy_revision import (
    load_strategy_candidate_revision_schema,
    validate_strategy_candidate_revision,
    apply_candidate_revision,
    write_strategy_candidate_revision,
    write_revised_strategy_candidate
)
from scripts.quant.human_approval import (
    load_human_backtest_approval_schema,
    validate_human_backtest_approval,
    build_pending_human_backtest_approval,
    write_human_backtest_approval,
    REPORTS_DIR as APP_DIR
)

def print_safety_banner():
    print("\n[SAFETY BOUNDARY ENFORCED]")
    print("financial_advice_generated: false")
    print("trading_signal_generated: false")
    print("bot_logic_generated: false")
    print("live_trading_logic_generated: false")
    print("backtest_run: false")
    print("-" * 30)

def cmd_schema_check(args):
    print_safety_banner()
    try:
        g_schema = load_readiness_gap_report_schema()
        r_schema = load_strategy_candidate_revision_schema()
        a_schema = load_human_backtest_approval_schema()
        if args.json:
            print(json.dumps({
                "gap": g_schema.get("version"),
                "revision": r_schema.get("version"),
                "approval": a_schema.get("version")
            }))
        else:
            print("[OK] Readiness Gap Report Schema Loaded.")
            print("[OK] Strategy Candidate Revision Schema Loaded.")
            print("[OK] Human Backtest Approval Schema Loaded.")
    except Exception as e:
        print(f"[FAIL] Schema load failed: {str(e)}")
        sys.exit(1)

def validate_note_file_path(file_path_str):
    path = Path(file_path_str).resolve()
    base_dir = Path(__file__).resolve().parent.parent.parent
    scratch_dir = (base_dir / "scratch" / "quant_strategy_candidates").resolve()

    if scratch_dir not in path.parents:
        raise ValueError(f"Note file must be within scratch/quant_strategy_candidates/. Got: {file_path_str}")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Note file not found: {file_path_str}")

    if path.stat().st_size > 100 * 1024:
        raise ValueError(f"Note file exceeds maximum allowed size of 100KB: {file_path_str}")

    return path

def load_json_record(filepath):
    if not filepath or not Path(filepath).exists():
        raise FileNotFoundError(f"Record not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def cmd_gap_report(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        rdy_record = load_json_record(args.readiness_file)
        
        schema = load_readiness_gap_report_schema()
        record = build_gap_report(
            candidate_record=cand_record,
            readiness_record=rdy_record,
            cand_path=args.candidate_file,
            rdy_path=args.readiness_file
        )
        
        validate_readiness_gap_report(record, schema)
        result = write_gap_report(record, GAP_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Gap Report ID: {record['gap_report_id']}")
            print(f"Missing Fields: {len(record['missing_fields'])}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")
                
    except Exception as e:
        print(f"[FAIL] Gap Report Failed: {str(e)}")
        sys.exit(1)

def cmd_revise_candidate(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        gap_record = load_json_record(args.gap_report_file)
        
        v_path = validate_note_file_path(args.revision_note)
        with open(v_path, 'r', encoding='utf-8') as f:
            note_text = f.read()

        schema = load_strategy_candidate_revision_schema()
        
        record = apply_candidate_revision(
            candidate_record=cand_record,
            gap_report_record=gap_record,
            revision_note_text=note_text,
            cand_path=args.candidate_file
        )
        
        validate_strategy_candidate_revision(record, schema)
        
        result_rev = write_strategy_candidate_revision(record, dry_run=args.dry_run)
        result_can = write_revised_strategy_candidate(record['candidate_record_after_revision'], dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps({"revision": result_rev, "candidate": result_can}, indent=2))
        else:
            print(f"[{result_rev['status'].upper()}] Revision ID: {record['revision_id']}")
            print(f"Path: {result_rev['path']}")
            print(f"[{result_can['status'].upper()}] Revised Candidate ID: {record['candidate_record_after_revision']['strategy_candidate_id']}")
            print(f"Path: {result_can['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Candidate Revision Failed: {str(e)}")
        sys.exit(1)

def cmd_human_approval_stub(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        rdy_record = load_json_record(args.readiness_file)
        
        schema = load_human_backtest_approval_schema()
        record = build_pending_human_backtest_approval(
            candidate_record=cand_record,
            readiness_record=rdy_record
        )
        
        validate_human_backtest_approval(record, schema)
        result = write_human_backtest_approval(record, APP_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Approval Stub ID: {record['approval_id']}")
            print(f"Status: {record['approval_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")
                
    except Exception as e:
        print(f"[FAIL] Human Approval Stub Failed: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Q12-Q14 Readiness Remediation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True)
    p_schema.add_argument("--json", action="store_true")

    # gap-report
    p_gap = subparsers.add_parser("gap-report")
    p_gap.add_argument("--candidate-file", required=True)
    p_gap.add_argument("--readiness-file", required=True)
    p_gap.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_gap.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_gap.add_argument("--json", action="store_true")

    # revise-candidate
    p_rev = subparsers.add_parser("revise-candidate")
    p_rev.add_argument("--candidate-file", required=True)
    p_rev.add_argument("--gap-report-file", required=True)
    p_rev.add_argument("--revision-note", required=True)
    p_rev.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_rev.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_rev.add_argument("--json", action="store_true")
    
    # human-approval-stub
    p_app = subparsers.add_parser("human-approval-stub")
    p_app.add_argument("--candidate-file", required=True)
    p_app.add_argument("--readiness-file", required=True)
    p_app.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_app.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_app.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "gap-report":
        cmd_gap_report(args)
    elif args.command == "revise-candidate":
        cmd_revise_candidate(args)
    elif args.command == "human-approval-stub":
        cmd_human_approval_stub(args)

if __name__ == "__main__":
    main()
