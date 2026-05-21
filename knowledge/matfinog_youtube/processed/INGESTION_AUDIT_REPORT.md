# MatFinOg YouTube Ingestion Audit Report

## Batch Audit Summary
- **Target Channel:** https://www.youtube.com/@MatFinOg
- **Milestone:** 01 (Initial 30-video batch)
- **Date:** 2026-05-21
- **Status:** SUCCESS

## Commands Run
1. `python -m pip install yt-dlp`
2. `python knowledge\matfinog_youtube\scripts\01_download_youtube_captions.py --run --limit 30`
3. `python knowledge\matfinog_youtube\scripts\02_clean_vtt_transcripts.py --run`
4. `python knowledge\matfinog_youtube\scripts\03_build_video_index.py --run`
5. `python knowledge\matfinog_youtube\scripts\04_build_transcripts_jsonl.py --run`

## Files Inspected
- `knowledge\matfinog_youtube\raw\`
- `knowledge\matfinog_youtube\processed\`
- `knowledge\matfinog_youtube\processed\transcripts_txt\`
- `knowledge\matfinog_youtube\processed\video_index.csv`
- `knowledge\matfinog_youtube\processed\transcripts.jsonl`

## Raw Output Counts
- **Video Folders under raw\:** 34 (Includes 30 shorts, 2 videos, and 2 metadata/playlist folders)
- **.info.json files:** 34
- **.vtt caption files:** 54
- **Videos with metadata but no captions:** 7 (Mostly newer shorts or specific metadata-only entries)
- **Caption Source:** Predominantly auto-generated English (`en` and `en-orig`)

## Processed Transcript Counts
- **Cleaned .txt transcript files:** 54
- **Empty transcripts:** 0
- **Shortest transcript length:** 137 characters
- **Artifact Check:** Sample inspection confirmed NO WEBVTT headers, NO timestamps, NO cue numbers, and NO repeated subtitle fragments. Text is clean paragraph-style.

## video_index.csv Validation
- **Row count:** 34
- **Missing video_id count:** 0
- **Missing title count:** 0
- **Missing url count:** 0
- **Caption Status Distribution:**
  - AVAILABLE: 27
  - MISSING: 7
- **Path integrity:** All `local_caption_file` and `local_info_json` paths exist relative to repo root.

## transcripts.jsonl Validation
- **Record count:** 27 (Matches unique videos with AVAILABLE captions)
- **Missing transcript_text count:** 0
- **Transcript Lengths:**
  - Minimum: 137 characters
  - Maximum: 6861 characters
  - Average: 825 characters
- **Source Integrity:** All records have `creator: MatFinOg` and `platform: youtube`.

## Issues Found
- **Minor:** Some videos (specifically 7 items) do not have captions available on YouTube. This is expected behavior for auto-generated captions on very short or recently uploaded content.
- **Pathing:** Scripts use Windows-style backslashes in some outputs, which is consistent with the current workstation OS (`win32`).

## Recommended Fixes
- None for this milestone. The pipeline is robust and handles missing captions gracefully.

## Safety Statement
- **NO Financial Advice:** This ingestion batch produced strictly raw and cleaned transcript text.
- **NO Trading Signals:** No signals, indicators, or recommendations were generated.
- **NO Broker Logic:** No connection to external trading platforms or broker APIs was established.
- **NO Bot Logic:** No automated trading or order generation logic was implemented.
- **NO Embeddings/RAG:** No vectorization or semantic analysis was performed.
- **NO Video/Audio:** Strictly text-based captions and metadata were processed.

## Conclusion
It is **SAFE** to proceed to the next milestone (e.g., transcript topic tagging, workflow extraction, or research prompt generation).
