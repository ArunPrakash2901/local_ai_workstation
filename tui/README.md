# Operator TUI

The operator TUI is intentionally read-only. It uses the same allowlisted workstation status commands in every mode:

- `ws ready`
- `ws stronghold-status`
- `ws handoff-status`
- `ws feature-status`
- `ws agent-hygiene`

## Dependency Policy

Option C is the current policy:

- `--snapshot` and `--plain` must remain dependency-free and available with the Python standard library alone.
- Textual is optional and must not be installed automatically.
- `ws tui` should use Textual when it is already available and otherwise fall back to plain mode.
- `ws tui --textual` may require Textual, but it must fail safely with a clear message if the dependency is missing.
- Any future Textual installation should use a dedicated virtual environment or another documented, approved dependency process.

The dashboard does not read unsafe folders by default, including `.env`, credentials, raw datasets, model files, archives, or `.git`.
