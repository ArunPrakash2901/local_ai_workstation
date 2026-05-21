import argparse
import json
import sys
from datetime import datetime
from .contracts import load_data_contracts, load_risk_policy, load_execution_policy
from .schema import validate_ohlcv_dataset
from .freshness import check_freshness
from .paths import REPO_ROOT, APPROVED_QUANT_ROOTS

from .ingest import ingest_ohlcv
from .fixture_adapter import FixtureAdapter

from .persistence import detect_persistence_capabilities, persist_ohlcv
from .catalog import scan_catalog
from .analytics import detect_analytics_capabilities, profile_dataset, read_supported_dataset
from .features import load_feature_contract, build_features

def cmd_feature_contract_check(args):
    """Check the validity of the feature contract."""
    print("Checking Feature Contract...")
    try:
        contract = load_feature_contract()
        print(f"[OK] feature_contracts.yaml (Version: {contract['version']})")
        print(f"Supported Features: {[f['name'] for f in contract['supported_features']]}")
        return 0
    except Exception as e:
        print(f"[FAIL] Feature contract check failed: {e}")
        return 1

def cmd_feature_build(args):
    """Build features from an input dataset."""
    print(f"Building Features for: {args.input}")
    try:
        input_path = REPO_ROOT / args.input
        rows = read_supported_dataset(input_path)
        
        features_list = [f.strip() for f in args.features.split(',')]
        result = build_features(rows, features_list)
        
        if not result["ok"]:
            print(json.dumps(result, indent=2))
            return 1
            
        # Determine output path under data/quant/features/
        # Use stem of input filename + feature suffix
        input_name = input_path.stem if not input_path.name.endswith(".json.fixture") else input_path.name.replace(".json.fixture", "")
        output_path = quant_path("data", "quant", "features", f"{input_name}_features")
        
        # Persistence
        persist_res = persist_ohlcv(
            rows=result["rows"],
            output_path=output_path,
            format=args.format,
            metadata={
                "provider": "feature_builder",
                "symbol": result["rows"][0].get("symbol", "UNKNOWN") if result["rows"] else "UNKNOWN",
                "interval": "1d", # Inferred or should be from input
                "created_by": "quant_feature_builder",
                "features": result["features_created"],
                "synthetic_fixture": any("fixture" in str(input_path).lower() for p in [input_path])
            },
            dry_run=not args.write_features
        )
        
        result["persistence"] = persist_res
        # Add safety flags
        result["external_api_called"] = False
        result["orders_generated"] = False
        result["trading_signal_generated"] = False
        result["live_trading_touched"] = False
        
        # Don't print all rows if it's a long list
        output_result = result.copy()
        if not args.show_rows:
            output_result["rows"] = f"[{len(result['rows'])} rows omitted]"
            
        print(json.dumps(output_result, indent=2))
        return 0 if persist_res["ok"] else 1
        
    except Exception as e:
        print(f"[FAIL] Feature building failed: {e}")
        return 1

def cmd_dataset_catalog(args):
    """Scan and print the dataset catalog."""
    print("Scanning Dataset Catalog...")
    catalog = scan_catalog()
    
    result = {
        "catalog": catalog,
        "count": len(catalog),
        "external_api_called": False
    }
    
    print(json.dumps(result, indent=2))
    return 0

def cmd_analytics_capabilities(args):
    """Detect and print local analytics capabilities."""
    print("Detecting Analytics Capabilities...")
    capabilities = detect_analytics_capabilities()
    
    result = {
        "capabilities": capabilities,
        "duckdb_available": capabilities["duckdb"],
        "external_api_called": False
    }
    
    print(json.dumps(result, indent=2))
    return 0

def cmd_dataset_profile(args):
    """Profile a dataset at the given relative path."""
    print(f"Profiling Dataset: {args.path}")
    # Convert relative to absolute
    try:
        path = REPO_ROOT / args.path
        profile = profile_dataset(path)
        
        # Add safety flags
        profile["external_api_called"] = False
        profile["live_trading_allowed"] = False
        
        print(json.dumps(profile, indent=2))
        return 0 if "errors" not in profile or not profile["errors"] else 1
    except Exception as e:
        print(f"[FAIL] Profiling request failed: {e}")
        return 1

def cmd_persistence_capabilities(args):
    """Detect and print local persistence capabilities."""
    print("Detecting Persistence Capabilities...")
    capabilities = detect_persistence_capabilities()
    
    result = {
        "capabilities": capabilities,
        "parquet_supported": capabilities["pandas"] and (capabilities["pyarrow"] or capabilities["fastparquet"]),
        "external_api_called": False
    }
    
    print(json.dumps(result, indent=2))
    return 0

def cmd_data_ingest_fixture(args):
    """Fetch and validate data from the fixture adapter."""
    print(f"Ingesting Fixture Data for: {args.symbol}")
    try:
        start = datetime.fromisoformat(args.start)
        end = datetime.fromisoformat(args.end)
        adapter = FixtureAdapter()
        
        result = ingest_ohlcv(
            provider=adapter,
            symbol=args.symbol,
            start_date=start,
            end_date=end,
            interval=args.interval,
            dry_run=args.dry_run,
            write_fixture=args.write_fixture,
            format=args.format
        )
        
        # Add safety flag to output
        result["external_api_called"] = False
        
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    except ValueError as e:
        print(f"[FAIL] Invalid date format: {e}")
        return 1

def cmd_contract_check(args):
    """Check the validity of YAML contracts."""
    print("Checking Quant Contracts...")
    try:
        data = load_data_contracts()
        print(f"[OK] data_contracts.yaml (Sources: {len(data['sources'])})")
        
        risk = load_risk_policy()
        print("[OK] risk_policy.yaml")
        
        exec_p = load_execution_policy()
        print("[OK] execution_policy.yaml")
        
        return 0
    except Exception as e:
        print(f"[FAIL] Contract check failed: {e}")
        return 1

def cmd_schema_check(args):
    """Validate a sample OHLCV dataset."""
    print("Validating Sample OHLCV Schema...")
    # Sample data for dry-run validation
    sample_data = [
        {"timestamp": "2026-05-20T09:30:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 102.0, "volume": 1000},
        {"timestamp": "2026-05-20T09:31:00", "open": 102.0, "high": 103.0, "low": 101.0, "close": 101.5, "volume": 800}
    ]
    
    if args.invalid:
        sample_data[1]["high"] = 90.0 # High < Low
    
    result = validate_ohlcv_dataset(sample_data)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1

def cmd_freshness_check(args):
    """Check freshness of a provided timestamp."""
    print(f"Checking Freshness for: {args.latest}")
    try:
        latest = datetime.fromisoformat(args.latest)
        policy = args.policy or "max_lag_24h"
        result = check_freshness(latest, policy)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    except ValueError:
        print(f"[FAIL] Invalid timestamp format: {args.latest}")
        return 1

def cmd_paths_check(args):
    """Verify Quant path configuration."""
    print(f"Repo Root: {REPO_ROOT}")
    print("Approved Quant Roots:")
    for root in APPROVED_QUANT_ROOTS:
        print(f" - {root}")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Quant Workstation Wave 1 Foundation CLI")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Always true for Wave 1")
    
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")
    
    # data-contract-check
    subparsers.add_parser("data-contract-check", help="Check validity of YAML contracts")
    
    # data-schema-check
    schema_parser = subparsers.add_parser("data-schema-check", help="Validate sample OHLCV schema")
    schema_parser.add_argument("--invalid", action="store_true", help="Generate invalid sample to test failure")
    
    # data-freshness-check
    freshness_parser = subparsers.add_parser("data-freshness-check", help="Check freshness policy")
    freshness_parser.add_argument("--latest", required=True, help="ISO timestamp of latest data")
    freshness_parser.add_argument("--policy", help="Policy string (e.g. max_lag_24h)")
    
    # paths-check
    subparsers.add_parser("paths-check", help="Verify Quant path configuration")

    # persistence-capabilities
    subparsers.add_parser("persistence-capabilities", help="Detect local persistence capabilities")

    # analytics-capabilities
    subparsers.add_parser("analytics-capabilities", help="Detect local analytics capabilities")

    # feature-contract-check
    subparsers.add_parser("feature-contract-check", help="Check validity of feature contract")

    # dataset-catalog
    subparsers.add_parser("dataset-catalog", help="Scan Quant dataset catalog")

    # dataset-profile
    profile_parser = subparsers.add_parser("dataset-profile", help="Profile a Quant dataset")
    profile_parser.add_argument("--path", required=True, help="Repo-relative path to dataset")

    # feature-build
    build_parser = subparsers.add_parser("feature-build", help="Build features from dataset")
    build_parser.add_argument("--input", required=True, help="Repo-relative path to input dataset")
    build_parser.add_argument("--features", required=True, help="Comma-separated list of features (e.g. returns_1d,sma_3)")
    build_parser.add_argument("--format", default="json_fixture", choices=["json_fixture", "parquet"], help="Output format")
    build_parser.add_argument("--write-features", action="store_true", help="Write features to data/quant/features/")
    build_parser.add_argument("--show-rows", action="store_true", help="Show all rows in output (default: false)")

    # data-ingest-fixture
    ingest_parser = subparsers.add_parser("data-ingest-fixture", help="Fetch and validate fixture OHLCV")
    ingest_parser.add_argument("--symbol", required=True, help="Symbol to fetch (e.g. SPY)")
    ingest_parser.add_argument("--start", required=True, help="ISO start date (YYYY-MM-DD)")
    ingest_parser.add_argument("--end", required=True, help="ISO end date (YYYY-MM-DD)")
    ingest_parser.add_argument("--interval", default="1d", help="Data interval (default: 1d)")
    ingest_parser.add_argument("--format", default="json_fixture", choices=["json_fixture", "parquet"], help="Persistence format")
    ingest_parser.add_argument("--write-fixture", action="store_true", help="Write tiny JSON fixture to data/quant/raw/")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    commands = {
        "data-contract-check": cmd_contract_check,
        "data-schema-check": cmd_schema_check,
        "data-freshness-check": cmd_freshness_check,
        "paths-check": cmd_paths_check,
        "persistence-capabilities": cmd_persistence_capabilities,
        "analytics-capabilities": cmd_analytics_capabilities,
        "feature-contract-check": cmd_feature_contract_check,
        "dataset-catalog": cmd_dataset_catalog,
        "dataset-profile": cmd_dataset_profile,
        "feature-build": cmd_feature_build,
        "data-ingest-fixture": cmd_data_ingest_fixture
    }
    
    if args.command in commands:
        sys.exit(commands[args.command](args))
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
