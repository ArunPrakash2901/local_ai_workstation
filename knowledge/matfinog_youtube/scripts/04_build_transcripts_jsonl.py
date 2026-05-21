import argparse
import json
import csv
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
    parser = argparse.ArgumentParser(description="Build transcripts JSONL from index and cleaned text.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run without writing JSONL")
    parser.add_argument("--run", action="store_false", dest="dry_run", help="Actually write the JSONL")
    parser.add_argument("--output-root", default="knowledge/matfinog_youtube", help="Root directory")
    
    args = parser.parse_args()

    root_dir = Path(args.output_root)
    processed_dir = root_dir / "processed"
    txt_dir = processed_dir / "transcripts_txt"
    log_dir = root_dir / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "04_jsonl.log"
    log_message(f"Starting JSONL build. Dry-run: {args.dry_run}", log_file)

    csv_path = processed_dir / "video_index.csv"
    jsonl_path = processed_dir / "transcripts.jsonl"

    if not csv_path.exists():
        log_message(f"Video index not found: {csv_path}. Please run 03_build_video_index.py first.", log_file)
        sys.exit(0)

    if not txt_dir.exists():
        log_message(f"Transcripts directory not found: {txt_dir}. Please run 02_clean_vtt_transcripts.py first.", log_file)
        sys.exit(0)

    records = []
    
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                video_id = row.get("video_id")
                if row.get("caption_status") == "AVAILABLE":
                    # Look for the cleaned text file
                    # We expect it to start with video_id (e.g., id.en.txt)
                    txt_files = list(txt_dir.glob(f"{video_id}*.txt"))
                    
                    if txt_files:
                        txt_file = txt_files[0]
                        with open(txt_file, "r", encoding="utf-8") as tf:
                            transcript_text = tf.read().strip()
                            
                        # Infer source from name if possible
                        transcript_source = "auto" if ".en" in txt_file.name else "unknown"
                        
                        record = {
                            "creator": "MatFinOg",
                            "platform": "youtube",
                            "video_id": video_id,
                            "title": row.get("title", "UNKNOWN"),
                            "upload_date": row.get("upload_date", "UNKNOWN"),
                            "url": row.get("url", "UNKNOWN"),
                            "duration": row.get("duration", "UNKNOWN"),
                            "source_file": str(txt_file.relative_to(root_dir)),
                            "transcript_text": transcript_text,
                            "transcript_source": transcript_source,
                            "processed_at": datetime.now().isoformat()
                        }
                        records.append(record)
                    else:
                        log_message(f"Warning: CSV says captions available, but no txt found for {video_id}", log_file)
                        
    except Exception as e:
        log_message(f"Error reading index or text: {e}", log_file)
        sys.exit(1)

    if args.dry_run:
        log_message(f"Dry-run: Would write {len(records)} records to {jsonl_path}", log_file)
    else:
        try:
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec) + "\n")
            log_message(f"Successfully wrote {len(records)} records to {jsonl_path}", log_file)
        except Exception as e:
            log_message(f"Failed to write JSONL: {e}", log_file)
            sys.exit(1)

if __name__ == "__main__":
    main()
