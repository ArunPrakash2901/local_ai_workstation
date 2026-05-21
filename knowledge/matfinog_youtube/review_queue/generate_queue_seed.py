import json
import csv
import os
from datetime import datetime

# Paths
INPUT_JSONL = r"D:\_ai_brain\knowledge\matfinog_youtube\prompt_library\prompt_library.jsonl"
OUTPUT_CSV = r"D:\_ai_brain\knowledge\matfinog_youtube\review_queue\human_review_queue_seed.csv"

# Ensure output directory exists
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# Rules for filtering
TARGET_PROMPT_TYPES = {
    "validation_question",
    "risk_review_question",
    "workflow_design_question",
    "workstation_feature_question",
    "replication_question"
}

def is_safe(prompt):
    # Strictly enforce safety flags
    if prompt.get("safety_financial_advice_generated"): return False
    if prompt.get("safety_trading_signal_generated"): return False
    if prompt.get("safety_bot_logic_generated"): return False
    if prompt.get("safety_live_trading_logic_generated"): return False
    
    # Exclude anything that looks like a trade recommendation in the title or text
    text = prompt.get("prompt_text", "").lower()
    unsafe_words = ["buy", "sell", "long", "short", "invest in", "recommendation"]
    if any(word in text for word in unsafe_words):
        return False
        
    return True

def generate_seed():
    seed_items = []
    
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
                
            if record.get("prompt_type") in TARGET_PROMPT_TYPES and is_safe(record):
                seed_items.append(record)
                
            if len(seed_items) >= 30:
                break
                
    # Write to CSV
    fieldnames = [
        "queue_item_id", "prompt_id", "prompt_type", "source_workflow_id", 
        "source_video_id", "source_title", "priority", "review_status", 
        "reviewer", "recommended_next_action", "safety_notes", "created_at"
    ]
    
    current_time = datetime.utcnow().isoformat() + "Z"
    
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, item in enumerate(seed_items):
            row = {
                "queue_item_id": f"Q-{i+1:03d}-{item.get('prompt_id')[:10]}",
                "prompt_id": item.get("prompt_id"),
                "prompt_type": item.get("prompt_type"),
                "source_workflow_id": item.get("source_workflow_id"),
                "source_video_id": item.get("source_video_id"),
                "source_title": item.get("source_title"),
                "priority": "medium",
                "review_status": "new",
                "reviewer": "HUMAN_REQUIRED",
                "recommended_next_action": item.get("suggested_next_human_action", "Needs review"),
                "safety_notes": "Passed automated safe word check. Human must verify no financial advice.",
                "created_at": current_time
            }
            writer.writerow(row)
            
    print(f"Successfully wrote {len(seed_items)} items to {OUTPUT_CSV}")

if __name__ == "__main__":
    generate_seed()
