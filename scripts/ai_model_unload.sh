#!/bin/bash

# Unload all models from Ollama VRAM
OLLAMA_HOST=${OLLAMA_HOST:-"http://localhost:11434"}

# To unload, we call generate with keep_alive=0
# Or just list and then do nothing? Actually keep_alive=0 is the trick.
curl -s -X POST "$OLLAMA_HOST/api/generate" -d '{
  "model": "hermes3:8b",
  "prompt": "",
  "keep_alive": 0
}' > /dev/null

echo "Requested model unload from VRAM."
