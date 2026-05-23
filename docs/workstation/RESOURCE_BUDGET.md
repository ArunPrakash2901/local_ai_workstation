# Workstation Resource Budget

This document outlines the strict computing resource budget for the Local AI Workstation. The environment is constrained by the host machine (16GB RAM, RTX 4070 Laptop GPU with 8GB VRAM limit). 

All development, processing, and commands must respect these limitations to ensure system stability and responsiveness.

## CPU Expectations
*   **Default Use:** Standard Python execution (e.g. data ingestion, CLI commands, markdown generation) must be single-threaded or minimally multi-threaded. 
*   **Heavy Processing:** CPU-heavy tasks (e.g. DuckDB aggregations, Parquet conversions) should not exceed 50% CPU utilization over sustained periods to preserve operator UI responsiveness.

## RAM Expectations
*   **Default workflows must run comfortably on 16GB RAM.** 
*   The system overhead (Windows + WSL2 + background tasks) typically consumes 6GB-8GB. 
*   **Workstation RAM Budget:** The workstation process itself should idle under 100MB and peak under 2GB.
*   **Announcement Rule:** Any task that may use more than 2GB RAM (e.g. loading large pandas DataFrames) must announce it via stdout before executing, requiring explicit operator approval.

## GPU and VRAM Limit Policy
*   **Default workflows must not require GPU.** By default, the workstation is purely a text/command processor.
*   **VRAM Ceiling:** The absolute VRAM ceiling is 8GB. 
*   **Explicit Flag Rule:** Any task that may use the GPU (e.g. local Ollama calls) must require an explicit flag (like `--llm` or `--model`) and confirmation. Background scripts must never "silently" spin up CUDA loads.

## Local LLM Policy
*   **Explicit Use Only:** Local LLM usage is explicitly forbidden for generic workstation routing, CLI parsing, and text formatting.
*   **When Forbidden:** Routine command processing, generating index artifacts, data scraping, embeddings, and any automated pipeline without human intervention.
*   **When Allowed:** Only when explicitly requested by the operator (e.g., `ws feature-local-review`, `ws task-split --llm`) for specific generative tasks, subject to VRAM limits.
*   **Cloud Fallback:** When a task requires context windows exceeding local limits (e.g., > 16k tokens) or exceeds local GPU VRAM capabilities, the system must fallback to creating a **Handoff Packet** for the Exchange Lane, deferring processing to cloud models rather than crashing locally.

## File Size and Memory Policy
*   **No-Large-Load Rule:** Do not load monolithic files into memory. 
*   **Maximum File Sizes:**
    *   JSON / YAML configs: < 10MB
    *   CSVs / Data: < 100MB for in-memory loads.
*   **Streaming/Chunking Expectations:** For any dataset or text corpus exceeding 100MB, the system must use generators, chunking, or streaming iteration (e.g., Polars/DuckDB out-of-core processing, or line-by-line JSONL readers).
