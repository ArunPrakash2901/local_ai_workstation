import argparse
import csv
import json
import sys
import yaml
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

def log_message(msg: str, log_file: Path = None):
    timestamp = datetime.now().isoformat()
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    if log_file and log_file.parent.exists():
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")

def get_evidence_snippet(text: str, matches: list, max_len: int = 200) -> str:
    """Extract a short snippet around the first keyword match."""
    if not matches:
        return ""
    
    first_match = matches[0].lower()
    try:
        idx = text.lower().find(first_match)
        if idx == -1:
            return ""
        
        start = max(0, idx - 50)
        end = min(len(text), idx + len(first_match) + 50)
        snippet = text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet[:max_len]
    except:
        return ""

def main():
    parser = argparse.ArgumentParser(description="Deterministic transcript tagging using taxonomy.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run without writing files")
    parser.add_argument("--run", action="store_false", dest="dry_run", help="Actually execute writing files")
    parser.add_argument("--output-root", default="knowledge/matfinog_youtube", help="Root directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files")
    parser.add_argument("--threshold", type=int, default=1, help="Minimum matches to assign a topic")
    
    args = parser.parse_args()

    root_dir = Path(args.output_root)
    processed_dir = root_dir / "processed"
    log_dir = root_dir / "logs"
    taxonomy_path = root_dir / "topic_taxonomy.yaml"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "06_tagging.log"

    log_message(f"Starting Topic Tagging. Dry-run: {args.dry_run}", log_file)

    canonical_jsonl_path = processed_dir / "canonical_transcripts.jsonl"
    output_jsonl_path = processed_dir / "transcript_topic_tags.jsonl"
    output_csv_path = processed_dir / "topic_index.csv"
    report_path = processed_dir / "TOPIC_TAGGING_REPORT.md"

    if not canonical_jsonl_path.exists():
        log_message(f"Error: canonical_transcripts.jsonl not found at {canonical_jsonl_path}", log_file)
        sys.exit(1)

    if not taxonomy_path.exists():
        log_message(f"Error: topic_taxonomy.yaml not found at {taxonomy_path}", log_file)
        sys.exit(1)

    if not args.force and (output_jsonl_path.exists() or output_csv_path.exists()):
        log_message("Tagging outputs already exist. Use --force to overwrite.", log_file)
        if not args.dry_run:
            sys.exit(0)

    # 1. Load Taxonomy
    try:
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            taxonomy_data = yaml.safe_load(f)
        topics = taxonomy_data.get("topics", [])
        taxonomy_version = taxonomy_data.get("taxonomy_metadata", {}).get("version", "1.0")
        log_message(f"Loaded taxonomy version {taxonomy_version} with {len(topics)} topics.", log_file)
    except Exception as e:
        log_message(f"Error loading taxonomy: {e}", log_file)
        sys.exit(1)

    # 2. Load Canonical Transcripts
    records = []
    try:
        with open(canonical_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
        log_message(f"Loaded {len(records)} canonical transcripts.", log_file)
    except Exception as e:
        log_message(f"Error loading transcripts: {e}", log_file)
        sys.exit(1)

    # 3. Tagging
    tagged_records = []
    topic_stats = {t["id"]: {"video_count": 0, "match_count": 0, "example_videos": []} for t in topics}
    all_matched_keywords = Counter()
    uncategorized_count = 0

    for rec in records:
        text_lower = rec["canonical_transcript_text"].lower()
        matched_topics = []
        topic_scores = {}
        topic_matched_keywords = {}
        evidence_snippets = {}

        for topic in topics:
            t_id = topic["id"]
            if t_id == "unknown_or_uncategorized":
                continue
            
            keywords = topic.get("keywords", [])
            patterns = topic.get("phrase_patterns", [])
            
            matches = []
            for kw in keywords:
                # Use regex for word boundaries to avoid partial matches
                count = len(re.findall(r'\b' + re.escape(kw.lower()) + r'\b', text_lower))
                if count > 0:
                    matches.extend([kw] * count)
                    all_matched_keywords[kw] += count
            
            for pat in patterns:
                count = len(re.findall(re.escape(pat.lower()), text_lower))
                if count > 0:
                    matches.extend([pat] * count)
                    all_matched_keywords[pat] += count

            if len(matches) >= args.threshold:
                matched_topics.append(t_id)
                topic_scores[t_id] = len(matches)
                topic_matched_keywords[t_id] = list(set(matches))
                evidence_snippets[t_id] = get_evidence_snippet(rec["canonical_transcript_text"], list(set(matches)))
                
                topic_stats[t_id]["video_count"] += 1
                topic_stats[t_id]["match_count"] += len(matches)
                if len(topic_stats[t_id]["example_videos"]) < 3:
                    topic_stats[t_id]["example_videos"].append({
                        "id": rec["video_id"],
                        "title": rec["title"]
                    })

        if not matched_topics:
            matched_topics = ["unknown_or_uncategorized"]
            topic_scores["unknown_or_uncategorized"] = 1
            uncategorized_count += 1
            topic_stats["unknown_or_uncategorized"]["video_count"] += 1

        primary_topic = matched_topics[0]
        if len(matched_topics) > 1:
            # Pick topic with highest score
            primary_topic = max(matched_topics, key=lambda x: topic_scores.get(x, 0))

        tagged_rec = {
            "creator": rec["creator"],
            "platform": rec["platform"],
            "video_id": rec["video_id"],
            "title": rec["title"],
            "url": rec["url"],
            "upload_date": rec["upload_date"],
            "duration": rec["duration"],
            "transcript_char_count": rec["transcript_char_count"],
            "transcript_word_count": rec["transcript_word_count"],
            "matched_topics": matched_topics,
            "primary_topic": primary_topic,
            "topic_scores": topic_scores,
            "matched_keywords": topic_matched_keywords,
            "evidence_snippets": evidence_snippets,
            "tagging_method": "deterministic_keyword_matching",
            "taxonomy_version": taxonomy_version,
            "processed_at": datetime.now().isoformat(),
            "safety_financial_advice_generated": False,
            "safety_trading_signal_generated": False,
            "safety_bot_logic_generated": False,
            "safety_live_trading_logic_generated": False
        }
        tagged_records.append(tagged_rec)

    log_message(f"Tagging complete. Categorized: {len(records) - uncategorized_count}, Uncategorized: {uncategorized_count}", log_file)

    # 4. Write Outputs
    if args.dry_run:
        log_message(f"Dry-run: Would write {len(tagged_records)} records and topic index.", log_file)
    else:
        try:
            # Write JSONL
            with open(output_jsonl_path, "w", encoding="utf-8") as f:
                for rec in tagged_records:
                    f.write(json.dumps(rec) + "\n")
            log_message(f"Successfully wrote {len(tagged_records)} tagged records to {output_jsonl_path}", log_file)

            # Write CSV Index
            csv_rows = []
            for topic in topics:
                t_id = topic["id"]
                stat = topic_stats[t_id]
                csv_rows.append({
                    "topic_id": t_id,
                    "topic_description": topic["description"],
                    "video_count": stat["video_count"],
                    "total_keyword_matches": stat["match_count"],
                    "example_video_ids": "|".join([v["id"] for v in stat["example_videos"]]),
                    "example_titles": "|".join([v["title"] for v in stat["example_videos"]]),
                    "processed_at": datetime.now().isoformat()
                })
            
            headers = ["topic_id", "topic_description", "video_count", "total_keyword_matches", "example_video_ids", "example_titles", "processed_at"]
            with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(csv_rows)
            log_message(f"Successfully wrote topic index to {output_csv_path}", log_file)

            # Write Report
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("# MatFinOg YouTube Topic Tagging Report\n\n")
                f.write("## Purpose of Topic Tagging\n")
                f.write("To create a transparent, auditable indexing layer for the MatFinOg corpus using deterministic keyword matching based on a custom taxonomy.\n\n")
                f.write("## Files Inspected\n")
                f.write(f"- `{canonical_jsonl_path.name}`\n")
                f.write(f"- `{taxonomy_path.name}`\n\n")
                f.write("## Execution Summary\n")
                f.write(f"- **Canonical Transcripts Processed:** {len(records)}\n")
                f.write(f"- **Taxonomy Topics:** {len(topics)}\n")
                f.write(f"- **Categorized Videos:** {len(records) - uncategorized_count}\n")
                f.write(f"- **Uncategorized Videos:** {uncategorized_count}\n\n")
                
                f.write("## Topic Distribution\n")
                f.write("| Topic ID | Video Count | Match Count |\n")
                f.write("| --- | --- | --- |\n")
                for topic in topics:
                    t_id = topic["id"]
                    f.write(f"| {t_id} | {topic_stats[t_id]['video_count']} | {topic_stats[t_id]['match_count']} |\n")
                f.write("\n")

                f.write("## Top 10 Matched Keywords\n")
                for kw, count in all_matched_keywords.most_common(10):
                    f.write(f"- **{kw}**: {count} matches\n")
                f.write("\n")

                multi_topic_videos = [r for r in tagged_records if len(r["matched_topics"]) > 3]
                f.write("## Videos with Many Topics (>3)\n")
                for v in multi_topic_videos:
                    f.write(f"- **{v['title']}** ({v['video_id']}): {len(v['matched_topics'])} topics\n")
                f.write("\n")

                f.write("## Limitations\n")
                f.write("- Keyword-based tagging is sensitive to specific terminology and may miss context.\n")
                f.write("- False positives can occur if keywords are used in unrelated contexts.\n")
                f.write("- Does not capture semantic nuances beyond the provided keyword list.\n\n")

                f.write("## Safety Validation\n")
                f.write("- **STATUS: SAFE TO PROCEED**\n")
                f.write("- No financial advice, trading signals, or bot logic was generated.\n")
                f.write("- Tagging is strictly descriptive and categorical.\n")
                f.write("- No external APIs or LLMs were used.\n")

            log_message(f"Successfully wrote tagging report to {report_path}", log_file)

        except Exception as e:
            log_message(f"Failed to write outputs: {e}", log_file)
            sys.exit(1)

if __name__ == "__main__":
    main()
