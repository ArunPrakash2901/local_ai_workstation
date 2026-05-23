# Quant Research Workflow Roadmap

This roadmap integrates the data foundation and execution phases of the original Quant MVP with the rigorous research workflows synthesized from the MatFinOg corpus.

---

## Phase 0: Completed Planning/Safety Baseline
- **Objective:** Establish the governance, architecture, and safety contracts.
- **Deliverables:** PRD, Architecture, Workflow, Protocols, and Baseline YAML Templates.
- **Dependencies:** None.
- **Non-Goals:** Implementation.
- **Exit Criteria:** Core planning documents reviewed and approved.

## Phase 1: Completed Data Foundation
- **Objective:** Build the local data layer and ingestion pipeline.
- **Deliverables:** `data_contracts.yaml`, local data fetcher (Parquet/DuckDB).
- **Dependencies:** Upstream data sources.
- **Non-Goals:** Real-time data.
- **Exit Criteria:** Successful deterministic data ingestion to local storage.

## Phase 2: Completed/Ongoing Feature Foundation
- **Objective:** Establish feature calculation capabilities.
- **Deliverables:** `feature_contracts.yaml`, DuckDB feature builders.
- **Dependencies:** Phase 1.
- **Non-Goals:** Strategy logic.
- **Exit Criteria:** Standardized technical features generated reproducibly.

## Phase 3: Research Idea Intake and Hypothesis Builder
- **Objective:** Implement the `market_inefficiency_hypothesis_workflow`.
- **Deliverables:** `hypothesis_contract_schema.yaml`, idea intake CLI/TUI flow, human review gating for hypotheses.
- **Dependencies:** MatFinOg Corpus Synthesis.
- **Non-Goals:** Backtesting.
- **Exit Criteria:** A user can successfully draft and approve a hypothesis contract.

## Phase 4: Research Paper Replication Scaffold
- **Objective:** Implement the `research_paper_to_backtest_workflow`.
- **Deliverables:** Paper extraction templates, replication plan markdown generator.
- **Dependencies:** Phase 3.
- **Non-Goals:** Automated paper reading (LLM OCR is out of scope; focus is on structuring user inputs).
- **Exit Criteria:** A valid out-of-sample replication plan can be generated and approved.

## Phase 5: Strategy Specification Generator (Human Reviewed)
- **Objective:** Bridge the hypothesis/research into a formal strategy contract.
- **Deliverables:** Enhanced `strategy_spec_template.md`, AI specification drafting tool.
- **Dependencies:** Phase 3 & 4.
- **Non-Goals:** Code generation.
- **Exit Criteria:** A completed, human-approved strategy specification is ready for backtesting.

## Phase 6: Backtest Integration (Deterministic Only)
- **Objective:** Connect the approved specification to the backtest engine.
- **Deliverables:** Event-driven backtesting execution based on the specification.
- **Dependencies:** Phase 1, 2, 5.
- **Non-Goals:** Optimization/Curve-fitting.
- **Exit Criteria:** Reproducible backtest results based strictly on the specification.

## Phase 7: Risk-First Validation and Robustness Gates
- **Objective:** Implement `risk_first_strategy_review_workflow` and `execution_microstructure_review_workflow`.
- **Deliverables:** Mandatory risk checklist enforcement, microstructure parameter sensitivity testing.
- **Dependencies:** Phase 6.
- **Non-Goals:** Overriding human risk parameters.
- **Exit Criteria:** Strategies cannot advance without human sign-off on risk and microstructure sensitivity.

## Phase 8: Paper Trading Simulation (Future Only)
- **Objective:** Simulate execution of validated strategies.
- **Deliverables:** Paper trading engine, real-time simulated order book, daily reconciliation.
- **Dependencies:** Phase 7.
- **Non-Goals:** Live capital deployment.
- **Exit Criteria:** System accurately tracks simulated PnL against a risk policy.

## Phase 9: Live-Readiness Review (Outside MVP)
- **Objective:** Audit system for eventual live capital deployment.
- **Deliverables:** Gap analysis report, slippage/latency modeling.
- **Dependencies:** Phase 8.
- **Non-Goals:** Actual live trading.
- **Exit Criteria:** Comprehensive readiness review completed.