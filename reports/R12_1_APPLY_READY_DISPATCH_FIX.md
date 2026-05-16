# R12.1: Apply-Ready Dispatch Fix

## Root Cause
1. **Dispatcher Syntax Error:** During the R12 implementation, an imprecise string replacement introduced a malformed `esac` block at the bottom of `scripts/ws`, causing a bash syntax error (`unexpected EOF` / `syntax error near unexpected token 'esac'`). Additionally, the `apply-ready)` routing logic failed to insert correctly.
2. **Line Endings:** The new `scripts/ws_apply_ready.sh` script was saved with `CRLF` line endings, which is invalid in the WSL Bash environment, causing syntax errors (`unexpected token '$'{\r''`).

## Files Changed
- `scripts/ws`: Removed the duplicated/corrupted `esac` logic at the end of the file. Correctly inserted the `apply-ready)` dispatch route right before the `agent-run)` command block.
- `scripts/ws_apply_ready.sh`: Normalized line endings from CRLF to LF using `sed`.

## Syntax Validation Result
- `bash -n scripts/ws` successfully passed with no syntax errors.
- `bash -n scripts/ws_apply_ready.sh` successfully passed with no syntax errors.

## Execution Validation
The `ws apply-ready` command is now correctly recognized by the `ws` dispatcher. 
Running `ws apply-ready workstation_control_plane <task_file>` successfully executed the `ws_apply_ready.sh` script, which correctly performed its read-only checks, aborted due to the uncommitted Git changes, and safely returned `BLOCKED_DIRTY_REPO`. The implementation is fully functional and safely contained.
