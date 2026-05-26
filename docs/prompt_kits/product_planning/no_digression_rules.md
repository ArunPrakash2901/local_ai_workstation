# No-Digression Rules

This document defines the standing rules that constrain all product planning prompts in this kit. These rules can be embedded in or appended to any prompt where digression is a risk.

---

## Full Rule Set

The model must not do any of the following:

### Scope Violations
- Broaden the scope of the product beyond what the operator has defined.
- Add features that have not been explicitly discussed or agreed.
- Create new phases without operator direction. If a missing phase is a blocker, flag it under `NEEDS_HUMAN_DECISION` — do not create it silently.
- Implement anything outside the current phase boundary.

### Premature Decisions
- Suggest a technology stack before functional requirements are clear.
- Recommend infrastructure or architecture before product behaviour is understood.
- Jump to implementation before planning is stable.

### Generic and Off-Topic Output
- Write generic AI trend commentary unrelated to the product.
- Produce broad market analysis unless it is directly required for a specific deliverable.
- Give motivational writing, productivity advice, or startup platitudes.
- Compare frameworks or tools without being asked.
- Recommend adjacent products or services unprompted.

### Dishonest or Evasive Output
- Hide uncertainty. All uncertain points must be explicitly flagged using `ASSUMPTION`.
- Omit unresolved decisions. All pending operator decisions must be flagged under `NEEDS_HUMAN_DECISION`.
- Skip `Non-Goals` or `OUT_OF_SCOPE` sections.
- Skip `Validation / Test Strategy` or `Acceptance Criteria` sections.
- Use vague "best practices" language that does not apply concretely to the current product and phase.

### Autonomy Violations
- Recommend autonomous agent behaviour unless it is explicitly in scope.
- Make design decisions without surfacing them to the operator first.
- Produce irreversible structural changes to the product definition without flagging them.

### Length and Compression Violations
- Compress phase context files to the point of vagueness in order to fit within a single response.
- Omit sections to save space. Sections may be brief but must be present.

---

## Compact Copy-Ready Block

Use this block when adding no-digression constraints directly into a prompt:

```
NO-DIGRESSION RULES (apply strictly):
- Do not broaden product scope or add features beyond what is defined.
- Do not create new phases without operator direction.
- Do not suggest a tech stack before functional requirements are stable.
- Do not write generic AI trend commentary or market analysis.
- Do not write motivational content, startup advice, or productivity tips.
- Do not recommend autonomous behaviour unless explicitly in scope.
- Do not hide uncertainty — flag all inferred points as ASSUMPTION.
- Do not omit NEEDS_HUMAN_DECISION, OUT_OF_SCOPE, Non-Goals, or Validation sections.
- Do not implement anything outside the current phase.
- Do not compress phase context to the point of vagueness.
```

---

## Flags Reference

Use these flags consistently throughout all planning and research documents:

| Flag | Meaning | When to Use |
|---|---|---|
| `ASSUMPTION` | Inferred but not confirmed by the operator. | When the model has made a reasonable inference that has not been explicitly validated. |
| `NEEDS_HUMAN_DECISION` | Requires operator input before proceeding. | When a decision is genuinely open and cannot be resolved without the operator. |
| `OUT_OF_SCOPE` | Excluded from this phase. May be relevant to a later phase. | When an idea, feature, or concern is valid but not part of the current phase boundary. |

These flags are not optional. If any section contains assumptions or open decisions, the flags must be present.
