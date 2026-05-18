# Phase 7: Research Run Design

## Executive Summary
This document designs the second domain-specific runner for the AI Workstation: the **Research Run**. Building on the patterns established by the Learning Run, the Research Run focuses on the structured analysis of academic papers, technical documentation, and market data. It transforms raw sources into falsifiable hypotheses and evidence-based summaries. This domain serves as a high-reasoning, non-mutative bridge between strategic planning and eventual technical execution.

## 1. Rationale: Why Research after Learning?
- **Pattern Reuse**: Research directly leverages the "Source -> Analysis -> Synthesis -> Decision" loop proven in the Learning domain.
- **Strategic Foundation**: Reliable research is a prerequisite for high-stakes domains like `product` and `trading-research`.
- **Safety**: Like learning, research is purely informational and does not risk codebase corruption or financial loss.
- **Evidence Gating**: Establishes a standard for "Evidence-Based AI Development" where agents are only authorized to implement patterns that have been locally researched and verified.

## 2. Execution Pre-requisites
A Research Run is authorized when the stronghold is in the `LOCAL_CHECKLIST_READY` state.
1. **Stronghold Type**: Must be `research`.
2. **Contract Ready**: A clear research question and hypothesis must exist.
3. **Master Plan**: A Senior Architect has defined the source gathering and analysis strategy.
4. **Local Checklist**: A local model has decomposed the strategy into tactical analysis tasks.

## 3. Command Surface
**Primary Command:**
```bash
ws research-run <stronghold_id_or_path> --review-paper [--dry-run] [--model m]
```
- `--review-paper`: Initiates the analysis of a specific source identified in the `literature_map.md`.
- `--dry-run`: Previews the analysis plan (which sections of the paper to focus on) without calling models.

## 4. Information Architecture

### 4.1 Ingested Artifacts
- `architect_plan.md`: The strategic research roadmap.
- `local_checklist.md`: The source of the current tactical analysis task.
- `literature_map.md`: The registry of sources (URLs, local PDF paths, or abstracts).
- `hypothesis_log.md`: The current list of claims being investigated.
- `evidence_matrix.md`: The map of supporting/refuting data points.

### 4.2 Generated Artifacts
- `papers/<timestamp>_paper_review_plan.md`: The dry-run output outlining the analysis scope.
- `evidence/<timestamp>_source_notes.md`: Detailed notes extracted from the source.
- `hypothesis_log.md` (Updated): Updates to the status or confidence of hypotheses.
- `evidence_matrix.md` (Updated): Links extracted notes to specific hypotheses.
- `loop_log.md`: Auditable record of the research activity.

## 5. Anti-Hallucination & Evidence Anchoring
To prevent models from hallucinating contents of complex papers:
1. **Source Anchoring**: All notes in `source_notes.md` must include explicit page/paragraph references (once PDF parsing is enabled) or direct quotes.
2. **Classification Gating**: The model must distinguish between:
   - **Source Summary**: Objective extraction of what the author stated.
   - **Hypothesis**: A falsifiable claim derived from the source.
   - **Evidence**: Specific data points supporting or refuting a hypothesis.
   - **Speculation**: Qualitative ideas not directly proven by the source.
   - **Implementation Idea**: Tactical "how-to" notes for future agent runs.

## 6. Actor Roles
- **Human (Lead Researcher)**: Provides the source materials, reviews the evidence matrix, and makes the final decision on hypothesis validity.
- **Local Ollama (Research Intern)**: Summarizes papers, extracts key data points, populates the evidence matrix, and identifies contradictions.
- **Browser (Senior Architect)**: Performs high-context strategic reviews when research findings lead to a major pivot in the master plan.
- **WSL (Orchestrator)**: Manages the files, maintains the bibliography, and enforces safety gates.

## 7. Terminal States
- `RESEARCH_REVIEW_PLAN_READY`: Preflight checks passed; analysis plan generated.
- `RESEARCH_SOURCE_NOTES_READY`: Source analysis complete and recorded.
- `RESEARCH_HYPOTHESIS_READY`: Evidence synthesized and linked to a claim.
- `RESEARCH_NEEDS_MORE_EVIDENCE`: Current sources are insufficient to confirm the hypothesis.
- `RESEARCH_BLOCKED`: Conflicting evidence or inaccessible sources.

## 8. Safety & Isolation
- **No Automatic Strategy Deployment**: Research runs generate summaries, not executable strategies.
- **No Financial Interaction**: Strictly prohibited from proposing live trading actions.
- **No Code Mutation**: The runner remains strictly read-only relative to project repositories.

## 9. Integration with Trading Research
The Research domain acts as the **Information Feeder** for `trading-research`. 
1. Research Stronghold: Analyzes a paper on "Mean Reversion in Crypto".
2. Decision Gate: Classification `RESEARCH_HYPOTHESIS_READY`.
3. Transition: A `trading-research` stronghold is initialized, ingesting the research summary as its core `contract.md`.

## 10. Recommended MVP Implementation
**Phase 7.1: Dry-Run Review Planner**
`ws research-run <id> --review-paper --dry-run`
1. Resolves the stronghold and the next literature item.
2. Inspects `hypothesis_log.md`.
3. Generates a `papers/<timestamp>_paper_review_plan.md` outlining the "Points of Interest" to be extracted from the source to satisfy the current hypothesis.
4. No model calls.

## Next Steps
1. Create `scripts/ws_research_run.sh`.
2. Implement the dry-run review planner.
3. Establish the "Research Intern" system prompt for `hermes3:8b`.
4. Validate against the newly created "Agentic RAG" research stronghold.
