# MatFinOg YouTube Canonical Transcript Report

## Purpose of Canonical Normalization
The purpose of this step is to establish a deterministic, high-quality transcript layer for the MatFinOg YouTube corpus. By selecting one canonical transcript per video, we eliminate redundancy (auto vs manual vs duplicate tracks), exclude non-video metadata (channels, playlists), and filter out unusable content (empty or extremely short transcripts). This creates a clean foundation for future topic tagging and research extraction.

## Files Inspected
- `knowledge\matfinog_youtube\processed\video_index.csv`
- `knowledge\matfinog_youtube\processed\transcripts.jsonl`
- `knowledge\matfinog_youtube\processed\transcripts_txt\*.txt`

## Ingestion Metrics (Original Full-Channel Batch)
- **Total Metadata Records:** 232
- **Total Cleaned .txt Files:** 332
- **Initial transcripts.jsonl records:** 168 (One per video with at least one transcript)

## Canonical Normalization Results
- **Number of actual video records processed:** 230
- **Number of metadata-only/channel/playlist records excluded:** 2 (`@MatFinOg`, `UCQrLxbpidT8aCG3CFbM_YMA`)
- **Number of videos with candidate transcripts:** 168
- **Number of canonical transcripts selected:** 154
- **Number of videos missing transcripts:** 62
- **Number of videos with unusable transcripts:** 14 (Empty or < 100 characters)
- **Total empty transcripts found:** 1
- **Total extremely short transcripts found (<100 chars):** 13

## Duplicate Transcript Handling
For videos with multiple transcript tracks (e.g., `.en.txt` and `.en-orig.txt`), the script prioritized manual English captions over auto-generated ones. If texts were identical, the manual label was preserved. If multiple usable candidates existed, the longest one was selected to ensure maximum information density.

## Caption Source Distribution
- **Manual English:** 154
- **Auto English:** 0 (Usable manual English was available for all selected videos)
- **Unknown:** 0

## Canonical Transcript Length Stats
- **Shortest canonical transcript length:** 119 characters
- **Longest canonical transcript length:** 6861 characters
- **Average canonical transcript length:** 586 characters

## Issues Found
- 14 videos have transcripts that are too short to be useful for research (e.g., just intro music or very brief mentions).
- 62 videos (mostly Shorts) have no captions available at all.
- Many videos have redundant transcript files (`.en.txt` and `.en-orig.txt`) with identical content.

## Recommended Fixes
- None at this stage. The canonical layer correctly identifies and isolates usable content.

## Safety Validation
- **STATUS: SAFE TO PROCEED**
- This process did NOT produce any financial advice, trading signals, investment recommendations, broker logic, bot logic, or live trading automation.
- No external APIs were called.
- No embeddings or RAG were added.

## Conclusion
The MatFinOg YouTube corpus now has a verified canonical layer. It is ready for the next milestone: **Automated Workflow/Prompts Extraction and Topic Tagging.**
