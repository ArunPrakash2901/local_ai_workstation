# Global Graph Status

**Location**: `~/.graphify/global-graph.json` (inside WSL)
**Last Updated**: 2026-05-11

## Overview
Graphify has been installed and configured inside an isolated WSL python environment (`D:\_ai_brain\runtimes\graphify_venv`). It actively maintains local graphs per-project and aggregates them into a global knowledge graph.

## Indexed Projects

| Project | Nodes | Graph Location | Note |
|---|---|---|---|
| **portfolio_website** | 372 | `D:\portfolio_website\graphify-out\graph.json` | Core product site. |
| **Simulation** | 32 | `D:\Simulation\graphify-out\graph.json` | - |
| **GSP** | 7 | `D:\GSP\graphify-out\graph.json` | R-based research repo. |
| **LLM-engineer-handbook** | 7 | `D:\LLM-engineer-handbook\graphify-out\graph.json` | Reference repo. |
| **Melbourne-Oil-Scarcity-outlook** | 6 | `D:\Melbourne-Oil-Scarcity-outlook\graphify-out\graph.json` | Research repo. |

*Note: `kaagle_competitions` yielded 0 nodes (likely all files ignored by `.graphifyignore` or only contained binary/dataset files).*

## Interaction Rules
1. **Never scan the raw root of `D:\`**. Always CD into a project folder (e.g., `cd D:\portfolio_website`) and run `graphify update .`.
2. **Re-extraction**: If you make major architectural changes, run `graphify update .` locally.
3. **Cross-Project Query**: To query the global graph for cross-project dependencies, you can use:
   `graphify query "..." --graph ~/.graphify/global-graph.json`
