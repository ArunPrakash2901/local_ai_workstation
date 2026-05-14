param(
    [string]$RunFolder = '',
    [switch]$VerboseMode
)

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AutoRoot = Resolve-Path (Join-Path (Split-Path -Parent $ScriptRoot) 'auto_runs') | Select-Object -ExpandProperty Path
function Convert-WslToWindowsPath([string]$Path) {
    if ($Path -match '^/mnt/([a-z])/(.*)$') {
        return "$($Matches[1].ToUpper()):\" + ($Matches[2] -replace '/', '\')
    }
    return $Path
}

function Get-LatestAgentRun([string]$Root) {
    $dirs = Get-ChildItem -LiteralPath $Root -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like '*agent*' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'task.md')) } |
        Sort-Object LastWriteTime -Descending
    if ($dirs) { return $dirs | Select-Object -First 1 }
    return $null
}

if ($RunFolder -and $RunFolder -ne 'latest') {
    $RunFolder = Convert-WslToWindowsPath $RunFolder
} elseif (-not $RunFolder -or $RunFolder -eq 'latest') {
    $latest = Get-LatestAgentRun $AutoRoot
    if ($latest) {
        $RunFolder = $latest.FullName
    }
}

if ($RunFolder -and (Test-Path -LiteralPath (Join-Path $RunFolder 'status.txt'))) {
    $statusText = (Get-Content -LiteralPath (Join-Path $RunFolder 'status.txt') -Raw -ErrorAction SilentlyContinue).Trim()
    $stdoutPath = Join-Path $RunFolder 'codex_stdout.md'
    $stderrPath = Join-Path $RunFolder 'codex_stderr.md'
    if (($statusText -match '^(CODEX_HANDOFF_READY|PLAN_ONLY)$') -and -not (Test-Path -LiteralPath $stdoutPath) -and -not (Test-Path -LiteralPath $stderrPath)) {
        $report = @(
            'Windows Agent Import',
            '---------------------',
            'Status: CODEX_NO_CHANGES',
            "Run: $RunFolder",
            'Notes: handoff run has no Codex output yet.'
        ) -join "`n"
        Set-Content -LiteralPath (Join-Path $RunFolder 'status.txt') -Value "CODEX_NO_CHANGES`n" -Encoding utf8
        Set-Content -LiteralPath (Join-Path $RunFolder 'final_report.md') -Value $report -Encoding utf8
        Write-Output 'CODEX_NO_CHANGES'
        Write-Output $RunFolder
        exit 0
    }
}

& (Join-Path $ScriptRoot 'ws_agent_run.ps1') -Command Import -RunFolder $RunFolder
