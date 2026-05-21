import os
import json
import csv
import yaml
import re
import argparse
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="Extract workflow patterns and research prompt candidates from MatFinOg transcripts.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without saving files.")
    parser.add_argument("--run", action="store_true", help="Execute the extraction.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files.")
    return parser.parse_args()

def load_taxonomy(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_jsonl(path):
    data = []
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return data

def get_snippets(text, keyword, max_snippets=2, context_chars=100):
    snippets = []
    # Use regex to find keyword with word boundaries
    pattern = rf"\b{re.escape(keyword)}\b"
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    
    for match in matches[:max_snippets]:
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        snippet = text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        snippets.append(snippet)
    return snippets

def generate_prompts(video_id, title, url, workflow_id, topic_ids, snippets):
    prompts = []
    
    # Prompt templates based on workflow
    templates = {
        "research_paper_to_backtest_workflow": [
            {"type": "replication_question", "text": "What specific data points and parameters would be required to replicate the core claims mentioned in this video?"},
            {"type": "validation_question", "text": "How can the methodology described here be validated using out-of-sample data to ensure robustness?"}
        ],
        "market_inefficiency_hypothesis_workflow": [
            {"type": "research_question", "text": "What evidence would be needed to test this market structure hypothesis empirically?"},
            {"type": "validation_question", "text": "Are there specific institutional constraints that could explain this price behavior beyond simple randomness?"}
        ],
        "risk_first_strategy_review_workflow": [
            {"type": "risk_review_question", "text": "What specific risk checks and drawdown limits should be defined before promoting this concept to a strategy candidate?"},
            {"type": "risk_review_question", "text": "How does the proposed risk management approach handle tail events or extreme market conditions?"}
        ],
        "execution_microstructure_review_workflow": [
            {"type": "validation_question", "text": "What metrics (e.g., slippage, fill rate) should be tracked to measure the execution quality of this workflow?"},
            {"type": "workflow_design_question", "text": "How can VWAP or other benchmarks be used to evaluate the effectiveness of this execution strategy?"}
        ],
        "ai_assisted_quant_learning_workflow": [
            {"type": "workflow_design_question", "text": "Which parts of this research process could be safely automated using an AI assistant while maintaining human validation?"},
            {"type": "workstation_feature_question", "text": "What kind of prompting framework would best support a learner trying to replicate this specific quant workflow?"}
        ],
        "workstation_module_candidate_workflow": [
            {"type": "workstation_feature_question", "text": "What workstation module or checklist could be built to support this repeatable research process?"},
            {"type": "workflow_design_question", "text": "How can this workflow be decomposed into discrete, testable stages for a local AI workstation?"}
        ],
        "psychological_process_and_discipline_workflow": [
            {"type": "workflow_design_question", "text": "What journaling or routine-tracking features would help reinforce the discipline discussed in this video?"},
            {"type": "research_question", "text": "How can we objectively measure adherence to the process rules defined here?"}
        ]
    }
    
    if workflow_id in templates:
        for i, template in enumerate(templates[workflow_id]):
            prompt = {
                "prompt_id": f"P-{video_id}-{workflow_id}-{i+1}",
                "source_video_id": video_id,
                "source_title": title,
                "source_url": url,
                "source_workflow_id": workflow_id,
                "supporting_topic_ids": topic_ids,
                "prompt_type": template["type"],
                "prompt_text": template["text"],
                "evidence_snippet": snippets[0] if snippets else "N/A",
                "allowed_use": "learning, research organisation, workflow planning, future PRD planning",
                "forbidden_use": "financial advice, trading signals, investment recommendations, live trading automation, broker execution",
                "requires_human_review": True,
                "processed_at": datetime.now().isoformat(),
                "safety_financial_advice_generated": False,
                "safety_trading_signal_generated": False,
                "safety_bot_logic_generated": False,
                "safety_live_trading_logic_generated": False
            }
            prompts.append(prompt)
            
    return prompts

def main():
    args = parse_args()
    
    if not args.run and not args.dry_run:
        print("Error: Specify --run or --dry-run.")
        return

    # Paths
    base_dir = os.path.join("knowledge", "matfinog_youtube")
    processed_dir = os.path.join(base_dir, "processed")
    taxonomy_path = os.path.join(base_dir, "workflow_taxonomy.yaml")
    transcripts_path = os.path.join(processed_dir, "canonical_transcripts.jsonl")
    topic_tags_path = os.path.join(processed_dir, "transcript_topic_tags.jsonl")
    
    output_patterns_path = os.path.join(processed_dir, "workflow_patterns.jsonl")
    output_index_csv = os.path.join(processed_dir, "workflow_index.csv")
    output_prompts_path = os.path.join(processed_dir, "research_prompt_candidates.jsonl")
    output_report_path = os.path.join(processed_dir, "WORKFLOW_EXTRACTION_REPORT.md")

    if args.run and not args.force:
        if any(os.path.exists(p) for p in [output_patterns_path, output_index_csv, output_prompts_path, output_report_path]):
            print("Error: Output files already exist. Use --force to overwrite.")
            return

    print(f"--- MatFinOg Workflow Extraction ({'DRY RUN' if args.dry_run else 'EXECUTE'}) ---")
    
    taxonomy = load_taxonomy(taxonomy_path)
    transcripts = load_jsonl(transcripts_path)
    topic_tags_list = load_jsonl(topic_tags_path)
    
    # Create lookup for topic tags
    topic_tags_map = {t["video_id"]: t for t in topic_tags_list}
    
    workflow_results = []
    all_prompts = []
    workflow_stats = {w["workflow_id"]: {"count": 0, "keywords": 0, "phrases": 0, "videos": []} for w in taxonomy["workflows"]}
    
    for transcript in transcripts:
        video_id = transcript["video_id"]
        text = transcript["canonical_transcript_text"]
        title = transcript["title"]
        
        tags = topic_tags_map.get(video_id, {})
        matched_topics = tags.get("matched_topics", [])
        
        video_workflows = []
        workflow_scores = {}
        matched_keywords_all = {}
        evidence_snippets_all = {}
        
        for wf in taxonomy["workflows"]:
            wf_id = wf["workflow_id"]
            if wf_id == "unknown_or_low_confidence_workflow":
                continue
                
            kw_matches = []
            for kw in wf["keywords"]:
                if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
                    kw_matches.append(kw)
            
            phrase_matches = []
            for phrase in wf["phrase_patterns"]:
                if re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE):
                    phrase_matches.append(phrase)
            
            topic_overlap = [t for t in matched_topics if t in wf["relevant_topic_ids"]]
            
            score = len(kw_matches) + len(phrase_matches) + (len(topic_overlap) * 2)
            
            if score >= wf["minimum_score"]:
                video_workflows.append(wf_id)
                workflow_scores[wf_id] = score
                matched_keywords_all[wf_id] = kw_matches + phrase_matches
                
                # Get snippets for first matched keyword
                if matched_keywords_all[wf_id]:
                    snippets = get_snippets(text, matched_keywords_all[wf_id][0])
                    evidence_snippets_all[wf_id] = snippets
                    
                    # Generate prompts
                    prompts = generate_prompts(video_id, title, transcript["url"], wf_id, topic_overlap, snippets)
                    all_prompts.extend(prompts)
                
                workflow_stats[wf_id]["count"] += 1
                workflow_stats[wf_id]["keywords"] += len(kw_matches)
                workflow_stats[wf_id]["phrases"] += len(phrase_matches)
                workflow_stats[wf_id]["videos"].append(video_id)
        
        if not video_workflows:
            video_workflows = ["unknown_or_low_confidence_workflow"]
            workflow_scores["unknown_or_low_confidence_workflow"] = 0
            workflow_stats["unknown_or_low_confidence_workflow"]["count"] += 1
            workflow_stats["unknown_or_low_confidence_workflow"]["videos"].append(video_id)

        primary_workflow = max(workflow_scores, key=workflow_scores.get) if workflow_scores else "unknown_or_low_confidence_workflow"
        
        res = {
            "creator": transcript["creator"],
            "platform": transcript["platform"],
            "video_id": video_id,
            "title": title,
            "url": transcript["url"],
            "upload_date": transcript["upload_date"],
            "duration": transcript["duration"],
            "matched_workflows": video_workflows,
            "primary_workflow": primary_workflow,
            "workflow_scores": workflow_scores,
            "supporting_topics": matched_topics,
            "matched_keywords": matched_keywords_all,
            "evidence_snippets": evidence_snippets_all,
            "extraction_method": "deterministic_keyword_matching",
            "taxonomy_version": taxonomy["taxonomy_metadata"]["version"],
            "processed_at": datetime.now().isoformat(),
            "safety_financial_advice_generated": False,
            "safety_trading_signal_generated": False,
            "safety_bot_logic_generated": False,
            "safety_live_trading_logic_generated": False
        }
        workflow_results.append(res)

    if args.dry_run:
        print(f"Dry run complete. Would process {len(transcripts)} transcripts.")
        print(f"Would generate {len(all_prompts)} research prompt candidates.")
        for wf_id, stats in workflow_stats.items():
            print(f"- {wf_id}: {stats['count']} videos")
        return

    # Save outputs
    with open(output_patterns_path, "w", encoding="utf-8") as f:
        for res in workflow_results:
            f.write(json.dumps(res) + "\n")
            
    with open(output_prompts_path, "w", encoding="utf-8") as f:
        for p in all_prompts:
            f.write(json.dumps(p) + "\n")
            
    with open(output_index_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["workflow_id", "workflow_description", "video_count", "total_keyword_matches", "total_phrase_matches", "supporting_topic_ids", "example_video_ids", "example_titles", "processed_at"])
        
        wf_lookup = {w["workflow_id"]: w for w in taxonomy["workflows"]}
        for wf_id, stats in workflow_stats.items():
            desc = wf_lookup[wf_id]["description"]
            supporting_topics = ",".join(wf_lookup[wf_id].get("relevant_topic_ids", []))
            examples = stats["videos"][:3]
            example_titles = []
            for vid in examples:
                for r in workflow_results:
                    if r["video_id"] == vid:
                        example_titles.append(r["title"])
                        break
            
            writer.writerow([
                wf_id,
                desc,
                stats["count"],
                stats["keywords"],
                stats["phrases"],
                supporting_topics,
                ",".join(examples),
                " | ".join(example_titles),
                datetime.now().isoformat()
            ])

    # Generate Report
    report_content = f"""# MatFinOg Workflow Extraction Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Purpose
Deterministic extraction of reusable workflow patterns and research prompt candidates from the tagged MatFinOg transcript corpus.

## Files Inspected
- `canonical_transcripts.jsonl`
- `transcript_topic_tags.jsonl`
- `workflow_taxonomy.yaml`

## Processing Summary
- Canonical transcripts processed: {len(transcripts)}
- Workflow taxonomy entries: {len(taxonomy["workflows"])}
- Videos matched to workflows: {sum(1 for r in workflow_results if "unknown_or_low_confidence_workflow" not in r["matched_workflows"])}
- Low-confidence/unknown videos: {workflow_stats["unknown_or_low_confidence_workflow"]["count"]}
- Research prompt candidates generated: {len(all_prompts)}

## Workflow Distribution
| Workflow ID | Video Count | Keywords Matched | Phrases Matched |
|-------------|-------------|------------------|-----------------|
"""
    for wf_id, stats in workflow_stats.items():
        report_content += f"| {wf_id} | {stats['count']} | {stats['keywords']} | {stats['phrases']} |\n"

    report_content += "\n## Prompt Type Distribution\n"
    prompt_types = {}
    for p in all_prompts:
        pt = p["prompt_type"]
        prompt_types[pt] = prompt_types.get(pt, 0) + 1
    
    report_content += "| Prompt Type | Count |\n|-------------|-------|\n"
    for pt, count in prompt_types.items():
        report_content += f"| {pt} | {count} |\n"

    report_content += "\n## Example Research Prompt Candidates\n"
    for p in all_prompts[:5]:
        report_content += f"- **{p['prompt_type']}**: \"{p['prompt_text']}\" (Source: {p['source_title']})\n"

    report_content += f"""
## Safety & Compliance
- **Financial Advice Generated:** No
- **Trading Signals Generated:** No
- **Broker/Bot Logic Generated:** No
- **Live Trading Automation:** No

This extraction layer is strictly for educational research and workstation workflow planning.

## Limitations
- Deterministic matching relies on keyword presence and may miss context.
- Scoring threshold is simple and may need tuning.
- "Unknown" videos represent content that doesn't fit the current workflow taxonomy.

## Conclusion
The workflow extraction was successful. It is safe to proceed to PRD and planning synthesis.
"""

    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Extraction complete. Results saved to {processed_dir}")

if __name__ == "__main__":
    main()
