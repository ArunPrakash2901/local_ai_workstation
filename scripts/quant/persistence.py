import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from .paths import ensure_within_repo, quant_path

def detect_persistence_capabilities() -> Dict[str, bool]:
    """Detect available local persistence libraries."""
    libs = ['pyarrow', 'fastparquet', 'duckdb', 'pandas']
    return {lib: importlib.util.find_spec(lib) is not None for lib in libs}

def write_json_fixture(rows: List[Dict[str, Any]], output_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Write synthetic fixture data to a JSON file."""
    if not metadata.get("synthetic_fixture", False):
        return {"ok": False, "error": "JSON fixture format is only permitted for synthetic data"}
    
    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Always use .json.fixture to distinguish from real data
    final_path = output_path.with_suffix(".json.fixture")
    
    data_to_write = {
        "metadata": metadata,
        "rows": rows
    }
    
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(data_to_write, f, indent=2)
    
    return {"ok": True, "written_to": str(final_path), "format": "json_fixture"}

def write_parquet_if_available(rows: List[Dict[str, Any]], output_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Write data to Parquet if a backend is available."""
    capabilities = detect_persistence_capabilities()
    
    if not (capabilities["pandas"] and (capabilities["pyarrow"] or capabilities["fastparquet"])):
        return {"ok": False, "error": "Parquet backend (pandas + pyarrow/fastparquet) unavailable"}

    try:
        import pandas as pd
        df = pd.DataFrame(rows)
        
        # Add metadata as pandas attributes (not persisted in standard parquet usually, 
        # but we include it in our result log)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure it has .parquet suffix
        final_path = output_path.with_suffix(".parquet")
        
        # Use pyarrow if available, else fastparquet
        engine = "pyarrow" if capabilities["pyarrow"] else "fastparquet"
        df.to_parquet(final_path, engine=engine, index=False)
        
        return {"ok": True, "written_to": str(final_path), "format": "parquet", "engine": engine}
    except Exception as e:
        return {"ok": False, "error": f"Parquet write failed: {str(e)}"}

def persist_ohlcv(
    rows: List[Dict[str, Any]], 
    output_path: Path, 
    format: str, 
    metadata: Dict[str, Any], 
    dry_run: bool = True
) -> Dict[str, Any]:
    """Orchestrate safe persistence of OHLCV data."""
    
    # 1. Path Safety Check
    try:
        ensure_within_repo(output_path)
    except PermissionError as e:
        return {"ok": False, "error": str(e)}

    # 2. Metadata validation
    required_meta = ["provider", "symbol", "interval"]
    for field in required_meta:
        if field not in metadata:
            return {"ok": False, "error": f"Missing required metadata field: {field}"}

    # 3. Dry Run Handling
    if dry_run:
        return {
            "ok": True, 
            "dry_run": True, 
            "intended_path": str(output_path), 
            "intended_format": format,
            "metadata": metadata,
            "rows_count": len(rows)
        }

    # 4. Format Dispatch
    if format == "json_fixture":
        return write_json_fixture(rows, output_path, metadata)
    elif format == "parquet":
        return write_parquet_if_available(rows, output_path, metadata)
    else:
        return {"ok": False, "error": f"Unsupported format: {format}"}
