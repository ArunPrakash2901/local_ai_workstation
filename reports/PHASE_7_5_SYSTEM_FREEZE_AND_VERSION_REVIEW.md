# Phase 7.5: System Freeze And Version Review

Date: 2026-05-18  
Status: Review only. This report defines the current freeze line; it does not implement new commands.

## Executive Summary

The Local AI Workstation has crossed the point where it should stop expanding by default. It now contains:

- a usable workstation control plane
- a complete generic Stronghold OS core
- a mature Learning Runner
- a partial Research Runner
- an older Feature Stronghold lane that remains useful but is not yet a complete execution product

The correct move now is not another new domain. The correct move is to freeze the present version map, declare the mature pieces complete for now, and make the next milestone narrow: finish reviewing the Research Runner before opening Product or Trading Research execution work.

## 1. Major Systems That Now Exist

1. **Workstation Control Plane**
   - readiness, models, task lifecycle, project registry, local build planning, cleanup/audit, packet and handoff utilities
2. **Feature Stronghold**
   - persistent feature contracts, local plans, validation, browser handoffs, local review, reporting, supervised run preflight
3. **Generic Stronghold OS**
   - domain-neutral strongholds with intake, contract formation, architect handoff, plan import, local checklist, reports, decision gates
4. **Learning Runner**
   - full human-in-the-loop tutoring lifecycle with session planning, tutoring, answer import, assessment, remediation, and advancement
5. **Research Runner**
   - early research workflow with dry-run review planning, local source notes, decision gating, and source registration
6. **Worktree And Agent Infrastructure**
   - worktree planning/review/sync support, bounded agent orchestration, agent hygiene, worktree-targeted dry-run packet support
7. **Handoff Layer**
   - local packets, clipboard copy/import, deterministic review, feature-aware and stronghold-aware browser reasoning lanes

## 2. Current Command Surface By Category

### Workstation

- `ws projects`
- `ws project`
- `ws ask`
- `ws global`
- `ws graph`
- `ws audit`
- `ws debug`
- `ws task`
- `ws build`
- `ws model`
- `ws models`
- `ws use`
- `ws warm`
- `ws unload`
- `ws kv`
- `ws kvuse`
- `ws daily`
- `ws moe`
- `ws ready`
- `ws status`
- `ws runs`
- `ws open-run`
- `ws aliases`
- `ws paths`
- `ws audit-workstation`
- `ws cleanup-plan`
- `ws cleanup-apply`
- `ws cleanup-status`
- `ws build-status`
- `ws build-runs`
- `ws open-build`
- `ws task-new`
- `ws task-split`
- `ws task-status`
- `ws task-next`
- `ws task-review`
- `ws task-complete`
- `ws task-block`

### Feature Stronghold

- `ws feature-new`
- `ws feature-plan`
- `ws feature-validate`
- `ws feature-handoff`
- `ws feature-report`
- `ws feature-status`
- `ws feature-local-review`
- `ws feature-architect-handoff`
- `ws feature-run`

### Generic Stronghold

- `ws stronghold-new`
- `ws stronghold-status`
- `ws stronghold-intake`
- `ws stronghold-intake-import`
- `ws stronghold-architect-handoff`
- `ws stronghold-plan-import`
- `ws stronghold-local-checklist`
- `ws stronghold-report`
- `ws stronghold-decision`

### Learning

- `ws learning-run`
- `ws learning-import-answers`
- `ws learning-assess`
- `ws learning-decision`
- `ws learning-review-session`
- `ws learning-advance`

### Research

- `ws research-run`
- `ws research-decision`
- `ws research-add-source`

### Worktree / Agent

- `ws apply-ready`
- `ws agent-run`
- `ws agent-run-worktree`
- `ws agent-status`
- `ws agent-canary`
- `ws agent-import`
- `ws agent-validate`
- `ws agent-hygiene`
- `ws agent-mark-stale-reviewed`
- `ws loop-plan`
- `ws loop-status`
- `ws loop-start`
- `ws worktree-plan`
- `ws worktree-create`
- `ws worktree-review`
- `ws worktree-sync`
- `ws worktree-status`

### Handoff

- `ws frontier`
- `ws packet`
- `ws redact`
- `ws escalate`
- `ws handoff-new`
- `ws handoff-copy`
- `ws handoff-import`
- `ws handoff-review`
- `ws handoff-status`

## 3. Stable Enough For Daily Use

### Stable daily workstation core

- readiness and status commands
- project registry lookups
- task lifecycle commands
- local-first `ws build --plan-only`
- audit/cleanup planning commands
- handoff packet lifecycle

### Stable cognitive-work core

- generic stronghold intake through decision/report flow
- Learning Runner lifecycle
- manual browser architect lane through handoffs

### Stable with bounded/manual use

- Feature Stronghold local evidence loop:
  - create
  - plan
  - validate
  - handoff
  - review
  - report
- worktree inspection and hygiene commands

## 4. Experimental

- `ws feature-run --dry-run` and later supervised apply preparation
- worktree-targeted agent adapter behavior beyond dry-run preparation
- early Research Runner:
  - useful
  - not yet milestone-reviewed as a complete lifecycle
- Graphify integration inside active stronghold loops
- stronghold behavior for `product`
- stronghold behavior for `trading-research`
- frontier escalation paths beyond manual, deliberate use

## 5. Should Not Be Used Yet

- any automatic browser automation path
- unattended `night-run`
- live worktree-targeted autonomous agent execution unless separately reviewed and enabled later
- Product Runner execution
- Trading Research Runner execution
- any path that implies live trading or capital deployment
- generic `stronghold-run` as a universal execution engine
- reserved frontier `review` / `stuck` commands

## 6. Runtime Folders That Must Remain Ignored

The following runtime or generated folders must stay out of Git:

- `runs/`
- `build_runs/`
- `archive/`
- `cleanup/`
- `frontier/responses/`
- `frontier/logs/`
- `frontier/packets/`
- `benchmarks/`
- `logs/`
- `scratch/`
- `graphify-out/`
- `runtimes/`
- `models/`
- `auto_runs/`
- `worktrees/`
- `handoffs/`
- `features/`
- `strongholds/`

Also keep generated readiness, hygiene, worktree, loop, and apply-ready reports ignored as already configured in `.gitignore`.

## 7. Current Version Map

| System | Version | Status |
| --- | --- | --- |
| Workstation Control Plane | `v1.0` | daily-use stable |
| Feature Stronghold | `v0.8` | stable local-evidence lane; supervised execution still incomplete |
| Generic Stronghold OS | `v1.0` | core lifecycle complete for now |
| Learning Runner | `v1.0` | complete enough for regular use |
| Research Runner | `v0.4` | early runner; functional but not yet freeze-ready |
| Product Runner | `v0.0` | not implemented |
| Trading Research Runner | `v0.0` | not implemented; research-only safety stance defined |

Versioning rule:

- `v1.0` means the current declared scope is coherent, useful, and can be used regularly without being a moving target.
- sub-`v1.0` means the system exists but is still under active design pressure.

## 8. Complete For Now

Declare these complete for the current freeze:

1. Workstation Control Plane baseline
2. Generic Stronghold OS core lifecycle
3. Learning Runner lifecycle
4. Handoff layer for local/browser-manual coordination
5. Existing task, readiness, hygiene, and inspection surfaces

## 9. Should Be Paused

Pause:

1. new domain runner creation
2. Product Runner work
3. Trading Research Runner work
4. browser automation work
5. generic execution abstraction work
6. additional Feature Stronghold expansion beyond bug fixes and targeted review

## 10. Next Single Bounded Milestone

**Next milestone: Phase 7.6 Research Runner milestone review and stabilization.**

Scope:

1. review the implemented research loop as one lifecycle
2. decide whether `research-run`, `research-add-source`, and `research-decision` are enough for a `v1.0` research baseline
3. identify at most one missing capability required before declaring Research Runner complete
4. do not start Product Runner or Trading Research Runner work until that review is complete

This is the smallest next step that reduces uncertainty instead of increasing surface area.

## 11. How Future Phases Avoid Endless Expansion

Use milestone discipline:

1. no new domain runner until the previous milestone has a review report
2. no implementation phase without an approved design phase
3. no cloud/provider run without a local state gate
4. no phase that mixes one new abstraction with one new domain
5. no new command family without declaring:
   - intended version
   - stop condition
   - evidence of completion
6. every 5 to 10 implementation phases, force a freeze/review report before adding more scope

## 12. Recommended Operating Rule

Adopt this as the workstation governance rule:

1. no new domain runner until the existing milestone is reviewed
2. no implementation without design
3. no cloud/provider run without local state gate
4. no trading execution
5. no runtime folders committed

## Validation Run

Requested validation performed on 2026-05-18:

- `ws ready`
  - passed
  - Ollama reachable
  - `hermes3:8b` loaded
  - Codex and Gemini detected
  - Claude not found
- `ws stronghold-status`
  - `research / agentic / CONTRACT_READY`
  - `learning / fine-tuning-small-open-source-models / LOCAL_CHECKLIST_READY`
  - `trading-research / quant-research-from-academic-papers / LOCAL_CHECKLIST_READY`
  - `product / local-ai-workstation-control-plane / INTAKE_IN_PROGRESS`
- `ws feature-status`
  - `stabilize-ws-command-documentation / VALIDATED_LOCAL`
- `ws handoff-status`
  - latest handoffs are `ARCHITECT_REVIEW_READY`
- `ws agent-hygiene`
  - current branch: `main`
  - unresolved `CODEX_RUNNING` folders: `0`
- `git status --short`
  - clean before this report was created
- `git diff --stat`
  - no tracked diff summary before this report was created

No command was implemented, no provider was invoked, no repo/worktree/stronghold was mutated, and no file outside this report was created or edited.
