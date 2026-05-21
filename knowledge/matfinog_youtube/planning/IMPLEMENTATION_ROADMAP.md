# Implementation Roadmap

## Phase 0: Corpus and Planning Complete
- **Objective:** Finalize the ingestion and planning based on the MatFinOg corpus.
- **Deliverables:** Processed JSONL/CSV artifacts, PRD, and Planning documents.
- **Dependencies:** None.
- **Non-Goals:** Implementation of UI or tools.
- **Exit Criteria:** Milestone 3A planning report is accepted.

## Phase 1: Prompt Library and Workflow Browser
- **Objective:** Build a simple CLI or text-based interface to search and view the 366 research prompts and 7 workflows.
- **Deliverables:** `prompt_browser.py` script.
- **Dependencies:** Phase 0.
- **Non-Goals:** Executing the prompts with an LLM.
- **Exit Criteria:** User can query prompts by topic, workflow, and type.

## Phase 2: Research Notebook Generator
- **Objective:** Deterministically generate markdown or Jupyter notebook templates based on selected workflows.
- **Deliverables:** `notebook_generator.py` that outputs pre-filled templates with risk and validation checkpoints.
- **Dependencies:** Phase 1.
- **Non-Goals:** Auto-running the notebooks.
- **Exit Criteria:** Successfully generated template for `risk_first_strategy_review_workflow`.

## Phase 3: Paper Replication Workflow Scaffold
- **Objective:** Implement a specific wizard for the `research_paper_to_backtest_workflow`.
- **Deliverables:** Interactive CLI wizard that asks for paper details and outputs a rigorous testing plan.
- **Dependencies:** Phase 2.
- **Non-Goals:** Downloading or parsing PDFs automatically.
- **Exit Criteria:** Wizard enforces out-of-sample validation planning.

## Phase 4: Hypothesis-to-Validation Checklist
- **Objective:** Implement the `market_inefficiency_hypothesis_workflow` forcing functions.
- **Deliverables:** A tool that blocks progression until failure conditions and market structure reasons are documented.
- **Dependencies:** Phase 2.
- **Non-Goals:** Validating if the hypothesis is actually true.
- **Exit Criteria:** Generated checklists include mandatory risk sign-offs.

## Phase 5: Integration with Quant MVP Feature/Backtest Layers
- **Objective:** Connect the planning outputs to the local `docs\quant_mvp` backtesting structure.
- **Deliverables:** Scripts that export completed research plans into the `contracts\quant\` or `tasks\` directories for the backtester to pick up.
- **Dependencies:** Phase 4, existing Quant MVP infrastructure.
- **Non-Goals:** Broker integration.
- **Exit Criteria:** Seamless file handoff between workflow coach and backtesting environment.

## Phase 6: Optional RAG/Embedding Layer
- **Objective:** Allow semantic search over the transcribed videos.
- **Deliverables:** Local vector database integration.
- **Dependencies:** Phase 5, **Separate Security/Safety Approval**.
- **Non-Goals:** External API calls.
- **Exit Criteria:** Fully local RAG functioning for educational queries.

## Phase 7: Future UI Integration
- **Objective:** Move the workflow coach into a visual application (e.g., TUI or Web UI).
- **Deliverables:** UI components.
- **Dependencies:** Phase 5.
- **Non-Goals:** Live trading UI.
- **Exit Criteria:** Checklists and prompts are accessible via UI.

## Safety Notice
**No financial advice generated. No trading signals generated. No investment recommendations generated. No broker logic generated. No bot logic generated. No live trading automation generated.**
