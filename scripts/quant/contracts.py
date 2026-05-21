import yaml
from pathlib import Path
from typing import Any, Dict
from .paths import quant_path

def load_contract(relative_path: str) -> Dict[str, Any]:
    """Load a YAML contract from the contracts/quant directory."""
    full_path = quant_path("contracts", "quant", relative_path)
    if not full_path.exists():
        raise FileNotFoundError(f"Contract not found: {full_path}")
    
    with open(full_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if data is None:
        raise ValueError(f"Contract is empty: {full_path}")
        
    return data

def load_data_contracts() -> Dict[str, Any]:
    data = load_contract("data_contracts.yaml")
    if "sources" not in data:
        raise ValueError("data_contracts.yaml missing 'sources' field")
    return data

def load_risk_policy() -> Dict[str, Any]:
    data = load_contract("risk_policy.yaml")
    if "limits" not in data:
        raise ValueError("risk_policy.yaml missing 'limits' field")
    if "live_trading_allowed" in data.get("safety_settings", {}):
        if data["safety_settings"]["live_trading_allowed"] is not False:
            raise SecurityError("CRITICAL: live_trading_allowed must be False")
    return data

def load_execution_policy() -> Dict[str, Any]:
    data = load_contract("execution_policy.yaml")
    if "execution" not in data:
        raise ValueError("execution_policy.yaml missing 'execution' field")
    return data

class SecurityError(Exception):
    """Raised when a security-critical contract field is invalid."""
    pass
