import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

def setup_directories(root_dir: Path):
    dirs = [
        root_dir / "raw",
        root_dir / "processed",
        root_dir / "logs"
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def log_message(msg: str, log_file: Path):
    timestamp = datetime.now().isoformat()
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    if log_file.parent.exists():
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")

def main():
    parser = argparse.ArgumentParser(description="Safely download MatFinOg YouTube captions")
    parser.add_argument("--run", action="store_true", help="Execute the download (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Print command only")
    parser.add_argument("--limit", type=int, help="Number of videos to check (default 30 if --all not set)")
    parser.add_argument("--all", action="store_true", help="Download all available public captions")
    parser.add_argument("--channel-url", default="https://www.youtube.com/@MatFinOg", help="Target channel URL")
    parser.add_argument("--output-root", default="knowledge/matfinog_youtube", help="Root directory for outputs")
    parser.add_argument("--archive-file", default="processed/download_archive.txt", help="Archive file relative to output root")
    parser.add_argument("--force", action="store_true", help="Force overwrite (not typically used here, handled by yt-dlp)")
    
    args = parser.parse_args()

    # Dry-run is the default unless --run is explicitly passed
    is_dry_run = not args.run

    root_dir = Path(args.output_root)
    setup_directories(root_dir)
    
    log_file = root_dir / "logs" / "01_download.log"
    log_message(f"Starting script. Dry-run: {is_dry_run}", log_file)

    archive_path = root_dir / args.archive_file
    raw_dir = root_dir / "raw"
    
    # yt-dlp command definition
    # Note: --skip-download prevents video/audio download
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "en.*",
        "--write-info-json",
        "--download-archive", str(archive_path),
        "-o", f"{raw_dir}/%(id)s/%(id)s.%(ext)s",
        args.channel_url
    ]

    # Handle limit/all logic
    if not args.all:
        limit = args.limit if args.limit is not None else 30
        cmd.extend(["--playlist-end", str(limit)])
        log_message(f"Limit set to: {limit}", log_file)
    else:
        log_message("Full channel mode enabled (--all). No playlist limit applied.", log_file)

    log_message(f"Prepared command: {' '.join(cmd)}", log_file)

    if is_dry_run:
        log_message("Dry-run mode enabled. Exiting without execution.", log_file)
        sys.exit(0)

    log_message("Executing yt-dlp...", log_file)
    try:
        # Run the command safely using subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            log_message(f"STDOUT: {result.stdout}", log_file)
        if result.stderr:
            log_message(f"STDERR: {result.stderr}", log_file)
            
        if result.returncode == 0:
            log_message("Download completed successfully.", log_file)
        else:
            log_message(f"yt-dlp returned non-zero exit code: {result.returncode}", log_file)
            sys.exit(result.returncode)
    except Exception as e:
        log_message(f"ERROR: {str(e)}", log_file)
        sys.exit(1)

if __name__ == "__main__":
    main()
