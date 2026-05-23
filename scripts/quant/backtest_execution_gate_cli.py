import argparse
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.quant.candidate_concrete_spec import (
    load_candidate_concrete_spec_schema,
    validate_candidate_concrete_spec,
    build_candidate_concrete_spec,
    apply_concrete_spec_to_candidate,
    write_candidate_concrete_spec,
    write_concretized_candidate
)
from scripts.quant.manual_dataset_import import (
    load_manual_dataset_import_schema,
    validate_manual_dataset_import,
    build_manual_dataset_import,
    write_manual_dataset_import
)
from scripts.quant.backtest_execution_preflight import (
    load_backtest_execution_preflight_schema,
    validate_backtest_execution_preflight,
    build_backtest_execution_preflight,
    write_backtest_execution_preflight
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
    print("execution_allowed: false")
    print("-" * 30)

def load_json_record(filepath):
    if not filepath or not Path(filepath).exists():
        raise FileNotFoundError(f"Record not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def cmd_schema_check(args):
    print_safety_banner()
    try:
        cs_schema = load_candidate_concrete_spec_schema()
        di_schema = load_manual_dataset_import_schema()
        pf_schema = load_backtest_execution_preflight_schema()
        if args.json:
            print(json.dumps({
                "concrete_spec": cs_schema.get("version"),
                "dataset_import": di_schema.get("version"),
                "preflight": pf_schema.get("version")
            }))
        else:
            print("[OK] Candidate Concrete Spec Schema Loaded.")
            print("[OK] Manual Dataset Import Schema Loaded.")
            print("[OK] Backtest Execution Preflight Schema Loaded.")
    except Exception as e:
        print(f"[FAIL] Schema load failed: {str(e)}")
        sys.exit(1)

def cmd_concrete_spec(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        
        note_text = "UNKNOWN"
        if args.spec_note:
            with open(args.spec_note, 'r', encoding='utf-8') as f:
                note_text = f.read()

        cs_schema = load_candidate_concrete_spec_schema()
        record = build_candidate_concrete_spec(
            candidate_record=cand_record,
            note_text=note_text,
            cand_path=args.candidate_file
        )
        
        validate_candidate_concrete_spec(record, cs_schema)
        
        result_spec = write_candidate_concrete_spec(record, dry_run=args.dry_run)
        
        # Apply spec (R3 branching)
        concretized_cand = apply_concrete_spec_to_candidate(cand_record, record)
        result_cand = write_concretized_candidate(concretized_cand, dry_run=args.dry_run)

        if args.json:
            print(json.dumps({"spec": result_spec, "candidate": result_cand}, indent=2))
        else:
            print(f"[{result_spec['status'].upper()}] Concrete Spec ID: {record['concrete_spec_id']}")
            print(f"Path: {result_spec['path']}")
            print(f"[{result_cand['status'].upper()}] Concretized Candidate ID: {concretized_cand['strategy_candidate_id']}")
            print(f"Path: {result_cand['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Concrete Spec Failed: {str(e)}")
        sys.exit(1)

def cmd_dataset_import(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        dsd_record = load_json_record(args.data_source_decision_file) if args.data_source_decision_file else None
        
        note_text = "UNKNOWN"
        if args.import_note:
            with open(args.import_note, 'r', encoding='utf-8') as f:
                note_text = f.read()

        di_schema = load_manual_dataset_import_schema()
        record = build_manual_dataset_import(
            strategy_candidate_record=cand_record,
            data_source_decision_record=dsd_record,
            import_note_text=note_text
        )
        
        validate_manual_dataset_import(record, di_schema)
        result = write_manual_dataset_import(record, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Import ID: {record['import_id']}")
            print(f"Status: {record['import_status']}")
            print(f"File: {record['source_file_path']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Dataset Import Failed: {str(e)}")
        sys.exit(1)

def cmd_preflight(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        di_record = load_json_record(args.dataset_import_file) if args.dataset_import_file else None
        
        # We search for other gates if not provided
        # For simplicity in this CLI, we only take what's passed.
        
        pf_schema = load_backtest_execution_preflight_schema()
        record = build_backtest_execution_preflight(
            strategy_candidate_record=cand_record,
            manual_dataset_import_record=di_record
        )
        
        validate_backtest_execution_preflight(record, pf_schema)
        result = write_backtest_execution_preflight(record, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Preflight ID: {record['preflight_id']}")
            print(f"Status: {record['preflight_status']}")
            print(f"Execution Allowed: {record['execution_allowed']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Preflight Failed: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Q24-Q26 Backtest Execution Gate")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True)
    p_schema.add_argument("--json", action="store_true")

    # concrete-spec
    p_spec = subparsers.add_parser("concrete-spec")
    p_spec.add_argument("--candidate-file", required=True)
    p_spec.add_argument("--spec-note", required=True)
    p_spec.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_spec.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_spec.add_argument("--json", action="store_true")

    # dataset-import
    p_imp = subparsers.add_parser("dataset-import")
    p_imp.add_argument("--candidate-file", required=True)
    p_imp.add_argument("--data-source-decision-file", required=False)
    p_imp.add_argument("--import-note", required=True)
    p_imp.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_imp.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_imp.add_argument("--json", action="store_true")

    # preflight
    p_pre = subparsers.add_parser("preflight")
    p_pre.add_argument("--candidate-file", required=True)
    p_pre.add_argument("--dataset-import-file", required=False)
    p_pre.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_pre.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_pre.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "concrete-spec":
        cmd_concrete_spec(args)
    elif args.command == "dataset-import":
        cmd_dataset_import(args)
    elif args.command == "preflight":
        cmd_preflight(args)

if __name__ == "__main__":
    main()
