# Approval Review Plan: examples

This review plan is advisory only. It does not approve packets, create handoffs, create branch plans, execute worker prompts, create branches, commit, push, or merge.

## Research Set ID

examples

## Ingest Manifest

`research_set_ingests/examples_ingest_manifest.json`

## Ingest Status

INGESTED

## Summary

- Total Packets: 1
- Ready For Approval: 1
- Needs Human Decision: 0
- Not Execution Ready: 0
- Unknown Status: 0
- Already Approved: 0
- Already Handed Off: 0
- Missing Worker Prompt: 0
- Missing Phase Manifest: 0

## Recommended Next Action

Review listed packet and worker prompt files in VS Code, then approve phases individually.

## Packet Review Table

| Phase | Packet | Worker Prompt | Phase Manifest | Validation Status | Approval Status | Handoff Status | Recommended Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| phase_01 - Foundation Intake | `phase_packets/examples__phase_01_foundation_packet.md` | `worker_prompts/examples__phase_01_foundation_worker_prompt.md` | `manifests/examples__phase_01_foundation_manifest.json` | READY_FOR_HUMAN_REVIEW | PENDING_HUMAN_REVIEW | NOT_CREATED | Open packet and worker prompt in VS Code, then approve this packet individually if acceptable. |

## VS Code Review Paths

- packet: `phase_packets/examples__phase_01_foundation_packet.md`
- worker_prompt: `worker_prompts/examples__phase_01_foundation_worker_prompt.md`
- phase_manifest: `manifests/examples__phase_01_foundation_manifest.json`

## Approval Boundary

- This report is not an approval record.
- Individual packet approval remains the human gate.
- Use `ws discovery approve <phase_or_packet_id>` only after VS Code review.
- Batch approval is intentionally not implemented.
