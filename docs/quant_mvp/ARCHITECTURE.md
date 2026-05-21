# ARCHITECTURE: Quant Trading MVP

**Version:** 1.0.0  
**Status:** DRAFT

---

## 1. System Overview
The Quant Trading module follows a **Split-Brain Architecture**. It separates the "creative" and "reasoning" layer (AI) from the "calculating" and "enforcing" layer (Deterministic Software).

---

## 2. Split-Brain Architecture

### A. Generative Side (The "Thinker")
- **Components:** LLM Agents (Gemini/Codex), Markdown Specs, Research Notes.
- **Language:** Natural Language, Python (for drafting), Markdown.
- **Outputs:** Strategy Specs, Experiment Hypotheses, Result Interpretations.
- **Constraints:** No direct access to broker APIs or the live order bus.

### B. Deterministic Side (The "Enforcer")
- **Components:** DuckDB, Parquet, Python (Backtest Engine), YAML Contracts.
- **Language:** SQL, Type-Safe Python, YAML.
- **Outputs:** Backtest Metrics, Validated Orders, Risk Alerts, Audit Logs.
- **Constraints:** Must follow hard-coded policies; cannot be "talked into" bypassing a gate.

---

## 3. Proposed Folder Structure
```text
D:/_ai_brain/
├── docs/quant_mvp/             # PRD, Roadmap, Protocols, Runbooks
├── contracts/quant/            # YAML/MD definitions for strategies and data
├── data/quant/                 # Local Parquet/DuckDB storage (ignored by Git)
│   ├── raw/                    # Untouched source data
│   └── processed/              # Cleaned, standardized features
├── research/quant/             # AI-generated notes, hypothesis, and EDA
├── experiments/quant/          # Backtest results and historical run artifacts
├── reports/quant/              # AI-generated summaries and research reports
├── logs/quant/                 # Audit trails, execution logs, reconciliation
├── scripts/quant/              # [FUTURE] Backtest runners, data fetchers, risk checkers
└── tests/quant/                # [FUTURE] Unit and integration tests for quant logic
```

---

## 4. Data Flow
1. **Ingest:** Data fetcher pulls from source -> Validates against `data_contracts.yaml` -> Stores in `data/quant/raw/`.
2. **Process:** Transformer applies cleaning/normalization -> Stores in `data/quant/processed/`.
3. **Signal:** Strategy logic reads processed data -> Generates signals.
4. **Simulate:** Backtest engine reads signals + `risk_policy.yaml` -> Simulates trades -> Writes to `data/quant/backtests/`.
5. **Analyze:** AI reads backtest results + `strategy_spec.md` -> Writes `experiment_manifest.yaml`.

---

## 5. Strategy Lifecycle (Statuses)
1. **idea:** Concept in `research/quant/`.
2. **draft_spec:** YAML/MD spec in `contracts/quant/`.
3. **spec_review:** Human-gated review of the logic.
4. **approved_for_backtest:** Promotion to backtesting engine.
5. **backtested:** Results stored in `data/quant/backtests/`.
6. **validation_review:** Robustness and stress tests complete.
7. **approved_for_paper:** Promotion to real-time simulation.
8. **paper_active:** Live signals being generated in simulation.
9. **paper_retired:** Strategy stopped after review.

---

## 6. Audit & Logging Model
- **Experiment Manifests:** Every run must produce a manifest linking the code version (Git hash), data version (DVC/Hash), and result metrics.
- **Reconciliation Logs:** Daily check comparing intended paper positions vs. simulated broker fills.
- **Human Approval Log:** A Git-backed log of who approved what strategy promotion and when.

---

## 7. Safety Constraints
- **No Direct Execution:** The AI cannot call a `place_order()` function. It can only propose orders to a `risk_gateway`.
- **Price Collars:** All orders must be within N basis points of the last known price.
- **Kill-Switch:** A single file or command that prevents any further order proposals from being processed.
- **Mode Isolation:** Environment variables must strictly distinguish `RESEARCH`, `PAPER`, and `LIVE_BLOCKED`.
