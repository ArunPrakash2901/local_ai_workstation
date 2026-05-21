import json
from datetime import datetime
from typing import Optional, Dict, Any
from .adapters import OHLCVProvider
from .schema import validate_ohlcv_dataset
from .storage import get_raw_dataset_path
from .freshness import check_freshness

from .persistence import persist_ohlcv

def ingest_ohlcv(
    provider: OHLCVProvider,
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    interval: str = "1d",
    dry_run: bool = True,
    write_fixture: bool = False,
    format: str = "json_fixture"
) -> Dict[str, Any]:
    """Orchestrate the ingestion of OHLCV data from a provider."""
    
    result = {
        "ok": False,
        "provider": provider.provider_name,
        "symbol": symbol,
        "dry_run": dry_run,
        "synthetic_fixture": provider.provider_name == "fixture",
        "rows_fetched": 0,
        "validation": None,
        "storage_path": None,
        "persistence": None,
        "errors": []
    }

    try:
        # 1. Fetch data from adapter
        data = provider.fetch_ohlcv(symbol, start_date, end_date, interval)
        result["rows_fetched"] = len(data)

        if not data:
            result["errors"].append(f"No data returned for {symbol}")
            return result

        # 2. Validate using schema.py
        validation = validate_ohlcv_dataset(data)
        result["validation"] = validation
        
        if not validation["ok"]:
            result["errors"].append("Schema validation failed")
            return result

        # 3. Check intended storage path
        storage_path = get_raw_dataset_path(provider.provider_name, symbol)
        result["storage_path"] = str(storage_path)

        # 4. Handle persistence using the new abstraction
        metadata = {
            "provider": provider.provider_name,
            "synthetic_fixture": provider.provider_name == "fixture",
            "symbol": symbol,
            "interval": interval,
            "created_by": "ingest_ohlcv",
            "source_mode": "research",
            "schema_validation_ok": validation["ok"]
        }

        # Override format if not json_fixture and not provided
        # But we default to json_fixture for safety
        
        persist_res = persist_ohlcv(
            rows=data,
            output_path=storage_path,
            format=format,
            metadata=metadata,
            dry_run=dry_run or (not write_fixture and provider.provider_name == "fixture")
        )
        
        result["persistence"] = persist_res
        result["ok"] = persist_res["ok"]
        
        if not persist_res["ok"]:
            result["errors"].append(persist_res.get("error", "Persistence failed"))

    except Exception as e:
        result["errors"].append(f"Ingestion failed: {str(e)}")

    return result
