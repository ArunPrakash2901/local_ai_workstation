param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('Run', 'Status', 'Canary', 'Import')]
    [string]$Command = 'Run',

    [string]$ProjectKey = '',
    [string]$TaskFile = '',

    [ValidateSet('detect', 'local', 'codex', 'handoff')]
    [string]$Mode = 'detect',

    [switch]$Branch,
    [int]$MaxFiles = 5,
    [int]$MaxMinutes = 10,
    [switch]$StopOnFail,
    [switch]$DryRun,
    [string]$Tests = '',
    [string]$RunFolder = '',
    [string]$RepoOverride = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WSHome = (Resolve-Path (Join-Path $ScriptRoot '..')).Path
$AutoRoot = Join-Path $WSHome 'auto_runs'
$ReportsRoot = Join-Path $WSHome 'reports'
$ScratchRoot = Join-Path $WSHome 'scratch'
$ProjectsYaml = Join-Path $WSHome 'registry\projects.yaml'
$CanaryCache = Join-Path $ReportsRoot 'agent_canary_status.json'
$CanaryScratch = Join-Path $ScratchRoot 'agent_canary.md'
$script:ActiveRun = ''

function Ensure-Dir([string]$Path) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Write-Text([string]$Path, [string]$Text) {
    $parent = Split-Path -Parent $Path
    if ($parent) { Ensure-Dir $parent }
    Set-Content -LiteralPath $Path -Value $Text -Encoding utf8
}

function Append-Text([string]$Path, [string]$Text) {
    $parent = Split-Path -Parent $Path
    if ($parent) { Ensure-Dir $parent }
    Add-Content -LiteralPath $Path -Value $Text -Encoding utf8
}

function Heartbeat([string]$Run, [string]$Message) {
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss UTC')
    Append-Text (Join-Path $Run 'heartbeat.log') "$stamp $Message`n"
}

function Convert-ToWindowsPath([string]$Path) {
    if ($Path -match '^/mnt/([a-z])/(.*)$') {
        return "$($Matches[1].ToUpper()):\" + ($Matches[2] -replace '/', '\')
    }
    return $Path
}

function Resolve-ExistingPath([string]$Path) {
    return (Resolve-Path -LiteralPath (Convert-ToWindowsPath $Path)).Path
}

function Resolve-CodexLauncher {
    $preferred = Join-Path $env:APPDATA 'npm\codex.cmd'
    if (Test-Path -LiteralPath $preferred) {
        return [pscustomobject]@{ Kind = 'cmd'; Path = $preferred; Label = 'codex.cmd (APPDATA)' }
    }
    $cmd = Get-Command codex.cmd -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) {
        return [pscustomobject]@{ Kind = 'cmd'; Path = $cmd.Source; Label = 'codex.cmd (PATH)' }
    }
    $ps1 = Get-Command codex.ps1 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($ps1) {
        return [pscustomobject]@{ Kind = 'ps1'; Path = $ps1.Source; Label = 'codex.ps1 (fallback)' }
    }
    return $null
}

function Get-CodexLauncherText {
    $launcher = Resolve-CodexLauncher
    if (-not $launcher) { return 'codex launcher unavailable' }
    return "$($launcher.Label): $($launcher.Path)"
}

function Quote-Arg([string]$Value) {
    if ($null -eq $Value) { return '""' }
    return '"' + ($Value -replace '"', '\"') + '"'
}

function Invoke-Process {
    param(
        [string]$FileName,
        [string[]]$ArgumentList = @(),
        [string]$RawArguments = '',
        [string]$WorkingDirectory,
        [string]$StdInText = '',
        [int]$TimeoutSeconds = 60,
        [string]$Run = '',
        [string]$Label = 'command'
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FileName
    $psi.Arguments = if ($RawArguments) { $RawArguments } else { ($ArgumentList | ForEach-Object { Quote-Arg $_ }) -join ' ' }
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    if ($StdInText) { $psi.RedirectStandardInput = $true }

    $proc = [System.Diagnostics.Process]::new()
    $proc.StartInfo = $psi
    [void]$proc.Start()
    if ($StdInText) {
        $proc.StandardInput.Write($StdInText)
        $proc.StandardInput.Close()
    }

    $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
    $stderrTask = $proc.StandardError.ReadToEndAsync()
    $start = Get-Date
    $lastBeat = $start
    $timedOut = $false

    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 1
        if ($Run -and (((Get-Date) - $lastBeat).TotalSeconds -ge 30)) {
            Heartbeat $Run "$Label still running"
            $lastBeat = Get-Date
        }
        if (((Get-Date) - $start).TotalSeconds -ge $TimeoutSeconds) {
            $timedOut = $true
            if ($Run) { Heartbeat $Run "$Label timed out after $TimeoutSeconds seconds; terminating process tree" }
            try { cmd.exe /c "taskkill /F /T /PID $($proc.Id) >nul 2>&1" | Out-Null } catch {}
            try { if (-not $proc.HasExited) { $proc.Kill() } } catch {}
            break
        }
    }

    try { $proc.WaitForExit(5000) | Out-Null } catch {}
    $stdoutReady = $stdoutTask.Wait(5000)
    $stderrReady = $stderrTask.Wait(5000)
    $stdout = if ($stdoutReady) { $stdoutTask.Result } else { '[agent] stdout unavailable before process cleanup completed' }
    $stderr = if ($stderrReady) { $stderrTask.Result } else { '[agent] stderr unavailable before process cleanup completed' }
    if ($timedOut) {
        if (-not $stdout.Trim()) { $stdout = '[agent] no stdout captured before timeout' }
        $stderr = (($stderr.Trim(), "[agent] process timed out after $TimeoutSeconds seconds") | Where-Object { $_ }) -join "`n"
    }
    $exitCode = if ($proc.HasExited) { $proc.ExitCode } else { -1 }
    if ($Run) { Heartbeat $Run "$Label completed rc=$exitCode" }
    return [pscustomobject]@{
        ExitCode = $exitCode
        StdOut = $stdout.Trim()
        StdErr = $stderr.Trim()
        TimedOut = $timedOut
    }
}

function Invoke-Codex {
    param(
        [string]$RepoPath,
        [string]$PromptPath,
        [string]$ResponsePath,
        [int]$TimeoutSeconds,
        [string]$Run,
        [string]$Label
    )

    $launcher = Resolve-CodexLauncher
    if (-not $launcher) {
        return [pscustomobject]@{ Started = $false; ExitCode = $null; StdOut = ''; StdErr = 'codex launcher not found'; TimedOut = $false }
    }
    Write-Text (Join-Path $Run 'codex_launcher.md') ((Get-CodexLauncherText) + "`n")
    $prompt = Get-Content -LiteralPath $PromptPath -Raw
    $args = @(
        'exec',
        '--skip-git-repo-check',
        '--ignore-user-config',
        '--ephemeral',
        '--dangerously-bypass-approvals-and-sandbox',
        '--sandbox', 'danger-full-access',
        '-C', $RepoPath,
        '--output-last-message', $ResponsePath,
        '-'
    )
    if ($launcher.Kind -eq 'cmd') {
        $argTail = ($args | ForEach-Object { Quote-Arg $_ }) -join ' '
        $rawArgs = "/d /s /c call $(Quote-Arg $launcher.Path) $argTail"
        $result = Invoke-Process -FileName 'cmd.exe' -RawArguments $rawArgs -WorkingDirectory $WSHome -StdInText $prompt -TimeoutSeconds $TimeoutSeconds -Run $Run -Label $Label
    } else {
        $wrapped = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $launcher.Path) + $args
        $result = Invoke-Process -FileName 'powershell.exe' -ArgumentList $wrapped -WorkingDirectory $WSHome -StdInText $prompt -TimeoutSeconds $TimeoutSeconds -Run $Run -Label $Label
    }
    return [pscustomobject]@{
        Started = $true
        ExitCode = $result.ExitCode
        StdOut = $result.StdOut
        StdErr = $result.StdErr
        TimedOut = $result.TimedOut
    }
}

function Invoke-Git([string]$RepoPath, [string[]]$GitArgs) {
    return Invoke-Process -FileName 'git' -ArgumentList (@('-C', $RepoPath) + $GitArgs) -WorkingDirectory $RepoPath -TimeoutSeconds 60
}

function Get-ProjectPath([string]$Key) {
    if ($RepoOverride) {
        return Resolve-ExistingPath $RepoOverride
    }
    $text = Get-Content -LiteralPath $ProjectsYaml -Raw
    $match = [Regex]::Match($text, "(?ms)^\s{2}$([Regex]::Escape($Key)):\s*$\r?\n(?<block>(?:^\s{4}.*\r?\n?)*)")
    if (-not $match.Success) { throw "Project key not found: $Key" }
    $wsl = [Regex]::Match($match.Groups['block'].Value, '(?m)^\s{4}wsl_path:\s*(.+?)\s*$')
    if (-not $wsl.Success) { throw "Project path missing for $Key" }
    return Resolve-ExistingPath $wsl.Groups[1].Value.Trim('"')
}

function Get-TaskInfo([string]$Path) {
    $text = Get-Content -LiteralPath $Path -Raw
    $titleMatch = [Regex]::Match($text, '(?im)^#\s*Task\s+(\d+)\s*[:\-]\s*(.+)$')
    function Section([string]$Name) {
        $m = [Regex]::Match($text, "(?ms)^\s*$([Regex]::Escape($Name)):\s*$\r?\n(?<body>.*?)(?=^\s*[A-Za-z][A-Za-z ]*:\s*$|^#\s*Task\s+\d+|\z)")
        if ($m.Success) { return $m.Groups['body'].Value.Trim() }
        return ''
    }
    $allowed = @()
    foreach ($line in (Section 'Allowed Files') -split "\r?\n") {
        $value = ($line.Trim() -replace '^-+\s*', '').Trim()
        if ($value -and $value -ne 'not specified' -and $value -ne 'REQUIRED_BEFORE_APPLY') { $allowed += $value }
    }
    return [pscustomobject]@{
        TaskNum = if ($titleMatch.Success) { [int]$titleMatch.Groups[1].Value } else { 1 }
        Title = if ($titleMatch.Success) { $titleMatch.Groups[2].Value.Trim() } else { 'task' }
        Allowed = $allowed
        HasAllowed = [bool]$allowed.Count
        Body = $text
    }
}

function New-RunFolder([string]$ProjectKey, [psobject]$Task, [string]$Suffix) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $slug = ($Task.Title -replace '[^A-Za-z0-9]+', '_').Trim('_').ToLower()
    if (-not $slug) { $slug = 'task' }
    return Join-Path $AutoRoot "$stamp`_$ProjectKey`_$($Task.TaskNum.ToString('000'))`_$slug`_$Suffix"
}

function Write-RunSummary(
    [string]$Run,
    [string]$Status,
    [string]$ModeLabel,
    [string]$Notes,
    [string[]]$Changed,
    [string[]]$Unsafe,
    [string]$ManualInstruction,
    [string]$AllowedFilesCheck = 'not applicable',
    [string[]]$ChangeDetectionErrors = @()
) {
    $lines = @(
        '# Windows Agent Orchestrator Report',
        '',
        '## Summary',
        "- Status: $Status",
        "- Mode: $ModeLabel",
        "- Notes: $Notes",
        '',
        '## Changed Files'
    )
    if ($Changed.Count) { $lines += $Changed | ForEach-Object { "- $_" } } else { $lines += '- none' }
    $lines += ''
    $lines += '## Unsafe Files'
    if ($Unsafe.Count) { $lines += $Unsafe | ForEach-Object { "- $_" } } else { $lines += '- none' }
    $lines += ''
    $lines += '## Allowed Files Check'
    $lines += "- $AllowedFilesCheck"
    $lines += ''
    $lines += '## Change Detection Errors'
    if ($ChangeDetectionErrors.Count) { $lines += $ChangeDetectionErrors | ForEach-Object { "- $_" } } else { $lines += '- none' }
    $lines += ''
    $lines += '## Manual Instruction'
    $lines += $(if ($ManualInstruction) { $ManualInstruction } else { 'none' })
    Write-Text (Join-Path $Run 'final_report.md') (($lines -join "`n") + "`n")
}

function Ensure-CodexArtifacts([string]$Run, [object]$Result, [string]$FallbackNote) {
    $stdout = if ($null -ne $Result -and $Result.StdOut) { $Result.StdOut } else { "[agent] stdout unavailable: $FallbackNote" }
    $stderr = if ($null -ne $Result -and $Result.StdErr) { $Result.StdErr } else { "[agent] stderr unavailable: $FallbackNote" }
    $exit = if ($null -ne $Result -and $null -ne $Result.ExitCode) { [string]$Result.ExitCode } else { "NO_PROCESS_EXIT_CODE: $FallbackNote" }
    Write-Text (Join-Path $Run 'codex_stdout.md') ($stdout + "`n")
    Write-Text (Join-Path $Run 'codex_stderr.md') ($stderr + "`n")
    Write-Text (Join-Path $Run 'codex_exit_code.txt') ($exit + "`n")
}

function Get-ChangedFiles([string]$RepoPath) {
    $result = Invoke-Git $RepoPath @('status', '--porcelain')
    $errors = @()
    if ($result.TimedOut) {
        $errors += 'git status --porcelain timed out.'
    }
    if ($result.ExitCode -ne 0) {
        $stderr = if ($result.StdErr) { $result.StdErr } else { 'no stderr captured' }
        $errors += "git status --porcelain failed with exit code $($result.ExitCode): $stderr"
    }
    if ($errors.Count) {
        return [pscustomobject]@{
            Paths = @()
            Errors = $errors
        }
    }

    $paths = @()
    foreach ($line in ($result.StdOut -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $match = [Regex]::Match($line, '^(?<status>.{2}) (?<path>.+)$')
        if (-not $match.Success) {
            $errors += "Unrecognized git status --porcelain output: $line"
            continue
        }
        $path = $match.Groups['path'].Value.Trim()
        if ($path -match ' -> ') { $path = ($path -split ' -> ', 2)[1].Trim() }
        $paths += $path
    }
    return [pscustomobject]@{
        Paths = @($paths)
        Errors = @($errors)
    }
}

function Save-CanaryCache([string]$Status, [string]$Run, [string]$Notes) {
    $existing = if (Test-Path -LiteralPath $CanaryCache) { Get-Content -LiteralPath $CanaryCache -Raw | ConvertFrom-Json } else { $null }

    $latestPass = $null
    if ($existing) {
        if (($existing.PSObject.Properties.Name -contains 'latest_pass_utc') -and $existing.latest_pass_utc) {
            $latestPass = $existing.latest_pass_utc
        } elseif (($existing.PSObject.Properties.Name -contains 'status') -and $existing.status -eq 'AGENT_CANARY_PASSED') {
            if ($existing.PSObject.Properties.Name -contains 'timestamp_utc') {
                $latestPass = $existing.timestamp_utc
            }
        }
    }

    if ($Status -eq 'AGENT_CANARY_PASSED') {
        $latestPass = (Get-Date).ToUniversalTime().ToString('o')
    }

    $payload = [ordered]@{
        status = $Status
        timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
        run_folder = $Run
        notes = $Notes
        latest_pass_utc = $latestPass
    }
    Write-Text $CanaryCache ($payload | ConvertTo-Json -Depth 4 -Compress)
}

function Run-Canary {
    Ensure-Dir $AutoRoot
    Ensure-Dir $ScratchRoot
    Ensure-Dir $ReportsRoot
    $run = Join-Path $AutoRoot ("{0}_agent_canary" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    $script:ActiveRun = $run
    Ensure-Dir $run
    Write-Text (Join-Path $run 'status.txt') "STARTED`n"
    Heartbeat $run 'agent canary started'
    Write-Host "Agent canary starting: run=$run launcher=$(Get-CodexLauncherText) timeout=3m"

    $baseline = "# Agent Canary`n`nBASELINE $(Get-Date).`n"
    Write-Text $CanaryScratch $baseline
    Write-Text (Join-Path $run 'scratch_before.md') $baseline
    $promptPath = Join-Path $run 'agent_canary_work_order.md'
    $prompt = 'Append one line to scratch/agent_canary.md: Codex canary completed. Do not modify any other file. Stop after editing.'
    Write-Text $promptPath ($prompt + "`n")
    Write-Text (Join-Path $run 'codex_prompt.md') ($prompt + "`n")

    $result = Invoke-Codex -RepoPath $WSHome -PromptPath $promptPath -ResponsePath (Join-Path $run 'codex_response.md') -TimeoutSeconds 180 -Run $run -Label 'codex canary'
    Ensure-CodexArtifacts $run $result 'canary process did not start'
    $final = Get-Content -LiteralPath $CanaryScratch -Raw -ErrorAction SilentlyContinue
    if (-not $result.Started) {
        $status = 'CODEX_NOT_STARTED'
        $notes = 'Codex launcher unavailable'
    } elseif ($result.TimedOut) {
        $status = 'AGENT_TIMEOUT'
        $notes = 'Canary timed out'
    } elseif ($result.ExitCode -ne 0) {
        $status = 'CODEX_FAILED'
        $notes = 'Canary Codex process failed'
    } elseif ($final -match 'Codex canary completed\.') {
        $status = 'AGENT_CANARY_PASSED'
        $notes = 'Codex edited the scratch canary successfully'
    } else {
        $status = 'CODEX_FAILED'
        $notes = 'Canary file did not change as expected'
    }
    Write-Text (Join-Path $run 'status.txt') "$status`n"
    try {
        Save-CanaryCache $status $run $notes
    } catch {
        $status = 'CODEX_FAILED'
        $notes = "Canary cache refresh failed: $($_.Exception.Message)"
        Write-Text (Join-Path $run 'status.txt') "$status`n"
    }
    Write-RunSummary $run $status 'canary' $notes @() @() 'Inspect canary artifacts before enabling unattended runs.'
    return $run
}

function Run-Agent {
    if (-not $ProjectKey -or -not $TaskFile) { throw 'Project key and task file are required.' }
    $repo = Get-ProjectPath $ProjectKey
    $taskPath = Resolve-ExistingPath $TaskFile
    $task = Get-TaskInfo $taskPath
    $run = New-RunFolder $ProjectKey $task 'agent_run'
    $script:ActiveRun = $run
    Ensure-Dir $run
    Heartbeat $run 'agent run started'
    Write-Text (Join-Path $run 'task.md') (Get-Content -LiteralPath $taskPath -Raw)
    Write-Text (Join-Path $run 'status.txt') "STARTED`n"

    $branchName = ''
    if ($Branch) {
        $branchName = "agent/$ProjectKey/$($task.TaskNum.ToString('000'))-$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        $branchResult = Invoke-Git $repo @('checkout', '-B', $branchName)
        Write-Text (Join-Path $run 'branch_create.log') (($branchResult.StdOut + "`n" + $branchResult.StdErr).Trim() + "`n")
    }
    Write-Text (Join-Path $run 'git_status_before.md') ((Invoke-Git $repo @('status', '--short', '--branch')).StdOut + "`n")

    $canary = if (Test-Path -LiteralPath $CanaryCache) { Get-Content -LiteralPath $CanaryCache -Raw | ConvertFrom-Json } else { $null }
    $canaryPass = $canary -and $canary.status -eq 'AGENT_CANARY_PASSED'
    $routeMode = if ($Mode -eq 'detect') { $(if ($canaryPass) { 'codex' } else { 'handoff' }) } else { $Mode }
    $willAttemptCodex = (-not $DryRun) -and $routeMode -eq 'codex' -and $canaryPass -and $task.HasAllowed
    $startup = "Agent run starting: run=$run mode=$routeMode launcher=$(Get-CodexLauncherText) timeout=${MaxMinutes}m codex_attempt=$willAttemptCodex"
    Write-Text (Join-Path $run 'startup.md') ("# Agent Run Startup`n`n- Run: $run`n- Mode: $routeMode`n- Launcher: $(Get-CodexLauncherText)`n- Timeout Minutes: $MaxMinutes`n- Codex Attempt: $willAttemptCodex`n")
    Write-Host $startup

    $workOrder = @(
        '# Work Order',
        '',
        '## Task',
        $task.Body.Trim(),
        '',
        '## Branch',
        $branchName,
        '',
        '## Allowed Files'
    )
    if ($task.Allowed.Count) { $workOrder += $task.Allowed | ForEach-Object { "- $_" } } else { $workOrder += '- none declared' }
    $workOrder += @(
        '',
        '## Working Rules',
        '- Modify only allowed files.',
        '- Do not delete files.',
        '- Do not touch secrets, raw data, or model files.',
        '- Do not commit or push.',
        '- Stop after edits.'
    )
    $workOrderPath = Join-Path $run 'codex_work_order.md'
    Write-Text $workOrderPath (($workOrder -join "`n") + "`n")
    Write-Text (Join-Path $run 'codex_prompt.md') (($workOrder -join "`n") + "`n")

    if ($DryRun) {
        Ensure-CodexArtifacts $run $null 'dry-run; Codex not launched'
        Write-Text (Join-Path $run 'status.txt') "PLAN_ONLY`n"
        Write-RunSummary $run 'PLAN_ONLY' $routeMode 'Dry run completed; Codex not launched.' @() @() 'Review work order only.'
        return $run
    }
    if (-not $task.HasAllowed) {
        Ensure-CodexArtifacts $run $null 'explicit Allowed Files missing'
        Write-Text (Join-Path $run 'status.txt') "CODEX_NOT_STARTED`n"
        Write-RunSummary $run 'CODEX_NOT_STARTED' $routeMode 'Task is missing explicit Allowed Files.' @() @() 'Add explicit task boundaries before apply.'
        return $run
    }
    if ($routeMode -ne 'codex' -or -not $canaryPass) {
        Ensure-CodexArtifacts $run $null 'Codex unattended execution not enabled'
        Write-Text (Join-Path $run 'status.txt') "CODEX_NOT_STARTED`n"
        Write-RunSummary $run 'CODEX_NOT_STARTED' $routeMode 'Codex unattended execution not enabled.' @() @() 'Use handoff/import flow.'
        return $run
    }

    Write-Text (Join-Path $run 'status.txt') "CODEX_RUNNING`n"
    Heartbeat $run 'codex execution starting'
    $result = Invoke-Codex -RepoPath $repo -PromptPath $workOrderPath -ResponsePath (Join-Path $run 'codex_response.md') -TimeoutSeconds ($MaxMinutes * 60) -Run $run -Label 'codex run'
    Ensure-CodexArtifacts $run $result 'Codex process did not start'
    if (-not $result.Started) {
        Write-Text (Join-Path $run 'status.txt') "CODEX_NOT_STARTED`n"
        Write-RunSummary $run 'CODEX_NOT_STARTED' 'codex' 'Codex process did not start.' @() @() 'Inspect launcher status.'
        return $run
    }
    if ($result.TimedOut) {
        Write-Text (Join-Path $run 'status.txt') "AGENT_TIMEOUT`n"
        Write-RunSummary $run 'AGENT_TIMEOUT' 'codex' 'Codex exceeded the run timeout.' @() @() 'Inspect Codex artifacts before retrying.'
        return $run
    }
    if ($result.ExitCode -ne 0) {
        Write-Text (Join-Path $run 'status.txt') "CODEX_FAILED`n"
        Write-RunSummary $run 'CODEX_FAILED' 'codex' 'Codex exited non-zero.' @() @() 'Inspect Codex artifacts before retrying.'
        return $run
    }

    $changeResult = Get-ChangedFiles $repo
    $changed = @($changeResult.Paths)
    $changeErrors = @($changeResult.Errors)
    $unsafe = @($changed | Where-Object { $task.Allowed -notcontains $_ })
    Write-Text (Join-Path $run 'changed_files.txt') (($changed -join "`n") + "`n")
    Write-Text (Join-Path $run 'unsafe_files.txt') (($unsafe -join "`n") + "`n")
    Write-Text (Join-Path $run 'change_detection_errors.txt') (($changeErrors -join "`n") + "`n")
    Write-Text (Join-Path $run 'status.txt') "CODEX_COMPLETED`n"
    $allowedFilesCheck = if ($changeErrors.Count) {
        'unknown: changed-file detection failed; review change_detection_errors.txt'
    } elseif ($unsafe.Count) {
        'failed: one or more changed files were outside Allowed Files'
    } else {
        'passed: all detected changed files stayed within Allowed Files'
    }
    Write-RunSummary $run 'CODEX_COMPLETED' 'codex' 'Codex process completed; review diff validation artifacts.' $changed $unsafe 'Review diff and task allowlist before marking complete.' $allowedFilesCheck $changeErrors
    return $run
}

function Run-Import([string]$Folder) {
    if (-not $Folder -or $Folder -eq 'latest') {
        $latest = Get-ChildItem -LiteralPath $AutoRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'task.md') } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if (-not $latest) { throw 'No agent run found.' }
        $Folder = $latest.FullName
    }
    $resolved = Resolve-ExistingPath $Folder
    Write-Output $resolved
    return $resolved
}

function Write-Status {
    $launcher = Get-CodexLauncherText
    $cache = if (Test-Path -LiteralPath $CanaryCache) { Get-Content -LiteralPath $CanaryCache -Raw | ConvertFrom-Json } else { $null }

    $statusText = if ($cache -and ($cache.PSObject.Properties.Name -contains 'status')) { $cache.status } else { 'not_run' }
    $timeText = if ($cache -and ($cache.PSObject.Properties.Name -contains 'timestamp_utc')) { $cache.timestamp_utc } else { 'none' }
    $passText = if ($cache -and ($cache.PSObject.Properties.Name -contains 'latest_pass_utc') -and $cache.latest_pass_utc) { $cache.latest_pass_utc } else { 'none' }
    $unattendedEnabled = if ($cache -and ($cache.PSObject.Properties.Name -contains 'status') -and $cache.status -eq 'AGENT_CANARY_PASSED') { 'yes' } else { 'no' }

    $lines = @(
        'Windows Agent Orchestrator Status',
        '---------------------------------',
        "Selected launcher: $launcher",
        "Canary cache (latest attempt): $statusText",
        "Canary timestamp: $timeText",
        "Canary latest pass: $passText",
        "Unattended Codex execution enabled: $unattendedEnabled"
    )
    Write-Output ($lines -join "`n")
}

try {
    Ensure-Dir $AutoRoot
    Ensure-Dir $ReportsRoot
    Ensure-Dir $ScratchRoot
    switch ($Command) {
        'Status' { Write-Status }
        'Canary' {
            $run = Run-Canary
            $status = (Get-Content -LiteralPath (Join-Path $run 'status.txt') -Raw).Trim()
            Write-Output "$status`: $run"
        }
        'Import' { Run-Import $RunFolder | Out-Host }
        default {
            $run = Run-Agent
            $status = (Get-Content -LiteralPath (Join-Path $run 'status.txt') -Raw).Trim()
            Write-Output $status
            Write-Output $run
            Write-Output (Join-Path $run 'final_report.md')
            if (-not $DryRun -and $status -eq 'CODEX_RUNNING') {
                throw 'Agent run returned while still CODEX_RUNNING.'
            }
        }
    }
}
catch {
    $message = $_.Exception.Message
    if ($script:ActiveRun -and (Test-Path -LiteralPath $script:ActiveRun)) {
        try { Ensure-CodexArtifacts $script:ActiveRun $null $message } catch {}
        try { Write-Text (Join-Path $script:ActiveRun 'status.txt') "AGENT_INTERRUPTED`n" } catch {}
        try { Write-RunSummary $script:ActiveRun 'AGENT_INTERRUPTED' 'agent' $message @() @() 'Inspect run artifacts before retrying.' } catch {}
        Write-Output $script:ActiveRun
        Write-Output (Join-Path $script:ActiveRun 'final_report.md')
    }
    Write-Error $message
    exit 1
}
