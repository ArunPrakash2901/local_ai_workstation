import json
import csv
import os
from collections import defaultdict
from datetime import datetime

INPUT_FILE = r"D:\_ai_brain\knowledge\matfinog_youtube\processed\research_prompt_candidates.jsonl"
OUTPUT_JSONL = r"D:\_ai_brain\knowledge\matfinog_youtube\prompt_library\prompt_library.jsonl"
OUTPUT_CSV = r"D:\_ai_brain\knowledge\matfinog_youtube\prompt_library\prompt_library_index.csv"

def generate_title(prompt_type, workflow_id):
    pt = prompt_type.replace('_', ' ').title()
    wf = workflow_id.replace('_workflow', '').replace('_', ' ').title()
    return f"{pt} for {wf}"

def get_action(prompt_type):
    actions = {
        "validation_question": "List validation checks before treating this as a strategy candidate.",
        "risk_review_question": "Identify required data before requesting implementation.",
        "replication_question": "Review the source video and write the hypothesis in your own words.",
        "research_question": "Ask a cloud model to draft a research plan only after reviewing the source.",
        "workflow_design_question": "Check whether the idea belongs in learning notes, research backlog, or quant MVP backlog.",
        "workstation_feature_question": "Review whether this feature adds value to the workstation MVP."
    }
    return actions.get(prompt_type, "Review the source video and write the hypothesis in your own words.")

def process_library():
    stats = defaultdict(lambda: {
        "prompt_count": 0,
        "example_prompt_ids": [],
        "example_source_titles": [],
        "human_review_required_count": 0
    })

    records_processed = 0

    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
         open(OUTPUT_JSONL, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            if not line.strip(): continue
            data = json.loads(line)
            
            # Map fields and add new ones
            record = {
                "prompt_id": data.get("prompt_id"),
                "prompt_title": generate_title(data.get("prompt_type", ""), data.get("source_workflow_id", "")),
                "prompt_type": data.get("prompt_type"),
                "prompt_text": data.get("prompt_text"),
                "source_workflow_id": data.get("source_workflow_id"),
                "source_topic_ids": data.get("supporting_topic_ids", []),
                "source_video_id": data.get("source_video_id"),
                "source_title": data.get("source_title"),
                "source_url": data.get("source_url"),
                "evidence_snippet": data.get("evidence_snippet"),
                "intended_use": data.get("allowed_use"),
                "forbidden_use": data.get("forbidden_use"),
                "human_review_required": data.get("requires_human_review", True),
                "suggested_next_human_action": get_action(data.get("prompt_type", "")),
                "safety_financial_advice_generated": False,
                "safety_trading_signal_generated": False,
                "safety_bot_logic_generated": False,
                "safety_live_trading_logic_generated": False,
                "source_artifact": "research_prompt_candidates.jsonl",
                "processed_at": datetime.utcnow().isoformat()
            }
            
            f_out.write(json.dumps(record) + '\n')
            records_processed += 1
            
            # Aggregate stats
            key = (record["prompt_type"], record["source_workflow_id"])
            stats[key]["prompt_count"] += 1
            if record["human_review_required"]:
                stats[key]["human_review_required_count"] += 1
            
            if len(stats[key]["example_prompt_ids"]) < 2:
                stats[key]["example_prompt_ids"].append(record["prompt_id"])
            if len(stats[key]["example_source_titles"]) < 2 and record["source_title"] not in stats[key]["example_source_titles"]:
                stats[key]["example_source_titles"].append(record["source_title"])

    # Write CSV Index
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            "prompt_type", "source_workflow_id", "prompt_count", 
            "example_prompt_ids", "example_source_titles", 
            "human_review_required_count", "processed_at"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        now = datetime.utcnow().isoformat()
        for (pt, wf), st in stats.items():
            writer.writerow({
                "prompt_type": pt,
                "source_workflow_id": wf,
                "prompt_count": st["prompt_count"],
                "example_prompt_ids": "; ".join(st["example_prompt_ids"]),
                "example_source_titles": "; ".join(st["example_source_titles"]),
                "human_review_required_count": st["human_review_required_count"],
                "processed_at": now
            })
            
    print(f"Processed {records_processed} records.")

if __name__ == "__main__":
    process_library()
