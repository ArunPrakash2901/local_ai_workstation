import argparse
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.quant.strategy_candidate import (
    load_strategy_candidate_schema,
    validate_strategy_candidate,
    build_strategy_candidate_from_inputs,
    write_strategy_candidate,
    REPORTS_DIR as CAN_DIR
)
from scripts.quant.pre_backtest_readiness import (
    load_pre_backtest_readiness_schema,
    validate_pre_backtest_readiness,
    evaluate_strategy_candidate_readiness,
    write_pre_backtest_readiness,
    REPORTS_DIR as RDY_DIR
)
from scripts.quant.backtest_handoff import (
    load_backtest_handoff_schema,
    validate_backtest_handoff,
    build_backtest_handoff_from_readiness,
    write_backtest_handoff,
    REPORTS_DIR as HOF_DIR
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
        c_schema = load_strategy_candidate_schema()
        r_schema = load_pre_backtest_readiness_schema()
        h_schema = load_backtest_handoff_schema()
        if args.json:
            print(json.dumps({
                "candidate": c_schema.get("version"),
                "readiness": r_schema.get("version"),
                "handoff": h_schema.get("version")
            }))
        else:
            print("[OK] Strategy Candidate Schema Loaded.")
            print("[OK] Pre-Backtest Readiness Schema Loaded.")
            print("[OK] Backtest Handoff Schema Loaded.")
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
    if not file_path_exists(filepath):
        raise FileNotFoundError(f"Record not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def file_path_exists(filepath):
    if not filepath:
        return False
    return Path(filepath).exists()

def cmd_candidate_draft(args):
    print_safety_banner()
    try:
        note_text = "UNKNOWN"
        title = "UNKNOWN"
        if args.note_file:
            v_path = validate_note_file_path(args.note_file)
            with open(v_path, 'r', encoding='utf-8') as f:
                note_text = f.read()
            title = v_path.stem
            
        idea_record = load_json_record(args.idea_file) if args.idea_file else None
        paper_record = load_json_record(args.paper_file) if args.paper_file else None
        
        # Determine title fallback
        if title == "UNKNOWN":
            if idea_record: title = idea_record.get('title', 'UNKNOWN')
            elif paper_record: title = paper_record.get('title', 'UNKNOWN')

        schema = load_strategy_candidate_schema()
        record = build_strategy_candidate_from_inputs(
            idea_record=idea_record,
            paper_record=paper_record,
            note_text=note_text,
            title=title
        )
        
        validate_strategy_candidate(record, schema)
        result = write_strategy_candidate(record, CAN_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Candidate ID: {record['strategy_candidate_id']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")
                
    except Exception as e:
        print(f"[FAIL] Candidate Draft Failed: {str(e)}")
        sys.exit(1)

def cmd_readiness_check(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        schema = load_pre_backtest_readiness_schema()
        
        record = evaluate_strategy_candidate_readiness(cand_record)
        validate_pre_backtest_readiness(record, schema)
        
        result = write_pre_backtest_readiness(record, RDY_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Readiness ID: {record['readiness_id']}")
            print(f"Status: {record['readiness_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Readiness Check Failed: {str(e)}")
        sys.exit(1)

def cmd_backtest_handoff_draft(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        rdy_record = load_json_record(args.readiness_file)
        
        schema = load_backtest_handoff_schema()
        
        record = build_backtest_handoff_from_readiness(cand_record, rdy_record)
        validate_backtest_handoff(record, schema)
        
        result = write_backtest_handoff(record, HOF_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Handoff ID: {record['handoff_id']}")
            print(f"Status: {record['handoff_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Backtest Handoff Draft Failed: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Q6-Q8 Readiness Gates")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True)
    p_schema.add_argument("--json", action="store_true")

    # candidate-draft
    p_cand = subparsers.add_parser("candidate-draft")
    p_cand.add_argument("--note-file", required=False)
    p_cand.add_argument("--idea-file", required=False)
    p_cand.add_argument("--paper-file", required=False)
    p_cand.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_cand.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_cand.add_argument("--json", action="store_true")

    # readiness-check
    p_rdy = subparsers.add_parser("readiness-check")
    p_rdy.add_argument("--candidate-file", required=True)
    p_rdy.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_rdy.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_rdy.add_argument("--json", action="store_true")

    # backtest-handoff-draft
    p_hof = subparsers.add_parser("backtest-handoff-draft")
    p_hof.add_argument("--candidate-file", required=True)
    p_hof.add_argument("--readiness-file", required=True)
    p_hof.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_hof.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_hof.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "candidate-draft":
        cmd_candidate_draft(args)
    elif args.command == "readiness-check":
        cmd_readiness_check(args)
    elif args.command == "backtest-handoff-draft":
        cmd_backtest_handoff_draft(args)

if __name__ == "__main__":
    main()
