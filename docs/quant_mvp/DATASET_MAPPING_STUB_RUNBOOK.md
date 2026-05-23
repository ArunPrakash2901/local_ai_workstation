# Dataset Mapping Stub Runbook

## Purpose
Once the data requirements are formalized, the system needs to map those requirements to physical, local datasets. This runbook explains how to generate the Dataset Mapping Stub.

## How Dataset Mapping Works
For this milestone, the engine assumes NO data is available. It generates a stub marked `needs_source_decision`.

## Local Path Checking Only
If a proposed local path is provided in the future, the engine will only run `Path(path).exists()`. It will not read the file contents, preserving RAM (<150MB constraint) and enforcing the "no large files" policy.

## Data Quality
Fields like `data_quality_known` will remain `UNKNOWN` until an explicit data quality pass is performed in a later milestone.

## Execution
```powershell
python scripts/quant/backtest_preparation_cli.py dataset-mapping `
  --data-requirement-file reports/quant/backtest_data_requirements/<REQ_ID>.json `
  --dry-run
```
*(Append `--write` to save it).*

## Safety Boundaries
- **No APIs:** No data is downloaded.
- **No Speculation:** If the file does not exist, `local_file_exists` is strictly set to `False`.