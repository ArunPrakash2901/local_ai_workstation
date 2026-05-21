import os
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
from .paths import REPO_ROOT, is_approved_quant_path, ensure_within_repo, quant_path
from .persistence import detect_persistence_capabilities

APPROVED_DATA_ROOTS = [
    "data/quant/raw",
    "data/quant/clean",
    "data/quant/features",
]

SUPPORTED_SUFFIXES = [".json.fixture", ".parquet"]

def scan_catalog() -> List[Dict[str, Any]]:
    """Scan approved Quant data roots and return a catalog of datasets."""
    catalog = []
    persistence_caps = detect_persistence_capabilities()
    
    for root_rel in APPROVED_DATA_ROOTS:
        root_path = REPO_ROOT / root_rel
        if not root_path.exists():
            continue
            
        # Recursive scan
        for p in root_path.rglob("*"):
            if p.is_dir():
                continue
                
            # Path safety check
            try:
                ensure_within_repo(p)
                abs_allowed = is_approved_quant_path(p)
            except (PermissionError, ValueError):
                continue
                
            if not abs_allowed:
                continue

            # Basic metadata
            stat = p.stat()
            rel_path = p.relative_to(REPO_ROOT)
            suffix = "".join(p.suffixes) # Handles .json.fixture
            
            # Identify format
            fmt = "unknown"
            if p.name.endswith(".json.fixture"):
                fmt = "json_fixture"
            elif p.suffix == ".parquet":
                fmt = "parquet"
            
            # Synthetic check
            is_synthetic = "unknown"
            if fmt == "json_fixture" or "fixture" in str(rel_path).lower():
                is_synthetic = True
            elif "raw" in str(rel_path).lower():
                # In MVP raw data from adapters is future_real_market_data
                # but currently only fixture exists
                is_synthetic = False if "fixture" not in str(rel_path) else True
            
            # Read capability check
            read_supported = False
            reason = ""
            
            if fmt == "json_fixture":
                if stat.st_size < 10 * 1024 * 1024: # 10MB limit for JSON profile
                    read_supported = True
                else:
                    reason = "JSON file too large for profiling"
            elif fmt == "parquet":
                if persistence_caps["pandas"] and (persistence_caps["pyarrow"] or persistence_caps["fastparquet"]):
                    read_supported = True
                else:
                    reason = "Parquet backend missing"
            else:
                reason = f"Unsupported suffix: {suffix}"

            catalog.append({
                "dataset_id": p.stem if fmt != "json_fixture" else p.name.replace(".json.fixture", ""),
                "relative_path": str(rel_path).replace("\\", "/"),
                "absolute_path_allowed": abs_allowed,
                "format": fmt,
                "size_bytes": stat.st_size,
                "modified_timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "synthetic_fixture": is_synthetic,
                "read_supported": read_supported,
                "reason_if_unsupported": reason
            })
            
    return catalog
