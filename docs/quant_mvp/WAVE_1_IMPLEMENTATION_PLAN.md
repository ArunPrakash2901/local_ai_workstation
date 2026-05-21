# Wave 1 Implementation Plan: Quant Data Foundation

**Version:** 1.0.0  
**Status:** DRAFT  
**Lane:** Quant Trading  
**Parent Workstation:** `D:\_ai_brain`

---

## 1. Current Repository Evidence

### Command Surface
- The workstation uses a unified `ws` command dispatcher (`scripts/ws`).
- Commands are grouped by lane (e.g., `product-`, `learning-`, `feature-`).
- Subcommands typically map to specialized Bash or Python scripts in `scripts/`.
- [PROPOSED] Quant subcommands should follow the `ws quant <subcommand>` pattern.

### Script & Test Conventions
- Implementation logic lives in `scripts/`.
- Tests are often colocated in `scripts/` as `test_*.py` or use a custom `run_tests()` function to minimize dependencies.
- A virtual environment is available at `runtimes/workstation_venv/`.
- `PyYAML` is the standard for configuration handling.

### Safety & Validation
- `ws_apply_guard.sh` and `validate_ws_command_safety.py` enforce safety boundaries.
- The system prioritizes `dry-run` modes and explicit human confirmation before mutation.
- Path abstraction is managed via `registry/paths.yaml`.

---

## 2. Proposed Wave 1 Folder Layout
All paths are relative to the workstation root (`D:\_ai_brain`).

```text
├── contracts/quant/            # Existing: data_contracts.yaml, risk_policy.yaml
├── data/quant/
│   ├── raw/                    # Untouched OHLCV Parquet files
│   ├── clean/                  # Standardized, validated OHLCV
│   └── features/               # Derived features (signals/indicators)
├── experiments/quant/
│   ├── manifests/              # Versioned run metadata
│   └── results/                # Backtest execution artifacts
├── reports/quant/              # AI research and performance summaries
├── scripts/quant/              # Wave 1 Implementation Logic
├── tests/quant/                # Wave 1 Testing Suite
└── logs/quant/                 # Data ingestion and validation logs
```

---

## 3. Wave 1 Deliverables
The smallest safe set of components to establish a quantitative data foundation:

1.  **Contract Loader:** A Python module to read and parse `contracts/quant/data_contracts.yaml`.
2.  **OHLCV Schema Validator:** Ensures ingested data matches the column and type requirements defined in the contracts.
3.  **Local Storage Manager:** Standardizes the storage of Parquet files using DuckDB-compatible conventions.
4.  **Data Freshness Checker:** Implements the `freshness_policy` check from `data_contracts.yaml`.
5.  **Source Adapter Boundary:** A clean interface for data retrieval, initially targeting `yfinance` as a no-broker historical source.
6.  **Quant CLI Dispatcher:** A placeholder in `scripts/ws` to route `ws quant` commands.
7.  **Safety & Validation Tests:** Unit tests for schema enforcement and path safety.

---

## 4. Proposed Files for Wave 1
*Note: No code files will be created in this task.*

### Implementation (`scripts/quant/`)
- `scripts/quant/contracts.py`: Logic for loading and validating YAML contracts.
- `scripts/quant/schema.py`: Type and column validation for OHLCV datasets.
- `scripts/quant/freshness.py`: Freshness and continuity check logic.
- `scripts/quant/adapter_yfinance.py`: Low-friction historical data retrieval (Boundary only).
- `scripts/quant/storage.py`: Path and Parquet/DuckDB management.
- `scripts/quant/cli.py`: Python-side dispatcher for `ws quant`.

### Testing (`tests/quant/`)
- `tests/quant/test_contracts.py`: Verifies `data_contracts.yaml` parsing.
- `tests/quant/test_schema.py`: Tests the validator with good/bad OHLCV samples.
- `tests/quant/test_freshness.py`: Verifies time-gap detection logic.
- `tests/quant/test_safety.py`: Confirms no writes occur outside `data/quant/`.

---

## 5. Proposed `ws quant` Command Design ([PROPOSED/FUTURE])

| Command | Action | Default Mode |
|---|---|---|
| `ws quant data-validate` | Validate a local dataset against a contract. | `--dry-run` |
| `ws quant data-freshness` | Check for gaps or staleness in a dataset. | `--dry-run` |
| `ws quant data-ingest` | Fetch and validate data from a source. | `--dry-run` |
| `ws quant contract-check` | Verify `data_contracts.yaml` syntax and fields. | `N/A` |

---

## 6. Data Source Decision
- **Primary Recommendation:** `yfinance` (Yahoo Finance).
  - **Pros:** No API keys required, free historical OHLCV, wide ticker support (ETFs).
  - **Cons:** Not institutional grade, subject to rate limits.
  - **Role:** Perfect for Wave 1 local testing and schema validation.
- **Future Options:**
  - **Alpaca:** Preferred for US market data with a key (required for paper trading later).
  - **Stooq:** Good secondary for CSV-based historical data.
  - **IBKR:** Institutional path for Australian and Global markets.

**API Keys:** Marked as **[UNKNOWN]** for Wave 1.

---

## 7. Safety Constraints
- **Live Trading:** Strictly forbidden. No live code paths.
- **Broker Connectivity:** No active connections to broker order buses.
- **Order Generation:** No modules for creating or submitting trade orders.
- **Data Boundaries:** No writes outside of `data/quant/` and `experiments/quant/`.
- **Fail-Closed:** Scripts must exit with non-zero if contract fields are missing or data fails validation.
- **Transparency:** All external calls must be logged and visible in `logs/quant/`.

---

## 8. Acceptance Criteria
- [ ] `scripts/quant/contracts.py` successfully parses `contracts/quant/data_contracts.yaml`.
- [ ] Schema validator rejects data with missing columns (e.g., missing `close`).
- [ ] Freshness checker correctly identifies data older than the `max_lag_24h` policy.
- [ ] All tests in `tests/quant/` pass in the `runtimes/workstation_venv` environment.
- [ ] `ws quant` subcommands are registered and return help text.
- [ ] Zero broker-specific SDKs or credentials introduced in Wave 1.

---

## 9. Recommended Next Implementation Prompt
> **Next Prompt for Codex:**
> "Using the `WAVE_1_IMPLEMENTATION_PLAN.md`, implement the core Quant Data Foundation. Create `scripts/quant/contracts.py`, `scripts/quant/schema.py`, and `scripts/quant/storage.py` to handle the loading and validation of `contracts/quant/data_contracts.yaml`. Ensure all file paths are relative to `D:\_ai_brain`. Include a test suite in `tests/quant/test_foundation.py` that verifies schema rejection and contract parsing. Do not implement external API calls or broker connectivity yet. Integrate the subcommands into `scripts/ws` under the `quant` namespace as [PROPOSED] placeholders."
