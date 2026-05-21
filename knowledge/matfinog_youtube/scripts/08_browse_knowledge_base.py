import argparse
import json
import csv
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_LIB_FILE = BASE_DIR / "prompt_library" / "prompt_library.jsonl"
PROMPT_INDEX_FILE = BASE_DIR / "prompt_library" / "prompt_library_index.csv"
WORKFLOW_INDEX_FILE = BASE_DIR / "processed" / "workflow_index.csv"
TOPIC_INDEX_FILE = BASE_DIR / "processed" / "topic_index.csv"
REVIEW_QUEUE_FILE = BASE_DIR / "review_queue" / "human_review_queue_seed.csv"
NOTEBOOK_TEMPLATE_FILE = BASE_DIR / "notebooks" / "research_notebook_template.md"

def print_safety_statement():
    print("\n--- SAFETY BOUNDARY ---")
    print("This is a read-only local learning and research organisation tool.")
    print("WARNING: No financial advice, trading signals, or live trading automation logic generated.")
    print("-----------------------\n")

def load_jsonl(filepath):
    records = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except FileNotFoundError:
        pass
    return records

def load_csv(filepath):
    records = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    except FileNotFoundError:
        pass
    return records

def cmd_overview(args):
    prompts = load_jsonl(PROMPT_LIB_FILE)
    workflows = load_csv(WORKFLOW_INDEX_FILE)
    topics = load_csv(TOPIC_INDEX_FILE)
    queue = load_csv(REVIEW_QUEUE_FILE)

    prompt_types = set(p.get("prompt_type") for p in prompts if p.get("prompt_type"))

    print("=== Knowledge Base Overview ===")
    print(f"Prompt Library Records: {len(prompts)}")
    print(f"Unique Prompt Types: {len(prompt_types)}")
    print(f"Workflow Index Rows: {len(workflows)}")
    print(f"Topic Index Rows: {len(topics)}")
    print(f"Review Queue Seed Items: {len(queue)}")
    
    print("\nPaths:")
    try:
        print(f"- Prompt Library: {PROMPT_LIB_FILE.relative_to(BASE_DIR.parent)}")
        print(f"- Workflow Index: {WORKFLOW_INDEX_FILE.relative_to(BASE_DIR.parent)}")
        print(f"- Topic Index:    {TOPIC_INDEX_FILE.relative_to(BASE_DIR.parent)}")
        print(f"- Review Queue:   {REVIEW_QUEUE_FILE.relative_to(BASE_DIR.parent)}")
        print(f"- Notebook Tmpl:  {NOTEBOOK_TEMPLATE_FILE.relative_to(BASE_DIR.parent)}")
    except ValueError:
        print(f"- Prompt Library: {PROMPT_LIB_FILE}")
        print(f"- Workflow Index: {WORKFLOW_INDEX_FILE}")
        print(f"- Topic Index:    {TOPIC_INDEX_FILE}")
        print(f"- Review Queue:   {REVIEW_QUEUE_FILE}")
        print(f"- Notebook Tmpl:  {NOTEBOOK_TEMPLATE_FILE}")

    print_safety_statement()

def cmd_list_prompts(args):
    prompts = load_jsonl(PROMPT_LIB_FILE)
    filtered = prompts

    if args.prompt_type:
        filtered = [p for p in filtered if p.get("prompt_type") == args.prompt_type]
    if args.workflow:
        filtered = [p for p in filtered if p.get("source_workflow_id") == args.workflow]
    if args.video_id:
        filtered = [p for p in filtered if p.get("source_video_id") == args.video_id]

    limit = min(args.limit, 100)
    filtered = filtered[:limit]

    print(f"=== Prompts (Showing {len(filtered)}) ===")
    for p in filtered:
        print(f"ID: {p.get('prompt_id')}")
        print(f"Type: {p.get('prompt_type')}")
        print(f"Workflow: {p.get('source_workflow_id')}")
        print(f"Title: {p.get('source_title', p.get('prompt_title'))}")
        if p.get("suggested_next_human_action"):
            print(f"Action: {p.get('suggested_next_human_action')}")
        print("-" * 20)
    print_safety_statement()

def cmd_show_prompt(args):
    prompts = load_jsonl(PROMPT_LIB_FILE)
    prompt = next((p for p in prompts if p.get("prompt_id") == args.prompt_id), None)

    if not prompt:
        print(f"Error: Prompt {args.prompt_id} not found.")
        sys.exit(1)

    print(f"=== Prompt Details: {prompt.get('prompt_id')} ===")
    print(f"Title: {prompt.get('prompt_title')}")
    print(f"Type: {prompt.get('prompt_type')}")
    print(f"Workflow: {prompt.get('source_workflow_id')}")
    print(f"Topics: {prompt.get('source_topic_ids')}")
    print(f"Video ID: {prompt.get('source_video_id')}")
    print(f"Source Title: {prompt.get('source_title')}")
    print(f"Source URL: {prompt.get('source_url')}")
    print("\nPrompt Text:")
    print(prompt.get('prompt_text', 'N/A')[:500] + ("..." if len(prompt.get('prompt_text', '')) > 500 else ""))
    print("\nEvidence Snippet:")
    print(prompt.get('evidence_quotes', 'N/A')[:200] + ("..." if len(prompt.get('evidence_quotes', '')) > 200 else ""))
    print(f"\nIntended Use: {prompt.get('intended_use')}")
    print(f"Forbidden Use: {prompt.get('forbidden_use')}")
    print(f"Suggested Action: {prompt.get('suggested_next_human_action')}")
    
    print("\nSafety Flags:")
    flags = {k:v for k,v in prompt.items() if str(k).startswith('safety_')}
    for k, v in flags.items():
        print(f"  {k}: {v}")

    print_safety_statement()

def cmd_list_workflows(args):
    workflows = load_csv(WORKFLOW_INDEX_FILE)
    print("=== Workflows ===")
    for w in workflows:
        print(f"ID: {w.get('workflow_id', w.get('workflow_name'))}")
        print(f"Videos: {w.get('video_count')}")
        print(f"Match Count: {w.get('total_match_count', w.get('total_matches', 'N/A'))}")
        print("-" * 20)
    print_safety_statement()

def cmd_list_topics(args):
    topics = load_csv(TOPIC_INDEX_FILE)
    print("=== Topics ===")
    for t in topics:
        print(f"ID: {t.get('topic_id', t.get('topic_name'))}")
        print(f"Videos: {t.get('video_count')}")
        print(f"Match Count: {t.get('total_match_count', t.get('total_matches', 'N/A'))}")
        print("-" * 20)
    print_safety_statement()

def cmd_review_queue(args):
    queue = load_csv(REVIEW_QUEUE_FILE)
    filtered = queue

    if args.prompt_type:
        filtered = [q for q in filtered if q.get("prompt_type") == args.prompt_type]
    if args.priority:
        filtered = [q for q in filtered if q.get("priority") == args.priority]
    if args.workflow:
        filtered = [q for q in filtered if q.get("source_workflow_id") == args.workflow]

    limit = min(args.limit, 100)
    filtered = filtered[:limit]

    print(f"=== Review Queue (Showing {len(filtered)}) ===")
    for q in filtered:
        print(f"Queue ID: {q.get('queue_item_id')}")
        print(f"Prompt ID: {q.get('prompt_id')}")
        print(f"Type: {q.get('prompt_type')}")
        print(f"Workflow: {q.get('source_workflow_id')}")
        print(f"Title: {q.get('source_title', q.get('prompt_title'))}")
        print(f"Priority: {q.get('priority')}")
        print(f"Status: {q.get('review_status')}")
        print(f"Recommended Action: {q.get('recommended_next_action')}")
        print("-" * 20)
    print_safety_statement()

def cmd_notebook_template(args):
    if not NOTEBOOK_TEMPLATE_FILE.exists():
        print("Notebook template not found.")
        sys.exit(1)

    print("=== Notebook Template ===")
    try:
        print(f"Path: {NOTEBOOK_TEMPLATE_FILE.relative_to(BASE_DIR.parent)}")
    except ValueError:
        print(f"Path: {NOTEBOOK_TEMPLATE_FILE}")
    
    sections = []
    with open(NOTEBOOK_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                sections.append(line.strip())
                
    print("\nTop-level Sections:")
    for s in sections:
        if s.startswith('# '):
            print(f"  {s}")
        elif s.startswith('## '):
            print(f"    {s}")

    print("\nSafety Boundary Summary:")
    print("No live trading, no financial advice. Research and validation only.")
    print("Allowed Next Actions: Read code, backtest, paper trade, evaluate risk.")
    print("Forbidden Next Actions: Deploy bot, trade real money, skip risk validation.")
    print_safety_statement()

def cmd_validate(args):
    files_to_check = {
        "prompt_library.jsonl": PROMPT_LIB_FILE,
        "prompt_library_index.csv": PROMPT_INDEX_FILE,
        "workflow_index.csv": WORKFLOW_INDEX_FILE,
        "topic_index.csv": TOPIC_INDEX_FILE,
        "human_review_queue_seed.csv": REVIEW_QUEUE_FILE,
        "research_notebook_template.md": NOTEBOOK_TEMPLATE_FILE
    }

    failed = False
    print("=== Validation ===")
    for name, path in files_to_check.items():
        if path.exists():
            print(f"[OK] {name} exists.")
        else:
            print(f"[FAIL] {name} is missing.")
            failed = True

    prompts = load_jsonl(PROMPT_LIB_FILE)
    if prompts:
        print(f"[OK] Parsed {len(prompts)} records from prompt_library.jsonl.")
    else:
        print("[FAIL] Failed to parse prompt_library.jsonl or it is empty.")
        failed = True

    for i, p in enumerate(prompts):
        flags = [p.get(k) for k in p.keys() if str(k).startswith('safety_')]
        if any(f is True for f in flags):
            print(f"[FAIL] Safety flag violated in prompt {p.get('prompt_id')} at index {i}.")
            failed = True

    queue = load_csv(REVIEW_QUEUE_FILE)
    forbidden_decisions = ["deploy", "trade", "bot"]
    for i, q in enumerate(queue):
        action = str(q.get("recommended_next_action", "")).lower()
        if any(fd in action for fd in forbidden_decisions):
            print(f"[FAIL] Forbidden decision in review queue at index {i}: {action}")
            failed = True

    print("\nValidation Result: " + ("FAILED" if failed else "PASSED"))
    print_safety_statement()
    if failed:
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="MatFinOg Read-Only Knowledge Base Browser")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("overview")

    p_list = subparsers.add_parser("list-prompts")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--prompt-type")
    p_list.add_argument("--workflow")
    p_list.add_argument("--video-id")

    p_show = subparsers.add_parser("show-prompt")
    p_show.add_argument("--prompt-id", required=True)

    subparsers.add_parser("list-workflows")
    subparsers.add_parser("list-topics")

    p_queue = subparsers.add_parser("review-queue")
    p_queue.add_argument("--limit", type=int, default=30)
    p_queue.add_argument("--prompt-type")
    p_queue.add_argument("--priority")
    p_queue.add_argument("--workflow")

    subparsers.add_parser("notebook-template")
    
    subparsers.add_parser("validate")

    args = parser.parse_args()

    if args.command == "overview":
        cmd_overview(args)
    elif args.command == "list-prompts":
        cmd_list_prompts(args)
    elif args.command == "show-prompt":
        cmd_show_prompt(args)
    elif args.command == "list-workflows":
        cmd_list_workflows(args)
    elif args.command == "list-topics":
        cmd_list_topics(args)
    elif args.command == "review-queue":
        cmd_review_queue(args)
    elif args.command == "notebook-template":
        cmd_notebook_template(args)
    elif args.command == "validate":
        cmd_validate(args)

if __name__ == "__main__":
    main()