import argparse
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.quant.candidate_completion import (
    load_candidate_detail_completion_schema,
    validate_candidate_detail_completion,
    build_candidate_detail_completion,
    apply_completion_to_candidate,
    write_candidate_detail_completion,
    write_completed_candidate,
    COMPLETION_DIR
)
from scripts.quant.data_source_decision import (
    load_data_source_decision_schema,
    validate_data_source_decision,
    build_data_source_decision,
    write_data_source_decision,
    REPORTS_DIR as DSD_DIR
)
from scripts.quant.single_backtest_approval_input import (
    load_single_backtest_approval_input_schema,
    validate_single_backtest_approval_input,
    build_single_backtest_approval_input,
    write_single_backtest_approval_input,
    REPORTS_DIR as API_DIR
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
        c_schema = load_candidate_detail_completion_schema()
        d_schema = load_data_source_decision_schema()
        a_schema = load_single_backtest_approval_input_schema()
        if args.json:
            print(json.dumps({
                "completion": c_schema.get("version"),
                "data_source": d_schema.get("version"),
                "approval_input": a_schema.get("version")
            }))
        else:
            print("[OK] Candidate Detail Completion Schema Loaded.")
            print("[OK] Data Source Decision Schema Loaded.")
            print("[OK] Single Backtest Approval Input Schema Loaded.")
    except Exception as e:
        print(f"[FAIL] Schema load failed: {str(e)}")
        sys.exit(1)

def cmd_complete_candidate(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        
        note_text = "UNKNOWN"
        if args.completion_note:
            with open(args.completion_note, 'r', encoding='utf-8') as f:
                note_text = f.read()

        c_schema = load_candidate_detail_completion_schema()
        record = build_candidate_detail_completion(
            candidate_record=cand_record,
            completion_note_text=note_text,
            cand_path=args.candidate_file
        )
        
        validate_candidate_detail_completion(record, c_schema)
        
        result_cmp = write_candidate_detail_completion(record, COMPLETION_DIR, dry_run=args.dry_run)
        
        # Apply completion (R2 branching)
        completed_cand = apply_completion_to_candidate(cand_record, record)
        result_cand = write_completed_candidate(completed_cand, dry_run=args.dry_run)

        if args.json:
            print(json.dumps({"completion": result_cmp, "candidate": result_cand}, indent=2))
        else:
            print(f"[{result_cmp['status'].upper()}] Completion ID: {record['completion_id']}")
            print(f"Path: {result_cmp['path']}")
            print(f"[{result_cand['status'].upper()}] Completed Candidate ID: {completed_cand['strategy_candidate_id']}")
            print(f"Path: {result_cand['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Candidate Completion Failed: {str(e)}")
        sys.exit(1)

def cmd_data_source_decision(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        dtr_record = load_json_record(args.data_requirement_file) if args.data_requirement_file else None
        
        note_text = "UNKNOWN"
        if args.decision_note:
            with open(args.decision_note, 'r', encoding='utf-8') as f:
                note_text = f.read()

        d_schema = load_data_source_decision_schema()
        record = build_data_source_decision(
            data_requirement_record=dtr_record,
            strategy_candidate_record=cand_record,
            decision_note_text=note_text
        )
        
        validate_data_source_decision(record, d_schema)
        result = write_data_source_decision(record, DSD_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Decision ID: {record['data_source_decision_id']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Data Source Decision Failed: {str(e)}")
        sys.exit(1)

def cmd_approval_input(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        
        note_text = "UNKNOWN"
        if args.approval_note:
            with open(args.approval_note, 'r', encoding='utf-8') as f:
                note_text = f.read()

        a_schema = load_single_backtest_approval_input_schema()
        record = build_single_backtest_approval_input(
            candidate_record=cand_record,
            note_text=note_text
        )
        
        validate_single_backtest_approval_input(record, a_schema)
        result = write_single_backtest_approval_input(record, API_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Approval Input ID: {record['approval_input_id']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Approval Input Failed: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Q18-Q20 Backtest Gate Inputs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True)
    p_schema.add_argument("--json", action="store_true")

    # complete-candidate
    p_comp = subparsers.add_parser("complete-candidate")
    p_comp.add_argument("--candidate-file", required=True)
    p_comp.add_argument("--completion-note", required=True)
    p_comp.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_comp.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_comp.add_argument("--json", action="store_true")

    # data-source-decision
    p_dsd = subparsers.add_parser("data-source-decision")
    p_dsd.add_argument("--candidate-file", required=True)
    p_dsd.add_argument("--data-requirement-file", required=True)
    p_dsd.add_argument("--decision-note", required=True)
    p_dsd.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_dsd.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_dsd.add_argument("--json", action="store_true")

    # approval-input
    p_api = subparsers.add_parser("approval-input")
    p_api.add_argument("--candidate-file", required=True)
    p_api.add_argument("--approval-note", required=True)
    p_api.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_api.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_api.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "complete-candidate":
        cmd_complete_candidate(args)
    elif args.command == "data-source-decision":
        cmd_data_source_decision(args)
    elif args.command == "approval-input":
        cmd_approval_input(args)

if __name__ == "__main__":
    main()
