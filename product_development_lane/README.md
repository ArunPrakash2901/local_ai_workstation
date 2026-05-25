# Product Development Lane

Product Development Lane v0.1 is a non-executing planning lane.

It consumes approved Discovery Lane execution queue manifests and handoff bundles, then converts them into product-development artifacts:

- product packets
- PRD briefs
- wireframe briefs
- UI/UX briefs
- feature specs
- implementation planning packets

It does not build the product directly.

## Boundary

Product Development Lane starts only from Discovery Lane queue manifests with:

```text
queue_status: READY_FOR_EXECUTION_LANE
```

It must not consume vague ideas, raw Deep Research reports, discovery conversations, or unapproved phase packets. Discovery Lane handoff bundles are the contract of record.

## Non-Execution Rules

This lane does not:

- execute worker prompts
- create, checkout, push, merge, or delete branches
- call ChatGPT, Gemini, Codex, local models, browsers, APIs, or providers
- generate application source code
- reinterpret product requirements beyond the approved Discovery handoffs
- modify Discovery Lane artifacts

Missing requirements are written as `NEEDS_HUMAN_DECISION`. Missing UI or wireframe information is written as `NOT_SPECIFIED_IN_DISCOVERY_HANDOFF`.

## Current Commands

Python fallback:

```powershell
python product_development_lane\tools\build_product_packet.py --queue discovery_lane\execution_queues\positive_path_example_execution_queue.json --output product_development_lane
python product_development_lane\tools\audit_product_development_lane.py --root product_development_lane
```

Workstation bridge:

```bash
ws product-dev build-packet --queue discovery_lane/execution_queues/positive_path_example_execution_queue.json
ws product-dev review-html --manifest product_development_lane/manifests/positive_path_example_product_development_manifest.json
ws product-dev review-audit
ws product-dev audit
ws product-dev help
```

## Normal Flow

1. Discovery Lane reaches `READY_FOR_EXECUTION_LANE`.
2. Run the product packet adapter.
3. Build review HTML surfaces for the new manifest.
4. Review generated PRD, wireframe brief, UI/UX brief, feature spec, and implementation plan in VS Code or a browser using the generated HTML dashboard.
5. Use those artifacts later for Product Development Lane or UI/UX adapter work.
6. Keep execution separate.

## Human Review Artifacts (v0.2.1)

Product Development Lane v0.2.1 integrates static HTML review surfaces into the workstation CLI.

- **Markdown/JSON** remain the canonical source of truth (Bucket 1).
- **HTML** serves as a human review surface for inspection and judgment (Bucket 2).
- HTML surfaces are self-contained and read-only.

Review surfaces do **not**:
- Approve or reject artifacts (decisions are written back to Bucket 1).
- Execute worker prompts.
- Create or modify git branches.
- Commit, push, or merge code.

### Commands

Generate review artifacts:
```bash
ws product-dev review-html --manifest product_development_lane/manifests/<set_id>_product_development_manifest.json
```

Audit review artifacts:
```bash
ws product-dev review-audit
```

Python fallback:
```powershell
python product_development_lane\tools\build_review_html.py --manifest product_development_lane\manifests\<set_id>_product_development_manifest.json --output product_development_lane\review_artifacts
python product_development_lane\tools\audit_review_artifacts.py --root product_development_lane
```

## Planned Future Responsibilities

Future guarded slices may add:

- PRD brief review and approval
- wireframe brief review
- UI/UX brief review
- feature spec review
- implementation plan review
- product review packet generation
- acceptance checklist generation

Coding and execution remain future lane work.

