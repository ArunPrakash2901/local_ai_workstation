# Write Approval Prep Runbook (Q48)

## 1. Purpose
This runbook explains how to prepare a draft Human Approval Form (HAF) and a hash evidence pack for future Quant research mutation. This is a preparation step only; write mode remains disabled.

## 2. Preparation Procedure
To prepare a draft approval for an idea intake, follow these steps:

1. **Perform a dry-run:** Run the standard dry-run command to preview the artifact.
   ```bash
   ws quant idea-intake-dry-run --title "My Idea" --source-type human_note --idea-file scratch/quant_ideas/my_idea.md
   ```

2. **Run the preparation tool:** Use the standalone preparation script to generate the draft HAF and evidence pack.
   ```powershell
   python scripts/quant/write_approval_prepare_cli.py prepare-idea-intake-approval `
     --title "My Idea" `
     --source-type human_note `
     --idea-file scratch/quant_ideas/my_idea.md `
     --write-draft
   ```

3. **Verify Draft Location:**
   - Draft approval file: `scratch/quant_approvals/HAF-DRAFT-XXXX.md`
   - Evidence pack: `scratch/quant_approvals/evidence/EVIDENCE-HAF-DRAFT-XXXX.json`

## 3. Storage and Structure
- **Draft Approvals:** Stored in `scratch/quant_approvals/`. They include YAML frontmatter and a human-readable markdown section.
- **Evidence Packs:** Stored in `scratch/quant_approvals/evidence/`. They contain JSON metadata including source hashes and safety flags.

## 4. Hash Integrity
The preparation tool computes the SHA256 of the input file. Any change to the input file after preparation will result in a hash mismatch, invalidating the draft during future human review or validator execution.

## 5. Reviewing the Draft
A human reviewer would inspect:
- The `source_input_hash` matches the current file state.
- The `safety_flags` are all `false`.
- The `intended_output_directory` is correct.
- The `forbidden_actions` are correctly listed.

## 6. Current Limitation: Write Mode Disabled
Even after preparation, executing a write-mode command is **not possible**. The `human_write_approval.py` validator will return a `BLOCKED` status because write mode has not been enabled in the workstation posture.

## 7. Safety Notice
- **No `ws` command grants approval.**
- **No `ws` command writes research idea artifacts.**
- **This tool only helps an operator prepare for a future human signature.**
