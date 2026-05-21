import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

def log_message(msg: str, log_file: Path):
    timestamp = datetime.now().isoformat()
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    if log_file.parent.exists():
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")

def main():
    parser = argparse.ArgumentParser(description="Build video index CSV from downloaded metadata.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run without writing CSV")
    parser.add_argument("--run", action="store_false", dest="dry_run", help="Actually write the CSV")
    parser.add_argument("--output-root", default="knowledge/matfinog_youtube", help="Root directory")
    
    args = parser.parse_args()

    root_dir = Path(args.output_root)
    raw_dir = root_dir / "raw"
    processed_dir = root_dir / "processed"
    log_dir = root_dir / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "03_index.log"
    log_message(f"Starting index build. Dry-run: {args.dry_run}", log_file)

    csv_path = processed_dir / "video_index.csv"

    if not raw_dir.exists():
        log_message(f"Raw directory does not exist: {raw_dir}", log_file)
        sys.exit(0)

    # Find all .info.json files
    info_files = list(raw_dir.rglob("*.info.json"))
    log_message(f"Found {len(info_files)} .info.json files.", log_file)

    rows = []
    headers = [
        "video_id", "title", "upload_date", "url", "duration",
        "view_count", "caption_status", "local_caption_file",
        "local_info_json", "processed_at"
    ]

    for info_path in info_files:
        video_dir = info_path.parent
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            video_id = data.get("id", "UNKNOWN")
            title = data.get("title", "UNKNOWN")
            upload_date = data.get("upload_date", "UNKNOWN")
            url = data.get("webpage_url", f"https://www.youtube.com/watch?v={video_id}")
            duration = data.get("duration", "UNKNOWN")
            view_count = data.get("view_count", "UNKNOWN")
            
            # Check for captions
            vtt_files = list(video_dir.glob("*.vtt"))
            if vtt_files:
                caption_status = "AVAILABLE"
                local_caption_file = str(vtt_files[0].relative_to(root_dir))
            else:
                caption_status = "MISSING"
                local_caption_file = "NONE"
                
            rows.append({
                "video_id": video_id,
                "title": title,
                "upload_date": upload_date,
                "url": url,
                "duration": duration,
                "view_count": view_count,
                "caption_status": caption_status,
                "local_caption_file": local_caption_file,
                "local_info_json": str(info_path.relative_to(root_dir)),
                "processed_at": datetime.now().isoformat()
            })
            
        except Exception as e:
            log_message(f"Error reading {info_path}: {e}", log_file)

    if args.dry_run:
        log_message(f"Dry-run: Would write {len(rows)} rows to {csv_path}", log_file)
    else:
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            log_message(f"Successfully wrote {len(rows)} rows to {csv_path}", log_file)
        except Exception as e:
            log_message(f"Failed to write CSV: {e}", log_file)
            sys.exit(1)

if __name__ == "__main__":
    main()
