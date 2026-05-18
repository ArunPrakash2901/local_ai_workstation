# Phase 5: Generic Stronghold Operating System Design

Date: 2026-05-18  
Status: Design only. No generic `stronghold-*` commands are implemented in this phase.

## Executive Summary

The workstation has proven the value of a persistent feature-level control point. The next architectural step is to generalize that pattern into a **Stronghold Operating System**: one common stateful shell for bounded work, with domain-specific overlays for software features, product development, learning, research, and trading research.

A Stronghold should not mean "software feature with a different label." It should mean:

- one durable objective
- one canonical contract
- one explicit state machine
- one evidence trail
- one controlled interface between human, local, browser, and CLI actors

The common kernel should stay small. Domain packs should add their own files, intake questions, validations, and execution lanes without breaking the shared safety model.

## 1. Generic Stronghold Abstraction

A **Stronghold** is a persistent, bounded workspace for one meaningful unit of work. It owns:

- objective
- constraints
- success criteria
- current plan
- state
- evidence
- actor interactions
- reports
- stop conditions

It is the generic case-file abstraction for work that may require repeated reasoning, execution, validation, and review. A Stronghold can represent:

- a feature to implement
- a product increment to shape
- a subject to learn
- a research question to investigate
- a trading idea to test without deploying capital

The workstation should treat every stronghold as a stateful object, not a loose folder of prompts.

## 2. Feature Stronghold As One Type

The current Feature Stronghold becomes the first concrete specialization of the generic abstraction:

- shared kernel:
  - contract
  - goals
  - constraints
  - success criteria
  - state
  - plan
  - evidence
  - logs
- feature overlay:
  - allowed files
  - repo/worktree state
  - validation plan
  - apply/run gates

Feature-specific commands can remain during migration, but conceptually they become typed wrappers around a generic stronghold engine rather than the whole system.

Recommended long-term storage model:

```text
D:\_ai_brain\strongholds\<type>\<namespace>\<stronghold_id_slug>\
```

Examples:

```text
D:\_ai_brain\strongholds\feature\workstation_control_plane\stabilize-ws-command-documentation\
D:\_ai_brain\strongholds\learning\ai-systems\distributed-systems-foundations\
D:\_ai_brain\strongholds\trading-research\equities\post-earnings-drift\
```

Compatibility note: existing `features/<project>/<feature>` folders should be adapted, not migrated blindly, until the generic engine is proven.

## 3. Initial Stronghold Types

| Type | Primary Use |
| --- | --- |
| `feature` | bounded software implementation work |
| `product` | product brief, roadmap, feature decomposition, release readiness |
| `learning` | human-in-the-loop skill acquisition and assessment |
| `research` | literature review, hypothesis development, evidence synthesis |
| `trading-research` | paper-to-hypothesis-to-backtest workflow with no live trading |

These five types are enough to prove that the abstraction is genuinely generic while still sharing substantial machinery.

## 4. Common Files Every Stronghold Should Own

| Path | Purpose |
| --- | --- |
| `contract.md` | scope, objective, non-goals, actor expectations |
| `goals.md` | concrete outcomes the loop should produce |
| `constraints.md` | safety limits, forbidden actions, resource boundaries |
| `success_criteria.md` | evidence required before completion |
| `state.json` | machine-readable state, timestamps, linked artifacts, blockers |
| `plan.md` | current authoritative plan |
| `loop_log.md` | append-only action journal |
| `evidence/` | validations, artifacts, check outputs, cited source bundles |
| `prompts/` | generated prompts for local/browser/CLI lanes |
| `responses/` | imported responses from actors |
| `reports/` | synthesized operator-facing reports |
| `runs/` | bounded execution attempts, study sessions, backtests, agent runs |

Recommended generic root discipline:

- only canonical files at the top level
- timestamped artifacts under subfolders
- no loose scratch files
- machine-readable references in `state.json`
- human-readable sequence in `loop_log.md`

## 5. Domain-Specific Files

### Learning

- `syllabus.md`
- `skill_map.md`
- `practice_log.md`
- `assessment.md`

### Product

- `product_brief.md`
- `roadmap.md`
- `feature_map.md`
- `release_report.md`

### Research

- `literature_map.md`
- `hypothesis_log.md`
- `evidence_matrix.md`
- `research_summary.md`

### Trading Research

- `paper_notes.md`
- `strategy_hypothesis.md`
- `backtest_plan.md`
- `risk_constraints.md`
- `paper_trading_report.md`

Feature strongholds keep their current overlay:

- `allowed_files.md`
- `validation_plan.md`
- repo/worktree metadata
- final feature report material

## 6. Intake Questions Before Creation

Every stronghold should first answer a common core:

1. What outcome are we trying to produce?
2. Why does this matter now?
3. What is explicitly out of scope?
4. What evidence would convince us the work is complete?
5. What resources may the system use?
6. What must never happen automatically?
7. What requires human approval?
8. What prior artifacts, repos, papers, or notes should be linked?

Domain-specific intake should then extend that core.

### Feature

- Which project/repo owns the work?
- What task or PRD is the source?
- Which files may change?
- Which files are explicitly denied?
- What commands prove success?
- Is a worktree required before mutation?

### Product

- Who is the user?
- What problem is being solved?
- What business or operator outcome matters?
- What release boundary defines success?
- Which candidate features are in or out?
- What dependencies or sequencing constraints already exist?

### Learning

- What skill should the human gain?
- What is the current baseline?
- What format of practice is preferred?
- How will retention and transfer be tested?
- What pace and time budget are realistic?
- What does mastery look like in observable terms?

### Research

- What question is being investigated?
- What would falsify the main hypothesis?
- Which source types are admissible?
- What date range or corpus matters?
- What uncertainty is acceptable?
- What final artifact is expected?

### Trading Research

- What paper or market observation motivates the idea?
- What is the signal hypothesis?
- What asset universe, horizon, and frequency apply?
- What transaction costs, slippage, and survivorship controls are required?
- What risk limits are mandatory?
- What would invalidate the idea before any paper trading?

## 7. Establishing "Absolute Understanding" Before Execution

Execution should not begin merely because a prompt exists. The system should require an **understanding gate**:

1. contract complete
2. constraints explicit
3. success criteria testable
4. unresolved questions listed and either answered or accepted
5. source artifacts linked
6. architect-level plan present for complex work
7. local model review completed against the plan
8. contradictions surfaced between contract, plan, and evidence
9. human review performed when the domain requires it

Recommended artifact:

```text
evidence/understanding_check_<timestamp>.md
```

That report should answer:

- what is known
- what remains uncertain
- what assumptions are being carried
- why execution is or is not allowed

For safety-critical domains, "absolute understanding" means explicit assumptions and bounded uncertainty, not false confidence.

## 8. Common State Machine

| State | Meaning |
| --- | --- |
| `CREATED` | skeleton exists |
| `INTAKE_IN_PROGRESS` | intake questions are being answered |
| `CONTRACT_READY` | contract, constraints, and success criteria are coherent |
| `ARCHITECT_REVIEW_READY` | packet is ready for senior reasoning review |
| `PLAN_IMPORTED` | authoritative architect plan has been imported |
| `LOCAL_REVIEW_READY` | local-model or deterministic review can run |
| `EXECUTION_READY` | all required gates for the domain have passed |
| `RUNNING` | a bounded execution/study/research attempt is active |
| `VALIDATING` | evidence is being checked against criteria |
| `NEEDS_HUMAN_REVIEW` | a human decision is required |
| `BLOCKED` | progress cannot continue safely |
| `COMPLETE` | success criteria are satisfied |

Recommended rule: stronghold state should be generic; run-specific sub-states should live in run artifacts, not explode the global state machine.

## 9. Actor Roles

| Actor | Role |
| --- | --- |
| WSL workstation | orchestration OS, filesystem authority, state machine, validation, logs, Git/worktree control |
| Browser ChatGPT/Gemini | senior architect lane for strategic reasoning and master plans |
| Local Ollama models | intern lane for decomposition, checklisting, contradiction finding, summarization, local review |
| Codex CLI | bounded implementation worker for code mutation once allowed |
| Gemini CLI | bounded synthesis/research/execution worker where suitable |
| Graphify | context graph layer connecting repos, files, tasks, plans, evidence, and domain artifacts |
| Human operator | approver, teacher/learner, capital owner, final arbiter for ambiguity and risk |

## 10. Graphify As Context Graph Layer

Graphify should become a reusable **context layer**, not just a codebase lookup tool.

Recommended integration:

1. continue project graphs for code structure
2. add stronghold artifact indexing:
   - contracts
   - goals
   - plans
   - reports
   - evidence
   - linked papers or datasets by reference
3. generate compact context packs from graph queries before local or browser reasoning
4. store graph query results as evidence, not ephemeral shell output
5. keep raw datasets, secrets, and oversized artifacts out of the graph

Important constraint:

- do not run `graphify update` on every trivial state transition
- update or refresh graph context on meaningful artifact changes:
  - stronghold creation
  - contract update
  - plan import
  - new validated evidence
  - major code/worktree drift

That gives Graphify a useful role in active loops without turning every state change into background churn.

## 11. Local Models As Interns After Architect Planning

Once a senior architect plan exists, local models should be used for bounded support work:

- decompose a master plan into concrete tasks
- produce checklists
- compare plan against contract and constraints
- summarize failures
- identify missing evidence
- suggest targeted clarifying questions
- rank what context should be sent to a stronger model

They should not silently replace the architect plan, authorize risky execution, or widen scope. Their outputs should be advisory artifacts that either:

- confirm readiness
- identify gaps
- recommend escalation

## 12. Browser Models As Architects Without Becoming Brittle Dependencies

Browser models should stay a **manual reasoning lane**:

- packet generated locally
- prompt copied manually
- response imported manually
- transcript preserved locally
- state transitions depend on imported evidence, not browser automation

This preserves the value of strong reasoning without making Chrome control, DOM stability, login state, quota, or provider UX part of the safety-critical path.

Optional browser automation can remain experimental later, but the stronghold model must work fully when the browser lane is manual.

## 13. Product Development Loops vs Learning Loops

### Product Development

- human role:
  - review contracts
  - approve plans
  - review reports and shipped outcomes
- workstation role:
  - coordinate plan, execution, validation, handoffs
  - use worktrees and bounded CLI workers
- success evidence:
  - roadmap progress
  - feature completion
  - release readiness
  - validation outputs

### Learning

- human role:
  - actively practice
  - answer questions
  - produce work
  - demonstrate retention
- workstation role:
  - curate syllabus
  - adapt practice
  - assess gaps
  - log progress
- success evidence:
  - completed practice
  - assessment performance
  - demonstrated transfer
  - human reflection

Product loops optimize delegated execution. Learning loops optimize human capability growth. Treating them the same would fail both.

## 14. Trading Research Safety Gates

Trading-research strongholds must be research-only by default.

Required gates:

1. literature or paper basis recorded
2. hypothesis stated before testing
3. backtest plan approved before running
4. data provenance recorded
5. lookahead, survivorship, leakage, and transaction-cost checks explicit
6. risk constraints written before results are interpreted
7. paper-trading evidence separated from historical backtest evidence
8. no path from research output to live capital deployment
9. human review required before any future real-world use

Allowed early outputs:

- hypothesis notes
- backtest plans
- historical backtest reports
- paper trading reports
- rejection reports

Disallowed:

- broker login use
- order submission
- capital allocation
- automatic portfolio changes

## 15. What Must Never Be Automated Initially

- live trading
- capital deployment
- destructive file deletion
- secret access
- unbounded cloud calls
- unattended night-run execution

Additional practical exclusions:

- blind browser automation as a required path
- implicit widening of repo or dataset access
- automatic override after failed validation

## 16. Generic Command Surface

Recommended long-term commands:

```bash
ws stronghold-new
ws stronghold-status
ws stronghold-intake
ws stronghold-plan
ws stronghold-architect-handoff
ws stronghold-import
ws stronghold-local-review
ws stronghold-run
ws stronghold-report
```

Suggested responsibilities:

| Command | Responsibility |
| --- | --- |
| `stronghold-new` | create skeleton, choose type, initialize state |
| `stronghold-status` | list state, blockers, latest artifacts |
| `stronghold-intake` | capture common and domain-specific intake answers |
| `stronghold-plan` | build/update domain plan from local evidence |
| `stronghold-architect-handoff` | create browser-ready senior architect packet |
| `stronghold-import` | import external/local responses into the stronghold |
| `stronghold-local-review` | run local deterministic or Ollama review |
| `stronghold-run` | coordinate bounded domain execution |
| `stronghold-report` | synthesize current/final report |

## 17. Mapping Existing `feature-*` Commands

| Existing Feature Command | Generic Equivalent |
| --- | --- |
| `feature-new` | `stronghold-new --type feature` |
| `feature-status` | `stronghold-status --type feature` |
| `feature-plan` | `stronghold-plan` |
| `feature-handoff` | `stronghold-architect-handoff` or typed `stronghold-handoff` |
| `feature-import` / handoff import path | `stronghold-import` |
| `feature-local-review` | `stronghold-local-review` |
| `feature-run` | `stronghold-run --type feature` |
| `feature-report` | `stronghold-report` |

Migration principle:

- keep feature commands working
- implement generic commands underneath or beside them
- avoid breaking the existing proven feature loop while learning what is truly common

## 18. Recommended Next MVP

Design now, implement later:

```bash
ws stronghold-new --type learning|product|feature|research|trading-research --title "<title>"
```

First MVP behavior:

1. create the generic folder structure
2. initialize common files
3. create the type-specific overlay files
4. record unanswered intake questions
5. initialize `state.json` as `CREATED` or `INTAKE_IN_PROGRESS`
6. write the first loop-log event
7. do not execute, hand off, invoke providers, mutate repos, or touch trading systems

This is the correct first slice because it tests whether the generic skeleton is real before the workstation starts generalizing planning and execution behavior.

## Validation Run

Requested validation performed on 2026-05-18:

- `ws ready`
  - passed
  - Ollama responding
  - `hermes3:8b` loaded
  - Codex and Gemini detected
  - Claude not found
- `ws feature-status`
  - current feature stronghold: `stabilize-ws-command-documentation`
  - state: `VALIDATED_LOCAL`
- `ws handoff-status`
  - latest handoff: `ARCHITECT_REVIEW_READY`
- `ws agent-hygiene`
  - current branch: `main`
  - unresolved `CODEX_RUNNING` folders: `0`
- `git status --short`
  - pre-existing untracked draft:
    - `reports/PHASE_5_GENERIC_STRONGHOLD_OPERATING_SYSTEM_DESIGN.md`
- `git diff --stat`
  - no tracked diff summary before this report rewrite

No generic stronghold command was implemented, no provider was invoked, no repository or worktree was mutated, and no file outside the requested design report was changed.
