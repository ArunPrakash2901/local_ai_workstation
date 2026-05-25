# Standardised Prompt 2: Product Understanding to Phase Breakdown

Copy and paste the text below into ChatGPT or Gemini.

---

## Role
Act as a Solution Architect and Project Strategist.

## Objective
Turn the corrected **Product Understanding Brief** into a logical, phase-wise implementation breakdown.

## The Corrected Brief
{{PRODUCT_UNDERSTANDING_BRIEF}}

## Instructions
1. **Respect the Brief:** Do not reopen vague discovery unless there are major gaps. Do not invent missing requirements.
2. **Phase Decomposition:** Break the product into bounded, manageable implementation phases. Avoid huge, vague phases.
3. **Deep Research Identification:** Identify which phases require **Deep Research** (e.g., specific technology choices, complex data flows, or unknown API integrations).
4. **Mark Uncertainty:** Any uncertainty must be marked as **NEEDS_HUMAN_DECISION**.
5. **No Premature Code:** Avoid premature coding details or unnecessary tech stack recommendations unless essential for phase definition.
6. **Output Requirements:** Produce a product-level phase map, recommended order, and detailed summaries for each phase.

## Output Per Phase
- **Phase ID** (e.g., phase_01)
- **Phase Title**
- **Phase Objective**
- **Why This Phase Exists**
- **Scope**
- **Non-Goals**
- **Inputs Needed**
- **Expected Outputs**
- **Dependencies**
- **Human Decisions Required**
- **Risks**
- **Validation Strategy**
- **Acceptance Criteria**
- **Parallelisation Potential**
- **Suggested Branch Name** (e.g., work/feature-x/phase-01)
- **Does This Phase Need Deep Research?** [YES/NO]
- **Phase Summary for Prompt 3:** (A concise, self-contained summary of the phase for use in a Deep Research prompt).

## Final Structure
- **Product-Level Phase Map**
- **Recommended Phase Order**
- **Parallelisation Notes**
- **Phase Dependency Notes**
- **Detailed Phase Sections** (One per phase)
- **Phase Summaries for Prompt 3** (Consolidated list)

## Rules
- Do not produce research reports yet.
- Do not generate worker prompts.
- Do not produce CLI execution instructions.
- Focus purely on logical phase decomposition.
- Use British/Australian spelling.
