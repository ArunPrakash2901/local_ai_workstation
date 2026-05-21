# MatFinOg YouTube Transcript Ingestion

## Purpose
This pipeline safely downloads and processes public YouTube captions/subtitles for the MatFinOg channel.
This pipeline is intended **strictly for personal research, workflow extraction, and quant-learning.**

## Safety Scope & Constraints
- **NO Financial Advice:** This pipeline does not produce financial advice, trading signals, or investment recommendations.
- **NO Live Trading:** This pipeline is not connected to any broker or automated trading system.
- **Captions Only:** This pipeline ONLY downloads public text captions/subtitles and video metadata. It **does not download videos or audio.**
- **No Private Data:** It strictly accesses public YouTube content.
- **No Embeddings (Yet):** This current milestone does not implement embeddings, RAG, or vector databases.

## Setup Requirements

1. Make sure Python 3.x is installed.
2. Check if `yt-dlp` is installed:
   ```powershell
   yt-dlp --version
   ```
3. If `yt-dlp` is missing, install it:
   ```powershell
   python -m pip install yt-dlp
   ```
*(Note: No large dependencies like pandas or ML libraries are required for this milestone).*

## Usage

All scripts support a `--dry-run` flag which is safe to run anytime.

### 8. Workstation Planning
The ingested corpus has been used to generate product requirements and planning documentation for a future "Workflow Coach" module in the Local AI Workstation.
These documents can be found in `knowledge/matfinog_youtube/planning/`. They strictly focus on research and learning scaffolding, prohibiting automated live execution.

### 9. Prompt Library
The output of Step 7 has been processed into a safe, structured Prompt Library under `knowledge/matfinog_youtube/prompt_library/`. This serves as the data foundation for future read-only Workflow Browser UIs without generating any new LLM content.

### 10. Research Notebook & Review Queue
A deterministic pipeline seeds high-potential prompts into a Human Review Queue (`knowledge/matfinog_youtube/review_queue/human_review_queue_seed.csv`). Prompts approved by a human can be scaffolded into safe, non-executable Research Notebooks (`knowledge/matfinog_youtube/notebooks/research_notebook_template.md`). This process explicitly enforces boundaries against generating trading signals or financial advice.

### 11. CLI Knowledge Base Browser
A minimal read-only CLI script is available to inspect the Prompt Library, Workflow Index, Topic Index, Review Queue, and Notebook Template. It enforces the same strict safety boundaries.

**Usage Examples:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\08_browse_knowledge_base.py overview
python knowledge\matfinog_youtube\scripts\08_browse_knowledge_base.py list-prompts --limit 10
python knowledge\matfinog_youtube\scripts\08_browse_knowledge_base.py list-prompts --prompt-type validation_question --limit 10
python knowledge\matfinog_youtube\scripts\08_browse_knowledge_base.py show-prompt --prompt-id <prompt_id>
python knowledge\matfinog_youtube\scripts\08_browse_knowledge_base.py review-queue --limit 30
python knowledge\matfinog_youtube\scripts\08_browse_knowledge_base.py list-workflows
python knowledge\matfinog_youtube\scripts\08_browse_knowledge_base.py list-topics
python knowledge\matfinog_youtube\scripts\08_browse_knowledge_base.py notebook-template
python knowledge\matfinog_youtube\scripts\08_browse_knowledge_base.py validate
```


### 1. Download Captions
Downloads the first 30 videos' captions and `.info.json` metadata. Uses a download archive to support resumability.

**Dry Run:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\01_download_youtube_captions.py --dry-run
```

**Execute:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\01_download_youtube_captions.py --run --limit 30
```

### 2. Clean VTT Transcripts
Converts raw `.vtt` subtitles into clean `.txt` files. Existing text files are not overwritten unless `--force` is used.

**Dry Run:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\02_clean_vtt_transcripts.py --dry-run
```

**Execute:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\02_clean_vtt_transcripts.py
```

### 3. Build Video Index
Generates `video_index.csv` summarizing the available metadata and caption status.

**Dry Run:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\03_build_video_index.py --dry-run
```

**Execute:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\03_build_video_index.py
```

### 4. Build Transcripts JSONL
Combines metadata and cleaned text into a single `transcripts.jsonl` file.

**Dry Run:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\04_build_transcripts_jsonl.py --dry-run
```

**Execute:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\04_build_transcripts_jsonl.py
```

### 5. Build Canonical Transcripts
Produces a single deterministic canonical transcript per video, excluding duplicates and metadata-only records.

**Dry Run:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\05_build_canonical_transcripts.py --dry-run
```

**Execute:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\05_build_canonical_transcripts.py --run
```

If outputs already exist and need rebuilding:
```powershell
python knowledge\matfinog_youtube\scripts\05_build_canonical_transcripts.py --run --force
```

### 6. Tag Transcript Topics
Categorises canonical transcripts into thematic groups using deterministic keyword matching.

**Dry Run:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\06_tag_transcript_topics.py --dry-run
```

**Execute:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\06_tag_transcript_topics.py --run
```

If outputs already exist and need rebuilding:
```powershell
python knowledge\matfinog_youtube\scripts\06_tag_transcript_topics.py --run --force
```

### 7. Extract Workflow Patterns
Identifies reusable workflow patterns and research prompt candidates from the tagged MatFinOg transcript corpus using deterministic matching.

**Dry Run:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\07_extract_workflow_patterns.py --dry-run
```

**Execute:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\07_extract_workflow_patterns.py --run
```

If outputs already exist and need rebuilding:
```powershell
python knowledge\matfinog_youtube\scripts\07_extract_workflow_patterns.py --run --force
```

## Full-channel Ingestion

Downloads all available public captions and metadata for the channel. This process is resumable via the download archive.

**Note:** This mode may take longer depending on the channel size. It strictly downloads captions and metadata, never video or audio.

**Dry Run:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\01_download_youtube_captions.py --dry-run --all
```

**Execute:**
```powershell
cd D:\_ai_brain
python knowledge\matfinog_youtube\scripts\01_download_youtube_captions.py --run --all

# After download, rebuild the corpus:
python knowledge\matfinog_youtube\scripts\02_clean_vtt_transcripts.py
python knowledge\matfinog_youtube\scripts\03_build_video_index.py
python knowledge\matfinog_youtube\scripts\04_build_transcripts_jsonl.py
python knowledge\matfinog_youtube\scripts\05_build_canonical_transcripts.py --run
python knowledge\matfinog_youtube\scripts\06_tag_transcript_topics.py --run
```

## Current Limitations & Future Work
- Currently limited to the first 30 videos to establish safe processing boundaries.
- No semantic tagging, topic generation, or vector search is enabled yet (awaiting a future approved milestone).
