import os
from pathlib import Path

def detect_repo_root() -> Path:
    """Robustly detect the workstation repository root."""
    # Assuming this script is in scripts/quant/paths.py
    # parents[1] is scripts/, parents[2] is root/
    root = Path(__file__).resolve().parents[2]
    # Safety check: ensure we are actually at D:\_ai_brain or equivalent
    if not (root / "scripts" / "ws").exists():
        # Fallback to hardcoded safe root if structure is unexpected
        return Path("D:/_ai_brain").resolve()
    return root

REPO_ROOT = detect_repo_root()

APPROVED_QUANT_ROOTS = [
    "data/quant",
    "experiments/quant",
    "reports/quant",
    "logs/quant",
    "contracts/quant",
    "docs/quant_mvp",
    "scripts/quant",
    "tests/quant",
]

def ensure_within_repo(path: Path | str) -> Path:
    """Fail-closed check to ensure a path is within the repo root."""
    p = Path(path).resolve()
    if not str(p).startswith(str(REPO_ROOT)):
        raise PermissionError(f"Path escape detected: {p} is outside {REPO_ROOT}")
    return p

def is_approved_quant_path(path: Path | str) -> bool:
    """Verify if a path is within the approved Quant directories."""
    p = ensure_within_repo(path)
    rel = p.relative_to(REPO_ROOT)
    rel_str = str(rel).replace("\\", "/")
    return any(rel_str.startswith(approved) for approved in APPROVED_QUANT_ROOTS)

def quant_path(*parts: str) -> Path:
    """Join parts to the repo root and ensure it is an approved quant path."""
    p = REPO_ROOT.joinpath(*parts).resolve()
    if not is_approved_quant_path(p):
        raise PermissionError(f"Path is not an approved Quant location: {p}")
    return p
