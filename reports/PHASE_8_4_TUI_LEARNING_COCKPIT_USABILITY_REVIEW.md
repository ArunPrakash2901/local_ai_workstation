# Phase 8.4: TUI Learning Cockpit Usability Review

## Overview
This report evaluates the usability and safety of the **TUI Learning Cockpit** (implemented in Phase 8.3 and hardened in Phase 8.3.1). The cockpit provides a read-only, state-aware dashboard within the workstation's terminal user interface, designed to guide the operator through the interactive learning loop.

## 1. Current Capabilities
The Learning Cockpit currently provides:
- **State Synthesis**: High-level view of the stronghold ID, title, current operational state, and granular session status.
- **Task Tracking**: Explicit display of the last completed task and the currently targeted next study goal.
- **Artifact Resolution**: Automatic mapping of the latest study plans, tutor sessions, answer templates, and assessments.
- **Provenance Verification**: Real-time analysis of the link between exercises and answers, detecting "stale" or "contaminated" evidence.
- **Safety Gating**: Suppression of advancement previews when decisions are potentially stale relative to new exercises.
- **Strategic Guidance**: A recommended next study action with an exact CLI command preview.

## 2. Analytical Integrity
- **Artifact Resolution**: **Correct**. The TUI successfully discovers and resolves deep paths for both normal and review artifacts.
- **Provenance Display**: **Understandable**. The `[OK] LINKED` vs `[!!] STALE/UNLINKED` indicators provide immediate visual feedback on evidence integrity.
- **Stale Decision Warnings**: **Effective**. The hard-block on advancement previews when evidence is mismatched prevents the operator from making progress based on invalid assessments.

## 3. Usability & Ergonomics
- **Command Preview**: Clear and actionable. It accurately incorporates stronghold IDs and artifact paths, significantly reducing manual typing errors.
- **Plain Mode Utility**: Highly usable. Even without the Textual library, the line-based interactive menu (via the `l` key) provides a structured and efficient workflow for monitoring progress.
- **Recommendation Safety**: **High**. Recommendations are derived from deterministic state checks and prioritize remediation (review sessions) over advancement when gaps exist.

## 4. Safety Boundaries & Execution Policy

### preview-only candidates (Highest Risk)
The following actions should remain preview-only for the foreseeable future:
- **`learning-advance`**: Marking a task complete is a permanent strategic transition.
- **`learning-decision`**: Classifying progress requires human confirmation of the model's qualitative feedback.

### Safety-Execution Candidates (Future Phase)
The following actions could potentially be executed behind a confirmation dialogue:
- **`learning-run --dry-run`**: Purely informational/preparatory.
- **`learning-assess`**: Deterministic ingestion of existing artifacts.

### NEVER Auto-Execute
- **Cloud Escalation**: Any action sending data to frontier providers must remain manual and explicit.
- **Master Plan Promotion**: Overwriting `architect_plan.md` with cloud model responses.
- **Branch/Worktree Mutation**: Any action modifying project source code.

## 5. Remaining Gaps
- **Research Cockpit**: Still not implemented (planned for Phase 8.5+).
- **Interactive Selection**: No ability to select a specific stronghold if multiple learning strongholds exist (currently shows all in sequence).
- **Execution Bridge**: No "Press X to run this command" capability yet.

## 6. Current Readiness
The `fine-tuning-small-open-source-models` stronghold is accurately identified as requiring a **review session dry-run**. The TUI correctly suppressed advancement because the operator initiated a new session after a previous successful review, creating a "stale decision" state that correctly requires fresh evidence.

## Next Recommended Phase
**Phase 8.5: Learning Cockpit Safe Action Execution Design**. 
This phase should focus on designing the UI controls and safety confirmations for executing low-risk commands (like dry-runs and assessments) directly from the TUI.

## Conclusion
The Learning Cockpit is coherent, safe, and highly usable in its current read-only state. It provides a robust analytical layer that ensures the human operator maintains "Absolute Understanding" before proceeding with manual execution.
