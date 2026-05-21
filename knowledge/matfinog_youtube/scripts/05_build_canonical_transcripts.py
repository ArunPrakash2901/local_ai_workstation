import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

def log_message(msg: str, log_file: Path = None):
    timestamp = datetime.now().isoformat()
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    if log_file and log_file.parent.exists():
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")

def get_transcript_stats(text: str):
    chars = len(text)
    words = len(text.split())
    return chars, words

def is_metadata_only(row: dict) -> bool:
    video_id = row.get("video_id", "")
    duration = str(row.get("duration", "UNKNOWN"))
    if video_id.startswith("@") or video_id.startswith("UC"):
        return True
    if duration == "UNKNOWN" or duration == "0":
        return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Build canonical transcript records.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run without writing files")
    parser.add_argument("--run", action="store_false", dest="dry_run", help="Actually execute writing files")
    parser.add_argument("--output-root", default="knowledge/matfinog_youtube", help="Root directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing canonical files")
    
    args = parser.parse_args()

    # Normalize root_dir to handle different relative paths if needed
    # Assuming script is run from D:\_ai_brain or similar
    root_dir = Path(args.output_root)
    processed_dir = root_dir / "processed"
    txt_dir = processed_dir / "transcripts_txt"
    log_dir = root_dir / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "05_canonical.log"

    log_message(f"Starting Canonical Normalization. Dry-run: {args.dry_run}", log_file)

    video_index_path = processed_dir / "video_index.csv"
    transcripts_jsonl_path = processed_dir / "transcripts.jsonl" # Input (optional but part of requirement)
    
    canonical_jsonl_path = processed_dir / "canonical_transcripts.jsonl"
    canonical_csv_path = processed_dir / "canonical_video_index.csv"

    if not video_index_path.exists():
        log_message(f"Error: video_index.csv not found at {video_index_path}", log_file)
        sys.exit(1)

    if not txt_dir.exists():
        log_message(f"Error: transcripts_txt directory not found at {txt_dir}", log_file)
        sys.exit(1)

    if not args.force and (canonical_jsonl_path.exists() or canonical_csv_path.exists()):
        log_message("Canonical outputs already exist. Use --force to overwrite.", log_file)
        if not args.dry_run:
            sys.exit(0)

    # 1. Load Video Index
    video_records = []
    try:
        with open(video_index_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            video_records = list(reader)
        log_message(f"Loaded {len(video_records)} records from video_index.csv", log_file)
    except Exception as e:
        log_message(f"Error reading video_index.csv: {e}", log_file)
        sys.exit(1)

    # 2. Map all available .txt files
    all_txt_files = list(txt_dir.glob("*.txt"))
    txt_map = {}
    for tf in all_txt_files:
        # Extract video_id from filename (assuming id.suffix.txt)
        # We'll use the part before the first dot as a heuristic, but better to check against known IDs
        stem = tf.name
        # Find which video_id this belongs to
        matching_id = None
        for vr in video_records:
            vid = vr["video_id"]
            if stem.startswith(vid):
                matching_id = vid
                break
        
        if matching_id:
            if matching_id not in txt_map:
                txt_map[matching_id] = []
            txt_map[matching_id].append(tf)

    log_message(f"Mapped {len(all_txt_files)} txt files to {len(txt_map)} video IDs.", log_file)

    canonical_records = []
    canonical_index_rows = []
    
    stats = {
        "metadata_only": 0,
        "transcript_missing": 0,
        "transcript_unusable": 0,
        "canonical_selected": 0,
        "empty": 0,
        "short": 0
    }

    for row in video_records:
        video_id = row["video_id"]
        title = row["title"]
        
        index_row = {
            "video_id": video_id,
            "title": title,
            "upload_date": row["upload_date"],
            "url": row["url"],
            "duration": row["duration"],
            "view_count": row["view_count"],
            "original_caption_status": row["caption_status"],
            "canonical_status": "unknown",
            "candidate_transcript_count": 0,
            "canonical_source_file": "NONE",
            "transcript_char_count": 0,
            "transcript_word_count": 0,
            "selection_reason": "N/A",
            "processed_at": datetime.now().isoformat()
        }

        if is_metadata_only(row):
            index_row["canonical_status"] = "metadata_only"
            stats["metadata_only"] += 1
            canonical_index_rows.append(index_row)
            continue

        candidates = txt_map.get(video_id, [])
        index_row["candidate_transcript_count"] = len(candidates)

        if not candidates:
            index_row["canonical_status"] = "transcript_missing"
            index_row["selection_reason"] = "No caption files found on disk."
            stats["transcript_missing"] += 1
            canonical_index_rows.append(index_row)
            continue

        # Load and filter candidates
        valid_candidates = []
        for cf in candidates:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                
                char_count, word_count = get_transcript_stats(text)
                
                source = "auto"
                if ".en-orig." in cf.name or "auto" in cf.name:
                    source = "auto"
                elif ".en." in cf.name:
                    source = "manual"
                
                # Check for empty/short
                if char_count == 0:
                    stats["empty"] += 1
                    continue
                if char_count < 100:
                    stats["short"] += 1
                    # We still keep it as a candidate but it might be rejected later if all are short
                
                valid_candidates.append({
                    "file": cf,
                    "text": text,
                    "char_count": char_count,
                    "word_count": word_count,
                    "source": source
                })
            except Exception as e:
                log_message(f"Error reading candidate {cf}: {e}", log_file)

        if not valid_candidates:
            index_row["canonical_status"] = "transcript_unusable"
            index_row["selection_reason"] = "All candidate transcripts were empty."
            stats["transcript_unusable"] += 1
            canonical_index_rows.append(index_row)
            continue

        # Filter out extremely short ones if there are better options
        usable_candidates = [c for c in valid_candidates if c["char_count"] >= 100]
        
        if not usable_candidates:
            # Fallback to the "best" short one if that's all we have? 
            # Instruction says: "If all transcript candidates are empty or extremely short, mark the video as transcript_unusable."
            index_row["canonical_status"] = "transcript_unusable"
            index_row["selection_reason"] = f"All {len(valid_candidates)} candidates were under 100 characters."
            stats["transcript_unusable"] += 1
            canonical_index_rows.append(index_row)
            continue

        # Selection logic among usable candidates
        # 1. Manual English
        manuals = [c for c in usable_candidates if c["source"] == "manual"]
        # 2. Auto English
        autos = [c for c in usable_candidates if c["source"] == "auto"]
        
        selected = None
        reason = ""
        
        if manuals:
            # Pick longest manual
            selected = max(manuals, key=lambda x: x["char_count"])
            reason = "Selected longest manual English transcript."
        elif autos:
            # Pick longest auto
            selected = max(autos, key=lambda x: x["char_count"])
            reason = "Selected longest auto-generated English transcript."
        else:
            # Pick longest of whatever is left
            selected = max(usable_candidates, key=lambda x: x["char_count"])
            reason = "Selected longest available transcript (source ambiguous)."

        # Deduplication check: if multiple have same text, we already picked one by priority/length.
        
        index_row["canonical_status"] = "canonical_selected"
        index_row["canonical_source_file"] = str(selected["file"].relative_to(root_dir))
        index_row["transcript_char_count"] = selected["char_count"]
        index_row["transcript_word_count"] = selected["word_count"]
        index_row["selection_reason"] = reason
        stats["canonical_selected"] += 1
        
        canonical_records.append({
            "creator": "MatFinOg",
            "platform": "youtube",
            "video_id": video_id,
            "title": title,
            "upload_date": row["upload_date"],
            "url": row["url"],
            "duration": row["duration"],
            "canonical_transcript_text": selected["text"],
            "canonical_source_file": index_row["canonical_source_file"],
            "canonical_transcript_source": selected["source"],
            "candidate_transcript_count": index_row["candidate_transcript_count"],
            "selection_reason": reason,
            "transcript_char_count": selected["char_count"],
            "transcript_word_count": selected["word_count"],
            "processed_at": index_row["processed_at"],
            "safety_financial_advice_generated": False,
            "safety_trading_signal_generated": False,
            "safety_bot_logic_generated": False,
            "safety_live_trading_logic_generated": False
        })
        
        canonical_index_rows.append(index_row)

    log_message(f"Normalization complete. Selected: {stats['canonical_selected']}, Missing: {stats['transcript_missing']}, Unusable: {stats['transcript_unusable']}, Metadata-only: {stats['metadata_only']}", log_file)

    if args.dry_run:
        log_message(f"Dry-run: Would write {len(canonical_records)} records to JSONL and {len(canonical_index_rows)} rows to CSV.", log_file)
    else:
        try:
            with open(canonical_jsonl_path, "w", encoding="utf-8") as f:
                for rec in canonical_records:
                    f.write(json.dumps(rec) + "\n")
            log_message(f"Successfully wrote {len(canonical_records)} records to {canonical_jsonl_path}", log_file)
            
            headers = [
                "video_id", "title", "upload_date", "url", "duration",
                "view_count", "original_caption_status", "canonical_status",
                "candidate_transcript_count", "canonical_source_file",
                "transcript_char_count", "transcript_word_count",
                "selection_reason", "processed_at"
            ]
            with open(canonical_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(canonical_index_rows)
            log_message(f"Successfully wrote {len(canonical_index_rows)} rows to {canonical_csv_path}", log_file)
            
        except Exception as e:
            log_message(f"Failed to write outputs: {e}", log_file)
            sys.exit(1)

if __name__ == "__main__":
    main()
