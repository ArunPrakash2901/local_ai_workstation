# HTML Review Surface Contract

Every generated HTML review surface in Product Development Lane must adhere to this structural contract.

## Required Header Information

- **Source Artifact Path:** Relative path to the canonical Markdown/JSON file.
- **Source Artifact Checksum (SHA-256):** Integrity check for the source.
- **Generated Timestamp:** When the HTML was projected.
- **Review Purpose:** E.g., "Human inspection of Product Requirement Document."
- **Canonical Source Warning:** High-visibility banner stating that Markdown is the source of truth.

## Required Content Sections

1. **Summary:** High-level overview of the artifact.
2. **Key Decisions:** Explicitly highlighted decisions made by the generator.
3. **Risks:** Detected risks or edge cases.
4. **Open Questions:** `NEEDS_HUMAN_DECISION` or `TODO` items.
5. **Acceptance Criteria:** Measurable criteria for success.

## Human Review Checklist (Static)

A standard checklist included in every review surface to guide the operator:
- [ ] Scope matches intent
- [ ] Non-goals are clear
- [ ] UI/UX expectations are clear
- [ ] Risks are visible
- [ ] Open decisions are surfaced
- [ ] Ready for next lane

## Safety Claims

The footer of every HTML page must explicitly state:
- No execution of worker prompts occurred.
- No branches were created, checked out, or modified.
- No commit, push, or merge actions were performed.
- This is a static projection only.

## Technical Constraints

- **Self-Contained:** CSS must be embedded in `<style>` tags.
- **No External JS:** No script tags allowed unless they are inline and purely for UI (e.g., toggling sections).
- **No CDN:** No external fonts, icons, or libraries.
- **Safe Rendering:** Content from source Markdown must be HTML-escaped to prevent XSS.
