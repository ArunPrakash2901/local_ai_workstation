$ErrorActionPreference = "Stop"

$model = "hermes3:8b"
if ($args.Count -gt 0) {
    $model = $args[0]
}

Write-Host "Warming up model: $model"
Write-Host "This will load it into VRAM and keep it hot for 30 minutes..."

try {
    $body = @{
        model = $model
        prompt = ""
    } | ConvertTo-Json
    
    $start = Get-Date
    Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing | Out-Null
    $elapsed = (Get-Date) - $start
    
    Write-Host "[OK] Model loaded successfully in $($elapsed.TotalSeconds) seconds." -ForegroundColor Green
    
    $gpu = nvidia-smi.exe --query-gpu=memory.used --format=csv,noheader
    Write-Host "Current VRAM Usage: $gpu" -ForegroundColor Cyan
} catch {
    Write-Host "[FAIL] Could not load model: $_" -ForegroundColor Red
}
