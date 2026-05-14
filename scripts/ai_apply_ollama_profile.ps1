# PowerShell script to apply Ollama environment variables and restart
$activeKvPath = "D:\_ai_brain\registry\active_kv_profile.yaml"
if (!(Test-Path $activeKvPath)) {
    Write-Error "Active KV profile not found."
    return
}

$activeKv = Get-Content $activeKvPath | ConvertFrom-Yaml
# Wait, PowerShell doesn't have ConvertFrom-Yaml by default. 
# Let's use a simple regex approach since the YAML is simple.

$content = Get-Content $activeKvPath -Raw
$kvType = if ($content -match 'kv_cache_type:\s*(\S+)') { $Matches[1] } else { "default" }
$flash = if ($content -match 'flash_attention:\s*(\S+)') { $Matches[1] } else { "true" }

Write-Host "Applying Profile: KV=$kvType, Flash=$flash"

# Set environment variables for the current session and globally
[Environment]::SetEnvironmentVariable("OLLAMA_KV_CACHE_TYPE", $kvType, "User")
[Environment]::SetEnvironmentVariable("OLLAMA_FLASH_ATTENTION", if ($flash -eq "true") { "1" } else { "0" }, "User")

Write-Host "Restarting Ollama..."
Stop-Process -Name "ollama" -ErrorAction SilentlyContinue
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden

Write-Host "Ollama restarted with new profile."
