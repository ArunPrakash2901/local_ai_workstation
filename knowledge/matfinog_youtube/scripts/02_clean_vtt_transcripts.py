import argparse
import re
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

def clean_vtt_text(vtt_content: str) -> str:
    """Removes VTT headers, timestamps, formatting and reduces duplicate lines."""
    lines = vtt_content.splitlines()
    cleaned_lines = []
    
    # Simple state/regex approach
    timestamp_pattern = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*")
    markup_pattern = re.compile(r"<[^>]+>")
    
    for line in lines:
        line = line.strip()
        # Skip empty lines
        if not line:
            continue
        # Skip VTT Header
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        # Skip Timestamps
        if timestamp_pattern.match(line):
            continue
        # Skip numeric cue IDs or UUIDs (heuristics)
        if line.isdigit() or re.match(r"^[0-9a-f\-]{36}$", line):
            continue
        
        # Remove markup like <c> or <00:00:00.000>
        text = markup_pattern.sub("", line).strip()
        
        # Simple duplicate suppression (auto-generated captions often repeat lines)
        if text and (not cleaned_lines or cleaned_lines[-1] != text):
            cleaned_lines.append(text)
            
    # Join and paragraphize slightly
    return " ".join(cleaned_lines)

def main():
    parser = argparse.ArgumentParser(description="Clean raw VTT transcripts into text.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run without writing files")
    parser.add_argument("--run", action="store_false", dest="dry_run", help="Actually execute writing files")
    parser.add_argument("--output-root", default="knowledge/matfinog_youtube", help="Root directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing txt files")
    
    args = parser.parse_args()

    root_dir = Path(args.output_root)
    raw_dir = root_dir / "raw"
    processed_dir = root_dir / "processed" / "transcripts_txt"
    log_dir = root_dir / "logs"
    
    processed_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "02_clean.log"
    log_message(f"Starting VTT cleaning. Dry-run: {args.dry_run}", log_file)

    if not raw_dir.exists():
        log_message(f"Raw directory does not exist: {raw_dir}", log_file)
        sys.exit(0)

    # Glob for all VTTs in the raw_dir subfolders
    vtt_files = list(raw_dir.rglob("*.vtt"))
    log_message(f"Found {len(vtt_files)} VTT files to process.", log_file)

    success_count = 0
    skip_count = 0

    for vtt_path in vtt_files:
        video_id = vtt_path.parent.name
        # Some subs might have lang codes in the name, e.g., id.en.vtt. Let's just use the vtt file stem
        txt_filename = f"{vtt_path.stem}.txt"
        txt_path = processed_dir / txt_filename

        if txt_path.exists() and not args.force:
            log_message(f"Skipping {txt_filename} (already exists). Use --force to overwrite.", log_file)
            skip_count += 1
            continue
            
        if args.dry_run:
            log_message(f"Dry-run: Would clean {vtt_path.name} -> {txt_path}", log_file)
            success_count += 1
            continue

        try:
            with open(vtt_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            cleaned = clean_vtt_text(content)
            
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(cleaned)
                
            log_message(f"Cleaned {vtt_path.name}", log_file)
            success_count += 1
        except Exception as e:
            log_message(f"Failed to process {vtt_path}: {e}", log_file)

    log_message(f"Finished. Success: {success_count}, Skipped: {skip_count}", log_file)

if __name__ == "__main__":
    main()
