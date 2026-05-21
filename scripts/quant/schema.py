from typing import Any, Dict, List, Optional
from datetime import datetime

def validate_ohlcv_row(row: Dict[str, Any], required_cols: List[str]) -> List[str]:
    """Validate a single OHLCV row."""
    errors = []
    for col in required_cols:
        if col not in row:
            errors.append(f"Missing column: {col}")
            continue
        
        val = row[col]
        
        # Numeric checks for OHLCV
        if col in ["open", "high", "low", "close", "volume"]:
            if not isinstance(val, (int, float)):
                errors.append(f"Column {col} must be numeric, found {type(val).__name__}")
            elif val < 0:
                errors.append(f"Column {col} cannot be negative: {val}")

    if "high" in row and "low" in row:
        if row["high"] < row["low"]:
            errors.append(f"High ({row['high']}) is less than Low ({row['low']})")
    
    for col in ["open", "close"]:
        if col in row and "high" in row:
            if row[col] > row["high"]:
                errors.append(f"{col.capitalize()} ({row[col]}) is greater than High ({row['high']})")
        if col in row and "low" in row:
            if row[col] < row["low"]:
                errors.append(f"{col.capitalize()} ({row[col]}) is less than Low ({row['low']})")

    return errors

def validate_ohlcv_dataset(data: List[Dict[str, Any]], required_cols: Optional[List[str]] = None) -> Dict[str, Any]:
    """Validate an entire OHLCV dataset (list of dicts)."""
    if required_cols is None:
        required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
    
    result = {
        "ok": True,
        "errors": [],
        "warnings": [],
        "row_count": len(data)
    }

    if not data:
        result["ok"] = False
        result["errors"].append("Dataset is empty")
        return result

    timestamps = []
    for i, row in enumerate(data):
        row_errors = validate_ohlcv_row(row, required_cols)
        if row_errors:
            result["ok"] = False
            for err in row_errors:
                result["errors"].append(f"Row {i}: {err}")
        
        if "timestamp" in row:
            ts = row["timestamp"]
            timestamps.append(ts)

    # Check for duplicates and sorting
    if timestamps:
        if len(timestamps) != len(set(timestamps)):
            result["ok"] = False
            result["errors"].append("Duplicate timestamps detected")
        
        if timestamps != sorted(timestamps):
            result["warnings"].append("Timestamps are not sorted")

    return result
