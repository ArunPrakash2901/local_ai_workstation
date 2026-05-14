# Machine State Report
Generated: 2026-05-11 15:05 AEST

## CPU
- **Model**: 13th Gen Intel Core i9-13900HX
- **Cores**: 24 (8P + 16E)
- **Threads**: 32
- **Max Clock**: 2200 MHz (base), turbo up to 5.4 GHz

## RAM
- **Total**: 63.73 GB DDR5
- **Available**: ~46 GB (at time of report)

## GPU
- **Model**: NVIDIA GeForce RTX 4070 Laptop GPU
- **Driver**: 596.36
- **VRAM**: 8188 MiB (8 GB)
- **Compute Capability**: 8.9 (Ada Lovelace)
- **Idle VRAM**: ~482 MiB
- **Hermes loaded VRAM**: ~5686 MiB
- **Idle Temperature**: 36°C
- **Idle Power**: ~4W

## Storage
| Drive | Used (GB) | Free (GB) | Total (GB) |
|-------|-----------|-----------|------------|
| C:    | 437.8     | 26.5      | 464.3      |
| D:    | 79.9      | 408.4     | 488.3      |

> [!WARNING]
> C: drive is low on space (26.5 GB free). Monitor this.

## OS
- Windows 11 (Build 26200.8328)

## WSL
- **Distro**: Ubuntu (WSL 2)
- **WSL Version**: 2.6.3.0
- **Kernel**: 6.6.87.2-1
- **Networking**: Mirrored mode (localhost accessible)

## Ollama
- **Version**: 0.23.0
- **Models Path**: D:\ollama\models
- **Host**: 0.0.0.0:11434
- **Status**: Running
- **Models**:
  - hermes3:8b (Q4_0, 4.7 GB, Llama family)
  - qwen2.5-coder:7b (Q4_K_M, 4.7 GB, Qwen2 family)

## Ollama Environment (User)
- OLLAMA_MODELS=D:\ollama\models
- OLLAMA_HOST=0.0.0.0:11434
- OLLAMA_FLASH_ATTENTION=1
- OLLAMA_KEEP_ALIVE=30m
- OLLAMA_MAX_LOADED_MODELS=1
- OLLAMA_NUM_PARALLEL=1

## Connectivity
- Windows → Ollama: ✅ Working (localhost:11434)
- WSL → Ollama: ✅ Working (localhost:11434 via mirrored networking)

## Hermes 3 8B Performance (Quick Test)
- **Tokens/sec**: ~49-53 tok/s
- **VRAM Usage**: ~5.2 GB loaded
- **Temperature**: 38°C during inference
