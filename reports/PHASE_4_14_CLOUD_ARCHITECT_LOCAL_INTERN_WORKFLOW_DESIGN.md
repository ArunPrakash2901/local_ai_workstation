# Phase 4.14: Cloud-Architect and Local-Intern Workflow Design

## Executive Summary
This document formalizes the "Senior Architect / Junior Intern" cognitive hierarchy for the AI Workstation. While local models (Ollama/Hermes 3) provide high-speed qualitative review, they lack the strategic vision and context-handling required to own complex feature architectures. This design re-centers cloud frontier models (Browser-based ChatGPT/Gemini) as the authoritative Feature Architects, while repurposing local models as "Interns" or "Operators" that handle granular plan decomposition, failure analysis, and pre-execution safety audits.

## 1. Cognitive Hierarchy Rationale

### 1.1 Why small local models (Ollama) should not own the master plan
- **Context Truncation**: Local 8B/7B models typically struggle with massive cross-file context packets required for strategic planning.
- **Reasoning Depth**: Advanced architecture requires high-level abstraction and trade-off analysis that frontier models (GPT-4o, Claude 3.5) perform significantly better.
- **Risk Mitigation**: A hallucinated master plan can lead to hours of wasted agent execution and difficult-to-revert codebase corruption.

### 1.2 Decisions requiring Browser/Cloud Architect Review
- Feature decomposition and implementation sequence.
- Cross-module integration patterns.
- Strategic refactoring or introducing new system-wide conventions.
- Final approval of high-risk implementation plans.

### 1.3 Tasks trusted to Local Intern models
- Generating granular checklists from an approved architect plan.
- Summarizing failed agent runs (Codex/Gemini CLI errors).
- Detecting "easy" logic gaps or syntax violations in local worktrees.
- Deciding whether a current state is "clean" enough to justify cloud escalation.

## 2. Information Architecture

### 2.1 Authoritative Plan Management
One document in the Feature Stronghold must be designated as the "Authoritative Plan."
- **Path**: `<feature_path>/architect_plan.md`
- **Pointer**: `state.json` will contain a `master_plan_path` field.
- **Import Flow**: `ws handoff-import` captures the response; a new `ws feature-plan-import` command validates and moves it into the stronghold.

### 2.2 Distinguished Plan Types
| Type | Owner | Role |
| --- | --- | --- |
| `current_plan.md` | WSL (Deterministic) | Record of current file paths and git state. |
| `architect_plan.md` | Cloud (Senior) | The strategic "Source of Truth" for implementation. |
| `local_review.md` | Local Model (Intern) | Qualitative audit of the plan vs. contract. |
| `execution_packet` | Agent Runner | The bounded context sent to Codex/Gemini CLI. |

## 3. Command Surface Enhancements

### 3.1 New & Refined Commands
- `ws feature-architect-handoff <id> --target <browser>`: Packages the entire stronghold context for a "Senior Architect" session.
- `ws feature-plan-import <id> --from-handoff <handoff_id>`: Promotes an imported response to the authoritative `architect_plan.md`.
- `ws feature-local-checklist <id>`: Intern-mode. Converts `architect_plan.md` into granular TODOs in `current_plan.md`.
- `ws feature-local-diagnose <id> --run <run_id>`: Intern-mode. Analyzes a failed agent run and suggests local fixes.

### 3.2 Reducing Manual Friction
- **Single-Prompt Architecture**: `feature-architect-handoff` will generate a high-density "Master Plan Request" prompt, minimizing the number of manual copy-paste rounds.
- **Local Triage**: By using local models to diagnose execution failures, we prevent the "infinite loop" of pasting errors back into the browser for simple fixes.

## 4. State Machine Transitions
1. `VALIDATED_LOCAL`: Deterministic checks pass.
2. `ARCHITECT_REVIEW_READY`: Context packet generated for cloud.
3. `ARCHITECT_PLAN_IMPORTED`: Cloud response promoted to `architect_plan.md`.
4. `LOCAL_REVIEW_ACCEPTED`: Local intern verifies the plan is implementable locally.
5. `READY_FOR_SUPERVISED_AGENT`: Supervised mutation (Worktree) is authorized.

## 5. Next MVP Implementation: `ws feature-architect-handoff`
The immediate priority is not more agent execution, but formalizing the "Architect" bridge.

**Command**:
`ws feature-architect-handoff <feature> --target chatgpt|gemini-browser --purpose master-plan`

**Requirements**:
1. Synthesize all stronghold artifacts (contract, plan, validation, history).
2. Format a "Senior Architect" prompt requesting a master implementation plan.
3. Use `ws handoff-new` logic to store the packet and notify the user.

## 6. Safety & Human Approval
The "Browser" remains the human-gated reasoning lane. No cloud response is imported or promoted without the operator manually running the import command, ensuring the human remains the final arbiter of architectural truth.

## Next Steps
- Implement `scripts/ws_feature_architect_handoff.sh`.
- Implement `scripts/ws_feature_plan_import.sh`.
- Update `ws feature-status` to display the authoritative plan status.
