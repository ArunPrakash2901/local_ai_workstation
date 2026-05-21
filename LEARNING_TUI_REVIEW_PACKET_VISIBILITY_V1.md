# Learning TUI Review Packet Visibility v1

## Purpose
This document (Phase 11) defines the implementation of read-only advancement review packet visibility within the Learning Cockpit / TUI. This ensures that operators can easily browse the contents of the latest decision-support packets without leaving the dashboard, strictly maintaining the manual advancement boundary.

## TUI Displays
The Learning Cockpit now includes an **ADVANCEMENT REVIEW PACKET** section that displays:
- **Packet ID**: The unique identifier for the latest packet (e.g., `ADV-PACKET-20260521T143413Z`).
- **Timestamp**: When the packet was generated.
- **Status**: The readiness status recorded in the packet.
- **Score**: The readiness score recorded in the packet.
- **Pointer/Sync**: Key alignment data from the time of packet creation.
- **Checks**: Count of required human verification steps and a summary of the first check.
- **Filename**: The actual markdown file name under `review_packets/`.

## Discovery & Extraction
The TUI includes a read-only discovery helper that:
1.  Scans `strongholds/learning/<stronghold_id>/review_packets/`.
2.  Identifies the latest `.md` file by modification time.
3.  Performs regex-based extraction of key fields (ID, status, checks) without using an external parser.
4.  Enforces a 100KB file size limit to prevent TUI lag.

## Safety Boundaries
- **Read-Only**: The TUI only reads existing markdown files; it never creates packets or modifies state based on packet content.
- **Hard Guard**: The TUI's internal command runner has been extended to block `--create-packet`, ensuring that persistent documentation records are only created via explicit CLI commands.
- **Manual Boundary**: The TUI explicitly states:
    - `Review packet is advisory.`
    - `Advancement remains manual.`
    - `TUI packet visibility is read-only.`

## Live Status Snapshot (`fine-tuning-small-open-source-models`)
As of Phase 11:
- **Latest Packet**: `20260521T143413Z_advancement_review_packet.md`
- **Packet ID**: `ADV-PACKET-20260521T143413Z`
- **Readiness**: `ready_for_human_review` (Score: 50/100)
- **State Integrity**: `state.json` remains untouched (mtime 2026-05-21 12:43 PM).

## Validation Results
- **Discovery Logic**: PASS (Verified regex extraction against sample content).
- **Hard Guard**: PASS (Verified `--create-packet` is blocked).
- **UI Integration**: PASS (Section added to cockpit display with advisory warnings).
- **No Mutation**: PASS (Confirmed no state files were modified during implementation).

## Known Limitations
- Displays only the latest packet; archival browsing is not yet implemented.
- Required human checks are displayed as a summary, not as interactive check-boxes.

## Next Recommended Task
- **Phase 12**: Implement TUI interactive checklist for review packets (requires a new TUI-local state layer).
