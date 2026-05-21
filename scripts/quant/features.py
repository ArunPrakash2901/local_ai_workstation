import yaml
import json
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional
from .paths import quant_path
from .contracts import load_contract

def load_feature_contract() -> Dict[str, Any]:
    """Load the feature building contract."""
    return load_contract("feature_contracts.yaml")

def compute_returns_1d(df: pd.DataFrame) -> pd.Series:
    """Compute 1-day simple returns: (close[t] / close[t-1]) - 1."""
    return df['close'].pct_change(fill_method=None)

def compute_sma(df: pd.DataFrame, window: int) -> pd.Series:
    """Compute Simple Moving Average over close price."""
    return df['close'].rolling(window=window).mean()

def compute_volatility(df: pd.DataFrame, window: int) -> pd.Series:
    """Compute rolling standard deviation of 1-day returns."""
    # Ensure returns exist
    if 'returns_1d' not in df.columns:
        rets = compute_returns_1d(df)
    else:
        rets = df['returns_1d']
    return rets.rolling(window=window).std()

def validate_feature_request(features_requested: List[str], contract: Dict[str, Any]) -> List[str]:
    """Validate requested features against the contract."""
    errors = []
    supported_names = [f['name'] for f in contract['supported_features']]
    blocked_names = [f['name'] for f in contract['blocked_features']]
    
    for req in features_requested:
        # Handle parametrized features like sma_3, volatility_5
        base_name = req
        if '_' in req:
            parts = req.split('_')
            if parts[0] in ['sma', 'volatility'] and parts[-1].isdigit():
                base_name = f"{parts[0]}_n"
        
        if base_name in blocked_names:
            errors.append(f"Feature '{req}' is explicitly BLOCKED: {next(f['reason'] for f in contract['blocked_features'] if f['name'] == base_name)}")
        elif base_name not in supported_names:
            errors.append(f"Feature '{req}' is not supported in the current contract.")
            
    return errors

def build_features(rows: List[Dict[str, Any]], features_requested: List[str]) -> Dict[str, Any]:
    """Build requested features from OHLCV rows."""
    contract = load_feature_contract()
    errors = validate_feature_request(features_requested, contract)
    
    result = {
        "ok": False,
        "rows": [],
        "features_created": [],
        "warnings": [],
        "errors": errors,
        "metadata": {
            "created_by": "quant_feature_builder",
            "feature_contract_version": contract.get("version"),
            "lookahead_safe": True
        }
    }

    if errors:
        return result

    if not rows:
        result["errors"].append("Input row list is empty.")
        return result

    try:
        df = pd.DataFrame(rows)
        # Ensure 'close' is numeric
        df['close'] = pd.to_numeric(df['close'])
        
        created = []
        
        # Always compute returns first if volatility is requested
        if any(f.startswith('volatility_') for f in features_requested) or 'returns_1d' in features_requested:
            df['returns_1d'] = compute_returns_1d(df)
            if 'returns_1d' in features_requested:
                created.append('returns_1d')

        for feat in features_requested:
            if feat == 'returns_1d':
                continue # Already done
                
            if feat.startswith('sma_'):
                window = int(feat.split('_')[1])
                df[feat] = compute_sma(df, window)
                created.append(feat)
            elif feat.startswith('volatility_'):
                window = int(feat.split('_')[1])
                df[feat] = compute_volatility(df, window)
                created.append(feat)

        # Convert back to list of dicts, ensuring NaNs are handled (converted to None for JSON)
        # Use simple list comprehension with dict cleaning to be safe
        raw_rows = df.to_dict(orient="records")
        cleaned_rows = []
        for r in raw_rows:
            cleaned_row = {k: (v if pd.notnull(v) else None) for k, v in r.items()}
            cleaned_rows.append(cleaned_row)
            
        result["rows"] = cleaned_rows
        result["features_created"] = created
        result["ok"] = True
        
    except Exception as e:
        result["ok"] = False
        result["errors"].append(f"Feature building failed: {str(e)}")

    return result

def validate_no_lookahead(rows: List[Dict[str, Any]]) -> bool:
    """
    Heuristic check to ensure no lookahead bias.
    In this wave, we rely on the implementation using rolling() without centering.
    """
    # Placeholder for future more rigorous check
    return True
