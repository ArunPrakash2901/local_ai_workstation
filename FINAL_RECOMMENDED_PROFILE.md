# Final Recommended AI Profile

This profile was selected after testing 4k, 8k, and 16k context lengths, evaluating memory usage on the 8GB RTX 4070, and testing WSL-to-Host networking.

## Best Daily Profile
- **Runtime**: Ollama (v0.23.0)
- **Model**: `hermes3:8b`
- **Context Setting**: `8192`
- **Performance**: ~50 tokens/sec
- **VRAM Footprint**: ~6.2 GB (leaves ~1.5 GB for OS/Display)

## Core Configuration (User Environment Variables)
These are already applied to your Windows user profile:
```env
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_MODELS=D:\ollama\models
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KEEP_ALIVE=30m
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
```

## WSL Networking
WSL is configured to use `networkingMode=mirrored`. This means Ollama running on Windows is natively accessible from WSL via `http://localhost:11434`.

## Rejected Configurations
- **16k Context**: Rejected. VRAM usage hits ~6.7GB and speed drops to ~28 tok/s. Not worth the performance penalty for daily use.
- **vLLM / ExLlama**: Rejected. High setup complexity for minimal gain on an 8GB laptop GPU. Ollama's `llama.cpp` backend is already highly optimized.
- **Overclocking/Undervolting**: Skipped. Thermals peaked at a safe 59°C during heavy 16k load. No hardware tweaking needed.

## Hot-Model Workflow
Your model is kept "hot" via `OLLAMA_KEEP_ALIVE=30m`. This means the first query might take 5 seconds to load weights into VRAM, but all subsequent queries within 30 minutes will respond instantly.

## What to Revisit Later
- **Disk Space**: C: drive is very low (~26GB). Revisit cleaning up old Windows updates or WSL images if it drops below 10GB.
- **16k+ Context**: If you upgrade to an external server with an RTX 3090 (24GB VRAM), you can push the context to 32k. For now, stick to 8k chunking via Graphify.
