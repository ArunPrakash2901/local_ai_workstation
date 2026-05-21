import json
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from .paths import ensure_within_repo, REPO_ROOT, is_approved_quant_path
from .persistence import detect_persistence_capabilities
from .schema import validate_ohlcv_dataset

def detect_analytics_capabilities() -> Dict[str, bool]:
    """Detect available local analytics libraries."""
    libs = ['pandas', 'pyarrow', 'duckdb']
    return {lib: importlib.util.find_spec(lib) is not None for lib in libs}

def profile_ohlcv_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Profile a list of OHLCV dictionaries."""
    if not rows:
        return {"row_count": 0, "errors": ["Empty row list"]}

    profile = {
        "row_count": len(rows),
        "column_names": list(rows[0].keys()) if rows else [],
        "min_timestamp": None,
        "max_timestamp": None,
        "duplicate_timestamp_count": 0,
        "null_count_by_column": {},
        "numeric_ranges": {},
        "schema_validation": validate_ohlcv_dataset(rows),
        "warnings": [],
        "errors": []
    }

    timestamps = []
    numeric_cols = ["open", "high", "low", "close", "volume"]
    
    for col in profile["column_names"]:
        profile["null_count_by_column"][col] = 0
        if col in numeric_cols:
            profile["numeric_ranges"][col] = {"min": float('inf'), "max": float('-inf')}

    for row in rows:
        for col in profile["column_names"]:
            val = row.get(col)
            if val is None:
                profile["null_count_by_column"][col] += 1
            
            if col == "timestamp" and val:
                timestamps.append(val)
            
            if col in numeric_cols and isinstance(val, (int, float)):
                profile["numeric_ranges"][col]["min"] = min(profile["numeric_ranges"][col]["min"], val)
                profile["numeric_ranges"][col]["max"] = max(profile["numeric_ranges"][col]["max"], val)

    if timestamps:
        profile["min_timestamp"] = min(timestamps)
        profile["max_timestamp"] = max(timestamps)
        profile["duplicate_timestamp_count"] = len(timestamps) - len(set(timestamps))

    # Clean up infs
    for col in profile["numeric_ranges"]:
        if profile["numeric_ranges"][col]["min"] == float('inf'):
            profile["numeric_ranges"][col] = None

    return profile

def read_supported_dataset(path: Path) -> List[Dict[str, Any]]:
    """Read a dataset if format and path are approved."""
    ensure_within_repo(path)
    if not is_approved_quant_path(path):
        raise PermissionError(f"Path is not an approved Quant location: {path}")

    caps = detect_persistence_capabilities()

    if path.name.endswith(".json.fixture"):
        if path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("JSON fixture too large for safe in-memory read")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Fixtures from Wave 1C have {"metadata": ..., "rows": ...}
            return data.get("rows", [])
            
    elif path.suffix == ".parquet":
        if not (caps["pandas"] and (caps["pyarrow"] or caps["fastparquet"])):
            raise RuntimeError("Parquet backend missing")
        import pandas as pd
        df = pd.read_parquet(path)
        return df.to_dict(orient="records")
    
    raise ValueError(f"Unsupported or unreadable format: {path.suffix}")

def profile_dataset(path: Path) -> Dict[str, Any]:
    """Profile a dataset at the given path."""
    try:
        rows = read_supported_dataset(path)
        profile = profile_ohlcv_rows(rows)
        profile["path"] = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        return profile
    except Exception as e:
        return {
            "ok": False,
            "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "errors": [f"Profiling failed: {str(e)}"]
        }
