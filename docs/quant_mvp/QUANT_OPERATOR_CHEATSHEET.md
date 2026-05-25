# Quant Operator Cheatsheet

## 1. Active Read-Only Commands (Unified `ws`)

| Command | Description |
|---|---|
| `ws quant dashboard` | High-level research lane overview |
| `ws quant idea-intake-dry-run` | Preview idea intake from file |
| `ws quant reports` | List completed Q milestone reports |
| `ws quant artifacts` | Summarize artifact counts and status |
| `ws quant lineage <id>` | Trace artifact parent/child links |
| `ws quant cheatsheet` | Show this cheatsheet |
| `ws quant status` | High-level researcher status |
| `ws quant list-tools` | List standalone research CLIs |
| `ws quant gates-status` | Check pre-backtest gate readiness |
| `ws quant synthetic-status` | Check synthetic simulation state |

## 2. Common Workflows

### Intake & Research
- Preview idea intake: `ws quant idea-intake-dry-run --title "VWAP" --idea-file scratch/quant_ideas/vwap.md`
- List reports: `ws quant reports`
- Count artifacts: `ws quant artifacts`

### Inspecting Progress
- Check the dashboard: `ws quant dashboard`

### Tracing Lineage
- Trace a candidate: `ws quant lineage CAN-951be4d5c93a-R3`
- Trace a synthetic run: `ws quant lineage SYN-f30f839cbcb1`

### Verifying Safety
- Check gates: `ws quant gates-status`
- Confirm synthetic-only: `ws quant synthetic-status`

## 3. Guarded Write Design & No-Op Executor (Q45-Q53)

- **Status:** DESIGNED but BLOCKED. No `ws` write command exists yet.
- **Active Command:** `ws quant idea-intake-dry-run` remains the only intake command.
- **Future Protocol:** Human Approval Forms (HAF) are required for any local write.
- **Validator:** `scripts/quant/human_write_approval.py` is ready to inspect future approvals.
- **Prep Tool (Standalone):** `python scripts/quant/write_approval_prepare_cli.py prepare-idea-intake-approval`
- **No-Op Executor (Standalone):** `python scripts/quant/guarded_write_executor_cli.py noop-execute --approval-file <file> --write-audit`

## 4. Standalone Research CLIs (Wave 1)

These tools remain standalone and require explicit execution from `scripts/quant/`.

- `idea_cli.py`: Research idea intake
- `paper_replication_cli.py`: Academic paper replication plans
- `strategy_candidate_cli.py`: Strategy candidate drafting
- `backtest_cli.py`: Backtest planning and gating
- `synthetic_execution_cli.py`: Synthetic simulation execution

## 4. Safety & Resource Boundaries

- **NO REAL BACKTESTS:** Real backtesting is blocked in this milestone.
- **NO APPROVALS:** Human approval granting is not exposed through `ws`.
- **NO DATA DOWNLOADS:** The workstation does not download market data automatically.
- **CPU ONLY:** All Quant research is CPU-only; no GPU usage is authorized.
- **LOW RAM:** Peak usage must remain below 100MB for these read-only commands.

## 5. Examples

```bash
# Get high-level status
ws quant status

# Lookup a specific candidate
ws quant lineage CAN-951be4d5c93a-R3

# List all available tools
ws quant list-tools
```
