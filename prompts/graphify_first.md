# Prompt: Graphify First

You are tasked with answering a question or performing a task on a codebase.

## Constraints
- **Do NOT** start by reading individual files.
- **DO** query the Graphify graph first.

## Instructions
1. Check the `graphify-out/manifest.json` or `GRAPH_REPORT.md` for a high-level overview.
2. Use `graphify query "<question>"` to find relevant symbols and files.
3. Use `graphify explain <module>` to understand specific components.
4. Only read files once you have pinpointed the exact locations needed for the task.
5. Keep the context window compact by only including essential snippets.

## Context
Project: {{project_key}}
Graph Path: {{graph_path}}
Question: {{question}}
