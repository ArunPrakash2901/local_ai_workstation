# Low-Resource Mode

Low-Resource Mode is the default operating posture of the Local AI Workstation. It guarantees that the workstation will remain fully functional and responsive without stressing the 16GB RAM and 8GB VRAM limits.

## Default Disabled Features
To maintain low resource footprint, the following technologies and workflows are disabled by default:
- **Embeddings:** No local embedding models loaded in memory.
- **RAG / Vector DBs:** No persistent ChromaDB, Milvus, or Faiss servers.
- **Local LLMs:** Ollama and local models remain unloaded until explicitly invoked.
- **Browser Automation:** Selenium, Playwright, or Puppeteer are strictly disabled.
- **Full Repo Scans:** Unbounded recursive `grep` or AST traversals in memory.
- **Large Dataframe Loads:** Loading entire market histories into pandas.
- **Unbounded Backtests:** Heavy multi-variate walk-forward optimizations are deferred to specialized execution runs.

## What Is Allowed
- Determinstic CLI routing and Python scripts.
- Markdown generation and templating.
- Reading chunked `.csv` and `.jsonl` files iteratively.
- Simple local safety validations.
- `DuckDB` queries using disk-backed execution rather than in-memory tables.

## Recommended Commands
Operators should favor these commands during long research sessions:
- `ws status`
- `ws matfinog overview` (proposed)
- `ws quant paths-check`
- `ws product-list`
- `ws task-status`

## Windows Task Hygiene
- **WSL Limits:** Ensure `.wslconfig` sets an explicit `memory=8GB` limit so WSL2 does not balloon and crash the Windows host.
- **Background Tasks:** Close heavy browsers (Chrome/Edge) with many tabs when entering a Quant research session. 
- **Docker:** Do not leave Docker Desktop running unless a specific container is required.

## Restrictions
- **Local Model Restrictions:** Only 7B to 8B parameter models quantized at Q4 or Q5 are permitted locally to respect the 8GB VRAM limit. 
- **Dataset-Size Restrictions:** CSVs larger than 100MB must not be loaded into Pandas. Use DuckDB relational queries instead.
- **Logging Rules:** Logs must rotate. No unbounded `DEBUG` level spam during regular operations. 

## Safe Fallback Behavior
If a command detects an impending OOM (Out-of-Memory) scenario or file size breach:
1. It must immediately halt execution.
2. It must print a clear error: `[RESOURCE GUARD] Task exceeded safety budget limits.`
3. It should recommend a chunking strategy or an Exchange Lane Handoff packet generation command instead.