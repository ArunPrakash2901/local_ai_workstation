import csv
import json
import os

input_workflows = r'D:\_ai_brain\knowledge\matfinog_youtube\processed\workflow_index.csv'
input_prompts = r'D:\_ai_brain\knowledge\matfinog_youtube\processed\research_prompt_candidates.jsonl'
output_matrix = r'D:\_ai_brain\knowledge\matfinog_youtube\planning\TRACEABILITY_MATRIX.csv'

os.makedirs(os.path.dirname(output_matrix), exist_ok=True)

requirements = {
    'research_paper_to_backtest_workflow': 'REQ-WF-001',
    'market_inefficiency_hypothesis_workflow': 'REQ-WF-002',
    'risk_first_strategy_review_workflow': 'REQ-WF-003',
    'execution_microstructure_review_workflow': 'REQ-WF-004',
    'ai_assisted_quant_learning_workflow': 'REQ-WF-005',
    'workstation_module_candidate_workflow': 'REQ-WF-006',
    'psychological_process_and_discipline_workflow': 'REQ-WF-007'
}

rows = []
with open(input_workflows, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        wf_id = row['workflow_id']
        if wf_id in requirements:
            req_id = requirements[wf_id]
            rows.append({
                'requirement_id': req_id,
                'requirement_title': f"Support {wf_id.replace('_', ' ').title()}",
                'source_type': 'workflow_index',
                'source_id': row['example_video_ids'].split(',')[0].strip() if row['example_video_ids'] else 'UNKNOWN',
                'source_title': row['example_titles'].split('|')[0].strip() if row['example_titles'] else 'UNKNOWN',
                'related_topic_id': row['supporting_topic_ids'],
                'related_workflow_id': wf_id,
                'related_prompt_type': 'N/A',
                'evidence_count': row['video_count'],
                'planning_document': 'WORKFLOW_REQUIREMENTS.md',
                'safety_notes': 'No financial advice generated'
            })

with open(input_prompts, 'r', encoding='utf-8') as f:
    # Just sample up to 20 prompts for brevity in the traceability matrix, ensuring a mix
    # We want a manageable CSV.
    sample_prompts = []
    for line in f:
        data = json.loads(line)
        wf_id = data.get('source_workflow_id')
        if wf_id in requirements:
            sample_prompts.append(data)
            if len(sample_prompts) >= 50:
                break
    
    for i, data in enumerate(sample_prompts):
        wf_id = data.get('source_workflow_id')
        rows.append({
            'requirement_id': f"REQ-PR-{data['prompt_type'].upper()}-{i}",
            'requirement_title': f"Support {data['prompt_type']}",
            'source_type': 'research_prompt',
            'source_id': data.get('source_video_id', 'UNKNOWN'),
            'source_title': data.get('source_title', 'UNKNOWN'),
            'related_topic_id': ','.join(data.get('supporting_topic_ids', [])),
            'related_workflow_id': wf_id,
            'related_prompt_type': data.get('prompt_type', 'UNKNOWN'),
            'evidence_count': 1,
            'planning_document': 'HUMAN_AI_OPERATING_MODEL.md',
            'safety_notes': 'No trading signals generated'
        })

with open(output_matrix, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'requirement_id', 'requirement_title', 'source_type', 'source_id',
        'source_title', 'related_topic_id', 'related_workflow_id',
        'related_prompt_type', 'evidence_count', 'planning_document', 'safety_notes'
    ])
    writer.writeheader()
    writer.writerows(rows)

print("Traceability matrix generated.")
