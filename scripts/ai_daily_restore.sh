#!/bin/bash

# Unload any currently loaded models first
bash /mnt/d/_ai_brain/scripts/ai_model_unload.sh

# Restore safe daily profile
bash /mnt/d/_ai_brain/scripts/ai_model_use.sh hermes_default
bash /mnt/d/_ai_brain/scripts/ai_kv_use.sh stable_default

echo "Daily profile restored: hermes_default, stable_default KV, 8192 context."
echo "Unloaded all models from VRAM."
echo "Note: Run ai_apply_ollama_profile.ps1 in PowerShell to finalize environment."
