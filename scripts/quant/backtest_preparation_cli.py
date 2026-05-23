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
from scripts.quant.backtest_data_requirements import (
    load_backtest_data_requirement_schema,
    validate_backtest_data_requirement,
    build_backtest_data_requirement,
    write_backtest_data_requirement,
    REPORTS_DIR as DTR_DIR
)
from scripts.quant.dataset_mapping_stub import (
    load_dataset_mapping_stub_schema,
    validate_dataset_mapping_stub,
    build_dataset_mapping_stub,
    write_dataset_mapping_stub,
    REPORTS_DIR as MAP_DIR
)
from scripts.quant.human_backtest_decision import (
    load_human_backtest_decision_packet_schema,
    validate_human_backtest_decision_packet,
    build_human_backtest_decision_packet,
    write_human_backtest_decision_packet,
    REPORTS_DIR as DEC_DIR
)

def print_safety_banner():
    print("\n[SAFETY BOUNDARY ENFORCED]")
    print("financial_advice_generated: false")
    print("trading_signal_generated: false")
    print("bot_logic_generated: false")
    print("live_trading_logic_generated: false")
    print("backtest_run: false")
    print("approval_granted: false")
    print("-" * 30)

def cmd_schema_check(args):
    print_safety_banner()
    try:
        dr_schema = load_backtest_data_requirement_schema()
        dm_schema = load_dataset_mapping_stub_schema()
        dp_schema = load_human_backtest_decision_packet_schema()
        if args.json:
            print(json.dumps({
                "data_req": dr_schema.get("version"),
                "data_map": dm_schema.get("version"),
                "decision": dp_schema.get("version")
            }))
        else:
            print("[OK] Backtest Data Requirement Schema Loaded.")
            print("[OK] Dataset Mapping Stub Schema Loaded.")
            print("[OK] Human Backtest Decision Packet Schema Loaded.")
    except Exception as e:
        print(f"[FAIL] Schema load failed: {str(e)}")
        sys.exit(1)

def load_json_record(filepath):
    if not filepath or not Path(filepath).exists():
        raise FileNotFoundError(f"Record not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def cmd_readiness_recheck(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        schema = load_pre_backtest_readiness_schema()
        
        record = evaluate_strategy_candidate_readiness(cand_record)
        validate_pre_backtest_readiness(record, schema)
        
        # Suffixing the readiness ID to denote a recheck instead of overwriting the original
        record['readiness_id'] = record['readiness_id'] + "-R1"
        
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

def cmd_data_requirements(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        rdy_record = load_json_record(args.readiness_file) if args.readiness_file else None
        
        schema = load_backtest_data_requirement_schema()
        
        record = build_backtest_data_requirement(
            candidate_record=cand_record,
            readiness_record=rdy_record
        )
        
        validate_backtest_data_requirement(record, schema)
        
        result = write_backtest_data_requirement(record, DTR_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Data Requirement ID: {record['data_requirement_id']}")
            print(f"Status: {record['requirement_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Data Requirements Failed: {str(e)}")
        sys.exit(1)

def cmd_dataset_mapping(args):
    print_safety_banner()
    try:
        dtr_record = load_json_record(args.data_requirement_file)
        
        schema = load_dataset_mapping_stub_schema()
        
        record = build_dataset_mapping_stub(dtr_record)
        
        validate_dataset_mapping_stub(record, schema)
        
        result = write_dataset_mapping_stub(record, MAP_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Dataset Mapping ID: {record['mapping_id']}")
            print(f"Status: {record['mapping_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Dataset Mapping Failed: {str(e)}")
        sys.exit(1)

def cmd_decision_packet(args):
    print_safety_banner()
    try:
        cand_record = load_json_record(args.candidate_file)
        rdy_record = load_json_record(args.readiness_file) if args.readiness_file else None
        dtr_record = load_json_record(args.data_requirement_file) if args.data_requirement_file else None
        map_record = load_json_record(args.dataset_mapping_file) if args.dataset_mapping_file else None
        
        schema = load_human_backtest_decision_packet_schema()
        
        record = build_human_backtest_decision_packet(
            candidate_record=cand_record,
            readiness_record=rdy_record,
            data_req_record=dtr_record,
            mapping_record=map_record
        )
        
        validate_human_backtest_decision_packet(record, schema)
        
        result = write_human_backtest_decision_packet(record, DEC_DIR, dry_run=args.dry_run)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[{result['status'].upper()}] Decision Packet ID: {record['decision_packet_id']}")
            print(f"Status: {record['decision_status']}")
            print(f"Path: {result['path']}")
            if args.dry_run:
                print("Run with --write to save.")

    except Exception as e:
        print(f"[FAIL] Decision Packet Failed: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Standalone CLI for Quant Q15-Q17 Backtest Preparation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema-check
    p_schema = subparsers.add_parser("schema-check")
    p_schema.add_argument("--dry-run", action="store_true", default=True)
    p_schema.add_argument("--json", action="store_true")

    # readiness-recheck
    p_rdy = subparsers.add_parser("readiness-recheck")
    p_rdy.add_argument("--candidate-file", required=True)
    p_rdy.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_rdy.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk (overrides default dry-run)")
    p_rdy.add_argument("--json", action="store_true")

    # data-requirements
    p_dtr = subparsers.add_parser("data-requirements")
    p_dtr.add_argument("--candidate-file", required=True)
    p_dtr.add_argument("--readiness-file", required=False)
    p_dtr.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_dtr.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_dtr.add_argument("--json", action="store_true")

    # dataset-mapping
    p_map = subparsers.add_parser("dataset-mapping")
    p_map.add_argument("--data-requirement-file", required=True)
    p_map.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_map.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_map.add_argument("--json", action="store_true")

    # decision-packet
    p_dec = subparsers.add_parser("decision-packet")
    p_dec.add_argument("--candidate-file", required=True)
    p_dec.add_argument("--readiness-file", required=True)
    p_dec.add_argument("--data-requirement-file", required=True)
    p_dec.add_argument("--dataset-mapping-file", required=True)
    p_dec.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    p_dec.add_argument("--write", action="store_false", dest="dry_run", help="Write to disk")
    p_dec.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "schema-check":
        cmd_schema_check(args)
    elif args.command == "readiness-recheck":
        cmd_readiness_recheck(args)
    elif args.command == "data-requirements":
        cmd_data_requirements(args)
    elif args.command == "dataset-mapping":
        cmd_dataset_mapping(args)
    elif args.command == "decision-packet":
        cmd_decision_packet(args)

if __name__ == "__main__":
    main()
