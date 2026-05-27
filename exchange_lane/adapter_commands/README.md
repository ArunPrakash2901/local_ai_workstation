# Exchange Adapter Command Templates

This directory contains deliberately disabled command templates for guarded real
CLI dispatch.

Real CLI dispatch supports `codex_cli` and `gemini_cli` in this MVP slice. A
template must be reviewed and changed to `enabled: true` before
`ws exchange real-dispatch --confirm` can launch those CLIs.

`ollama_local_command.json` is a planned local-provider adapter config. It is
disabled by default and declares the endpoint/model for future guarded provider
dispatch, but the current dispatcher refuses `--confirm` for Ollama until a
bounded request-body provider dispatcher is implemented.

The dispatcher builds argv from JSON fields only. It does not accept arbitrary
shell strings, does not use `shell=True`, does not start terminals, and does not
auto-approve CLI permission prompts.

Tests must use temporary enabled fake configs and mocked subprocesses. Production
templates remain disabled by default.
