# Product Lane First Real Smoke Test Plan

Date: 2026-05-21  
Project root: `D:\_ai_brain`  
Execution mode: manual operator run only (plan document; do not auto-run).

## 1. Smoke Test Target

- Product type: `website`
- Product label/title: `Portfolio Website Redesign`
- Expected product id (slug): `portfolio-website-redesign`

Low-risk objective: validate the end-to-end Phase 1 workflow from product creation to immutable scope lock, with explicit checkpoints at each guarded write step.

## 2. Preconditions

Before running the smoke test:

- Run safe no-write validation:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python scripts\check_local_safety.py
```

- From Windows PowerShell, invoke Product Lane commands through WSL Bash:

```powershell
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-new --type website --title "Portfolio Website Redesign" --dry-run'
```

- Do not run `scripts/ws` with Python. `scripts/ws` is a Bash dispatcher.
- Do not use sensitive real personal or client data in answers.
- Do not run unrelated `ws` mutation commands in parallel.

## 3. Exact Command Sequence (Do Not Execute In This Document)

### 3.1 Preview product creation

```bash
./scripts/ws product-new --type website --title "Portfolio Website Redesign" --id portfolio-website-redesign --dry-run
```

Expected:

- No files written.
- Preview shows target path under `products/portfolio-website-redesign/`.
- State not created yet.

### 3.2 Create product

```bash
./scripts/ws product-new --type website --title "Portfolio Website Redesign" --id portfolio-website-redesign --confirm
```

Expected:

- Files created:
  - `products/portfolio-website-redesign/product.yaml`
  - `products/portfolio-website-redesign/action_log.md`
- Product state in `product.yaml`: `INBOX`

Checkpoint A (manual inspect):

- Open `product.yaml` and verify:
  - `product_type: website`
  - `state: INBOX`
  - `private` value as expected

### 3.3 Preview intake

```bash
./scripts/ws product-intake --product portfolio-website-redesign --dry-run
```

Expected:

- No files written.
- Preview indicates future artifact writes only.
- State remains `INBOX`.

### 3.4 Start intake

```bash
./scripts/ws product-intake --product portfolio-website-redesign --confirm
```

Expected:

- Files created:
  - `products/portfolio-website-redesign/intake.md`
  - `products/portfolio-website-redesign/questions.md`
- `product.yaml` updated:
  - `state: INTAKE_STARTED`
  - `intake_started_at` set
  - `open_questions` populated

Checkpoint B (manual inspect):

- Confirm both template files exist and are readable.
- Confirm `product.yaml` transitioned to `INTAKE_STARTED`.

### 3.5 Create answers file manually

Create a temporary local answers file (example: `D:\_ai_brain\scratch\portfolio_answers.txt`) using format:

`question_id: answer text`

Website minimum set to reach `SCOPE_READY` should include required + blocking + privacy ids:

```text
website.goal: Refresh the portfolio site to improve clarity and conversion for consulting inquiries.
website.audience: Hiring managers, startup founders, and technical collaborators.
website.primary_pages: Home, About, Work, Services, Contact.
website.conversion: Submit a contact request for a discovery call.
website.content_sources: Existing resume bullets, case-study notes, and selected project summaries.
website.success_criteria: At least one qualified inquiry per week and clear project narrative on all core pages.
website.blocking_content: No blocker; required page copy draft is available.
website.blocking_assets: No blocker; logo and profile imagery are available.
website.blocking_approval: No external approval required for v1 launch.
website.privacy_sensitive_content: No personal/private client-confidential details will be published.
website.privacy_handoff_exclusions: Exclude any client names not already public.
```

### 3.6 Import answers

```bash
./scripts/ws product-answer-import --product portfolio-website-redesign --file /mnt/d/_ai_brain/scratch/portfolio_answers.txt --confirm
```

Expected:

- `products/portfolio-website-redesign/answers.md` created.
- `product.yaml` updated:
  - `state: SCOPE_READY` (if all required/blocking/privacy answered)
  - `open_questions: []`
  - `intake_completed_at` and `scope_ready_at` set

Checkpoint C (manual inspect):

- Confirm `answers.md` exists and includes imported answers.
- Confirm `product.yaml` state is `SCOPE_READY`.
- If state is `CLARIFICATION_NEEDED`, stop and fix unresolved answers before continuing.

### 3.7 Preview scope

```bash
./scripts/ws product-scope --product portfolio-website-redesign --dry-run
```

Expected:

- No files written.
- Deterministic scope preview printed.
- State remains `SCOPE_READY`.

Checkpoint D (manual inspect):

- Review scope preview output for obvious TODO/UNKNOWN sections.
- If scope is unclear, update answers and re-import before lock.

### 3.8 Lock scope

```bash
./scripts/ws product-lock-scope --product portfolio-website-redesign --confirm
```

Expected:

- `products/portfolio-website-redesign/scope_lock.md` created.
- `product.yaml` updated:
  - `state: SCOPE_LOCKED`
  - `scope_locked_at` set
  - `scope_lock_hash` set
  - `open_questions: []`
- Re-running lock should refuse overwrite.

Checkpoint E (manual inspect):

- Confirm `scope_lock.md` exists and includes operator confirmation statement.
- Confirm hash exists in `product.yaml`.

### 3.9 Verify status

```bash
ws product-status portfolio-website-redesign
```

Expected:

- Record shows `state: SCOPE_LOCKED` and scope lock metadata.

### 3.10 Verify list

```bash
ws product-list
```

Expected:

- Product appears in list with `SCOPE_LOCKED` state.

## 4. Expected Artifact Timeline

| Step | Expected new/updated artifacts |
|---|---|
| product-new --confirm | `product.yaml`, `action_log.md` |
| product-intake --confirm | `intake.md`, `questions.md`, `product.yaml` update (+ action log append if present) |
| product-answer-import --confirm | `answers.md`, `product.yaml` update (+ action log append if present) |
| product-scope --dry-run | No file writes |
| product-lock-scope --confirm | `scope_lock.md`, `product.yaml` update (+ action log append if present) |

## 5. Expected State Progression

`INBOX -> INTAKE_STARTED -> SCOPE_READY -> SCOPE_LOCKED`

If answers are incomplete, expected intermediate branch:

`INTAKE_STARTED -> CLARIFICATION_NEEDED -> SCOPE_READY`

## 6. Safety Posture Expectations During Smoke Test

- No model calls.
- No provider/cloud calls.
- No agent execution.
- No browser automation.
- Writes bounded to `products/portfolio-website-redesign/`.
- Scope lock is immutable once created.

## 7. Rollback/Cleanup Plan (Manual)

If smoke test must be reverted:

1. Stop at a checkpoint and capture current state with:
   - `ws product-status portfolio-website-redesign`
2. Prefer archive over destructive delete:
   - move `products/portfolio-website-redesign/` to a timestamped archive folder under `archive/` or `scratch/`.
3. Do not partially edit or delete single artifacts (`answers.md`, `scope_lock.md`, etc.) to force state changes.
4. If lock was created and scope must change, do not edit `scope_lock.md` directly; record a follow-up change task for a future scope-change flow.

## 8. What Not To Do

- Do not run this smoke test against real sensitive personal/client data.
- Do not skip dry-run steps before guarded writes.
- Do not execute `ws ready` as a substitute for this workflow.
- Do not manually edit `scope_lock.md` after lock.
- Do not run parallel Product Lane writes on the same `product_id`.

## 9. Smoke Test Exit Criteria

Smoke test is successful if:

- All commands run with expected safety posture.
- Final state is `SCOPE_LOCKED`.
- Expected artifacts exist and are internally consistent.
- No writes occurred outside `products/portfolio-website-redesign/`.
- No model/provider/agent/browser workflows were invoked.
