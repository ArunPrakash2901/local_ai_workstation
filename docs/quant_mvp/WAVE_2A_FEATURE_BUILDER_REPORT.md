# Wave 2A Report: Feature Contract & Deterministic Feature Builder

**Version:** 1.0.0  
**Status:** COMPLETE  
**Date:** 2026-05-21

---

## 1. Summary of Implementation
Wave 2A introduces a formal feature-building layer to the Quant MVP. This phase provides a deterministic pipeline for calculating neutral research features from validated OHLCV datasets. The implementation follows a strict "no-lookahead" and "no-signal" policy, ensuring that the feature builder remains a research tool rather than a strategy engine.

---

## 2. Files Created
- `contracts/quant/feature_contracts.yaml`: Defines the schema, allowed windows, and safety mandates for feature generation.
- `scripts/quant/features.py`: Implementation of deterministic feature builders (Returns, SMA, Volatility) using local Pandas.
- `tests/quant/test_features.py`: Unit tests for calculation accuracy, contract enforcement, and non-mutation of input data.

---

## 3. Files Modified
- `scripts/quant/cli.py`: Added `feature-contract-check` and `feature-build` subcommands.
- `scripts/ws`: Integrated new commands into the workstation dispatcher help and routing.
- `registry/ws_command_safety.yaml`: Registered new commands and cleaned up legacy duplicates.
- `WS_COMMAND_SAFETY_MATRIX.md`: Updated safety documentation.

---

## 4. Supported Features
- **`returns_1d`**: Simple 1-day percentage change.
- **`sma_n`**: Simple Moving Average over `n` periods (supports windows like 3, 5, 10, 20, 50, 200).
- **`volatility_n`**: Rolling standard deviation of 1-day returns over `n` periods.

---

## 5. Explicitly Blocked Features
- **`trading_signal`**: Buy/Sell/Hold signals are deferred to Wave 2B/3.
- **`rsi` / `macd`**: Complex technical indicators are deferred to maintain a simple, verified foundation.
- **Centered Windows**: Centered or future-looking rolling windows are strictly forbidden to prevent lookahead bias.

---

## 6. Safety & Write Behavior
- **Strictly Local**: `external_api_called` remains `false`. Zero network requests are made.
- **No Signals**: `trading_signal_generated` is explicitly `false` in all outputs.
- **Path Isolation**: Feature artifacts are written exclusively to `data/quant/features/` and must use the `.json.fixture` or `.parquet` formats.
- **Format Integrity**: Parquet persistence requires the `pyarrow` or `fastparquet` backend; the system blocks Parquet requests if no backend is available.

---

## 7. Command Examples
All commands default to `--dry-run`.

**Check Feature Contract:**
```bash
ws quant feature-contract-check
```

**Build Features (Dry-run):**
```bash
ws quant feature-build --input data/quant/raw/fixture/SPY.json.fixture --features returns_1d,sma_3
```

**Build and Persist Features:**
```bash
ws quant feature-build --input data/quant/raw/fixture/SPY.json.fixture --features returns_1d,sma_5,volatility_5 --write-features
```

---

## 8. Remaining Unknowns
- Handling of non-numeric data in custom feature requests.
- Performance impact of large rolling windows on multi-million row datasets.
- Schema evolution for feature store metadata.

---

## 9. Conclusion
**Wave 2A is complete.** The Quant lane now has a verified, safe, and deterministic rail for generating research features.

**Recommended Next Task:**
> **Wave 2B: Technical Indicator Library (Safe Core).**
> Implement `rsi`, `macd`, and `bollinger_bands` in `scripts/quant/features.py` after extending the `feature_contracts.yaml` to include these as "verified technical indicators."
