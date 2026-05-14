$ErrorActionPreference = "Stop"

Write-Host "========================================="
Write-Host " AI Workstation Health Check"
Write-Host "========================================="
Write-Host ""

# 1. Check Ollama API
Write-Host "1. Checking Ollama runtime..."
try {
    $r = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   [OK] Ollama is running and responding." -ForegroundColor Green
} catch {
    Write-Host "   [FAIL] Ollama is NOT reachable on localhost:11434." -ForegroundColor Red
    Write-Host "          Error: $_"
}

# 2. Check WSL Network
Write-Host "2. Checking WSL Connectivity..."
try {
    $wslCheck = wsl -d Ubuntu -- bash -c "curl -s --connect-timeout 2 http://localhost:11434/api/tags > /dev/null && echo OK || echo FAIL"
    if ($wslCheck -match "OK") {
        Write-Host "   [OK] WSL can reach Ollama natively (Mirrored Networking)." -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] WSL cannot reach Ollama." -ForegroundColor Red
    }
} catch {
    Write-Host "   [FAIL] Could not run WSL command." -ForegroundColor Red
}

# 3. Check Loaded Models (VRAM Status)
Write-Host "3. Checking Loaded Models..."
try {
    $ps = Invoke-WebRequest -Uri "http://localhost:11434/api/ps" -UseBasicParsing | ConvertFrom-Json
    if ($ps.models.Count -eq 0) {
        Write-Host "   [INFO] No models currently loaded in VRAM." -ForegroundColor Yellow
    } else {
        foreach ($m in $ps.models) {
            $sizeMB = [math]::Round($m.size_vram / 1MB, 1)
            Write-Host "   [OK] Loaded Model: $($m.name) ($sizeMB MB in VRAM)" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "   [FAIL] Could not query loaded models." -ForegroundColor Red
}

# 4. Check GPU Status
Write-Host "4. Checking GPU..."
try {
    $gpu = nvidia-smi.exe --query-gpu=memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader
    if ($gpu) {
        Write-Host "   [OK] RTX 4070 Status: $gpu (Used MiB, Total MiB, Temp C, Power W)" -ForegroundColor Green
    }
} catch {
    Write-Host "   [FAIL] Could not query NVIDIA SMI." -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================="
Write-Host " Health Check Complete"
Write-Host "========================================="
