import os
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

RISKY_FOLDERS = {
    "node_modules", ".git", "venv", "env", "__pycache__", "dist", "build", "cache",
    ".next", ".nuxt", ".target", "bin", "obj", ".idea", ".vscode", ".terraform"
}

RISKY_EXTENSIONS = {
    ".csv", ".parquet", ".xlsx", ".xls", ".db", ".sqlite", ".bin", ".pkl", ".h5", ".pt", ".onnx",
    ".jpg", ".png", ".gif", ".mp4", ".mov", ".zip", ".tar", ".gz", ".7z", ".pdf",
    ".env", ".pem", ".key", ".crt", ".pfx", ".p12", ".asc"
}

HEAVYWEIGHT_SIZE_THRESHOLD = 10 * 1024 * 1024  # 10 MB

def run_inventory(project_path: Path, output_root: Path, dry_run: bool = True) -> Dict[str, Any]:
    project_path = project_path.resolve()
    
    # Validation
    if project_path.parent == project_path: # Root drive
        raise ValueError(f"Drive root scans are forbidden: {project_path}")
    
    if not project_path.exists() or not project_path.is_dir():
        raise ValueError(f"Project path does not exist or is not a directory: {project_path}")

    project_id = project_path.name
    inventory_dir = output_root / "project_inventories"
    inventory_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = inventory_dir / f"{project_id}_inventory.md"
    manifest_path = inventory_dir / f"{project_id}_inventory.json"
    
    stats = {
        "total_files": 0,
        "total_dirs": 0,
        "risky_folders_found": [],
        "risky_extensions_found": set(),
        "heavyweight_files": [],
        "has_graphifyignore": False
    }
    
    inventory_data = []
    
    # Shallow scan
    for root, dirs, files in os.walk(project_path):
        rel_root = os.path.relpath(root, project_path)
        if rel_root == ".":
            rel_root = ""
            
        # Filter dirs in place to prevent descending into risky folders
        original_dirs = list(dirs)
        dirs[:] = [d for d in dirs if d not in RISKY_FOLDERS and not d.startswith(".")]
        
        for d in original_dirs:
            if d in RISKY_FOLDERS:
                stats["risky_folders_found"].append(os.path.join(rel_root, d))
        
        stats["total_dirs"] += len(dirs)
        
        if rel_root == "" and ".graphifyignore" in files:
            stats["has_graphifyignore"] = True
            
        for f in files:
            stats["total_files"] += 1
            f_path = Path(root) / f
            rel_f_path = os.path.join(rel_root, f)
            
            ext = f_path.suffix.lower()
            if ext in RISKY_EXTENSIONS:
                stats["risky_extensions_found"].add(ext)
            
            try:
                size = f_path.stat().st_size
                if size > HEAVYWEIGHT_SIZE_THRESHOLD:
                    stats["heavyweight_files"].append({"path": rel_f_path, "size": size})
            except OSError:
                size = -1
                
            inventory_data.append({
                "path": rel_f_path,
                "size": size,
                "extension": ext
            })

    stats["risky_extensions_found"] = sorted(list(stats["risky_extensions_found"]))
    
    status = "SAFE_FOR_GRAPHIFY_PLAN"
    if not stats["has_graphifyignore"]:
        status = "NEEDS_IGNORE_REVIEW"
    if len(stats["heavyweight_files"]) > 20 or len(stats["risky_folders_found"]) > 10:
        status = "NEEDS_IGNORE_REVIEW"
        
    result = {
        "project_id": project_id,
        "project_path": str(project_path),
        "timestamp": datetime.datetime.now().isoformat(),
        "status": status,
        "stats": stats,
        "inventory_sample_count": len(inventory_data)
    }
    
    if not dry_run:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Inventory Report: {project_id}\n\n")
            f.write(f"- **Project Path**: `{project_path}`\n")
            f.write(f"- **Status**: `{status}`\n")
            f.write(f"- **Timestamp**: {result['timestamp']}\n\n")
            f.write("## Stats\n")
            f.write(f"- Total Files (scanned): {stats['total_files']}\n")
            f.write(f"- Total Dirs (scanned): {stats['total_dirs']}\n")
            f.write(f"- Has `.graphifyignore`: {stats['has_graphifyignore']}\n\n")
            
            if stats["risky_folders_found"]:
                f.write("## Risky Folders Detected (Skipped)\n")
                for d in stats["risky_folders_found"][:10]:
                    f.write(f"- `{d}`\n")
                if len(stats["risky_folders_found"]) > 10:
                    f.write(f"- ... and {len(stats['risky_folders_found']) - 10} more\n")
                f.write("\n")
                
            if stats["heavyweight_files"]:
                f.write("## Heavyweight Files (>10MB)\n")
                for h in stats["heavyweight_files"][:10]:
                    f.write(f"- `{h['path']}` ({h['size'] / 1024 / 1024:.2f} MB)\n")
                if len(stats["heavyweight_files"]) > 10:
                    f.write(f"- ... and {len(stats['heavyweight_files']) - 10} more\n")
                f.write("\n")
                
            if stats["risky_extensions_found"]:
                f.write("## Risky Extensions Found\n")
                f.write(", ".join(f"`{e}`" for e in stats["risky_extensions_found"]) + "\n\n")
                
    return result

if __name__ == "__main__":
    # Minimal CLI for standalone test if needed
    import sys
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        o = Path("repo_context_lane")
        res = run_inventory(p, o, dry_run=False)
        print(json.dumps(res, indent=2))
