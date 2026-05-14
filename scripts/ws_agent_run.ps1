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
    [string]$Context = '8192'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WSHome = Join-Path (Split-Path -Parent $ScriptRoot) '.'
$WSHome = Resolve-Path (Join-Path $ScriptRoot '..') | Select-Object -ExpandProperty Path
$AutoRoot = Join-Path $WSHome 'auto_runs'
$ReportsRoot = Join-Path $WSHome 'reports'
$ScratchRoot = Join-Path $WSHome 'scratch'
$ProjectsYaml = Join-Path $WSHome 'registry\projects.yaml'
$CanaryCache = Join-Path $ReportsRoot 'agent_canary_status.json'
$CodexCanaryScratch = Join-Path $ScratchRoot 'agent_canary.md'
$KnownDocs = @('START_HERE.md', 'WORKSTATION_MANUAL.md', 'LOCAL_AI_STACK_STATUS.md', 'FINAL_RECOMMENDED_PROFILE.md', 'README.md')

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

function Convert-ToWslPath([string]$Path) {
    $p = $Path -replace '\\', '/'
    if ($p -match '^([A-Za-z]):/(.*)$') {
        return "/mnt/$($Matches[1].ToLower())/$($Matches[2])"
    }
    return $p
}

function Normalize-Path([string]$Path) {
    $candidate = $Path
    if ($candidate -match '^/mnt/([a-z])/(.*)$') {
        $candidate = "$($Matches[1].ToUpper()):\" + ($Matches[2] -replace '/', '\')
    }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Invoke-Process {
    param(
        [string]$FileName,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$StdInText = '',
        [int]$TimeoutSeconds = 60,
        [string]$Run,
        [string]$Label = 'command'
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FileName
    $psi.Arguments = $Arguments
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    if ($StdInText) {
        $psi.RedirectStandardInput = $true
    }

    $proc = [System.Diagnostics.Process]::new()
    $proc.StartInfo = $psi
    [void]$proc.Start()

    if ($StdInText) {
        $proc.StandardInput.Write($StdInText)
        $proc.StandardInput.Close()
    }

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
            try { $proc.Kill() } catch {}
            try {
                if (-not $proc.HasExited) {
                    cmd.exe /c "taskkill /F /T /PID $($proc.Id) >nul 2>&1" | Out-Null
                }
            } catch {}
            break
        }
    }

    try { $proc.WaitForExit(5000) | Out-Null } catch {}
    $stdout = ''
    $stderr = ''
    try { $stdout = $proc.StandardOutput.ReadToEnd() } catch {}
    try { $stderr = $proc.StandardError.ReadToEnd() } catch {}
    if ($Run) { Heartbeat $Run "$Label completed rc=$($proc.ExitCode)" }
    return [pscustomobject]@{
        ExitCode = $proc.ExitCode
        StdOut = $stdout.Trim()
        StdErr = $stderr.Trim()
        TimedOut = $timedOut
    }
}

function Load-ProjectMeta([string]$Key) {
    if (-not (Test-Path -LiteralPath $ProjectsYaml)) {
        throw "Missing registry: $ProjectsYaml"
    }
    $text = Get-Content -LiteralPath $ProjectsYaml -Raw
    $pattern = "(?ms)^\s{2}$([Regex]::Escape($Key)):\s*$\r?\n(?<block>(?:^\s{4}.*\r?\n?)*)"
    $m = [Regex]::Match($text, $pattern)
    if (-not $m.Success) {
        throw "Project key not found: $Key"
    }
    $block = $m.Groups['block'].Value
    $meta = [ordered]@{
        project_key = $Key
        display_name = $Key
        windows_path = ''
        wsl_path = ''
        graph_path = ''
        project_type = 'unknown'
        priority = 'unknown'
        safe_to_modify = $false
        status = 'unknown'
        notes = ''
    }
    foreach ($line in $block -split "\r?\n") {
        if ($line -notmatch '^\s{4}([^:]+):\s*(.*)$') { continue }
        $k = $Matches[1].Trim()
        $v = $Matches[2].Trim().Trim('"')
        if ($meta.Contains($k)) { $meta[$k] = $v }
        elseif ($k -eq 'safe_to_modify') { $meta['safe_to_modify'] = $v -match 'true' }
    }
    if (-not $meta['wsl_path']) {
        throw "Project path missing for $Key"
    }
    $meta['wsl_path'] = Convert-ToWslPath $meta['wsl_path']
    return [pscustomobject]$meta
}

function Parse-Task([string]$TaskPath, [string]$DefaultProject) {
    $text = Get-Content -LiteralPath $TaskPath -Raw
    $titleMatch = [Regex]::Match($text, '(?im)^#{1,6}\s*Task\s+(\d+)\s*[:\-]\s*(.+)$')
    $num = if ($titleMatch.Success) { [int]$titleMatch.Groups[1].Value } else { 1 }
    $title = if ($titleMatch.Success) { $titleMatch.Groups[2].Value.Trim() } else { [IO.Path]::GetFileNameWithoutExtension($TaskPath) }

    function Get-Section([string]$Name) {
        $pat = "(?ms)^\s*$([Regex]::Escape($Name)):\s*$\r?\n(?<body>.*?)(?=^\s*[A-Za-z][A-Za-z ]*:\s*$|^#{1,6}\s*Task\s+\d+|\z)"
        $m = [Regex]::Match($text, $pat)
        if ($m.Success) { return $m.Groups['body'].Value.Trim() }
        return ''
    }

    $allowed = @()
    foreach ($line in (Get-Section 'Allowed Files') -split "\r?\n") {
        $v = ($line.Trim() -replace '^-+\s*', '').Trim()
        if ($v -and $v -ne 'not specified') { $allowed += $v }
    }
    if (-not $allowed.Count) {
        foreach ($doc in $KnownDocs) {
            if ($text -like "*$doc*") { $allowed += $doc }
        }
    }
    $denied = @()
    foreach ($line in (Get-Section 'Denied Files') -split "\r?\n") {
        $v = ($line.Trim() -replace '^-+\s*', '').Trim()
        if ($v -and $v -ne 'not specified') { $denied += $v }
    }
    $acceptance = @()
    foreach ($line in (Get-Section 'Acceptance Criteria') -split "\r?\n") {
        $v = ($line.Trim() -replace '^-+\s*', '').Trim()
        if ($v) { $acceptance += $v }
    }
    $source = Get-Section 'Source'
    if (-not $source) { $source = 'manual' }
    $project = Get-Section 'Project'
    if (-not $project) { $project = $DefaultProject }
    $status = Get-Section 'Status'
    if (-not $status) { $status = 'inbox' }
    $risk = Get-Section 'Risk'
    if (-not $risk) { $risk = 'needs_review' }
    $escalation = Get-Section 'Escalation'
    if (-not $escalation) { $escalation = 'none' }
    return [pscustomobject]@{
        TaskNum = $num
        Title = $title
        Source = $source
        Project = $project
        Status = $status
        Goal = (Get-Section 'Goal')
        Acceptance = $acceptance
        Allowed = $allowed
        Denied = $denied
        TestCommand = (Get-Section 'Test Command')
        Risk = $risk
        Escalation = $escalation
        Notes = (Get-Section 'Notes')
        Body = $text
    }
}

function Get-Route([psobject]$Task, [string[]]$Allowed) {
    $text = $Task.Body
    if ($text -match '(?i)\b(secret|credential|token|password|model file|raw dataset|parquet|sqlite|duckdb)\b') {
        return 'restricted'
    }
    if (($Task.Title -match '(?i)\b(refactor|architecture|large|ambiguous)\b') -or ($Allowed.Count -eq 0)) {
        return 'handoff'
    }
    if ($Allowed | Where-Object { $_ -match '\.md$|\.txt$|\.rst$' }) { return 'docs' }
    return 'code'
}

function Get-CanaryCache {
    if (-not (Test-Path -LiteralPath $CanaryCache)) {
        return $null
    }
    try { return Get-Content -LiteralPath $CanaryCache -Raw | ConvertFrom-Json } catch { return $null }
}

function Save-CanaryCache([string]$Status, [string]$RunFolder, [string]$Notes) {
    $payload = [ordered]@{
        status = $Status
        timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
        run_folder = $RunFolder
        notes = $Notes
    }
    Write-Text $CanaryCache ($payload | ConvertTo-Json -Depth 5)
}

function New-RunFolder([string]$ProjectKey, [psobject]$Task, [string]$Suffix) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $slug = ($Task.Title -replace '[^A-Za-z0-9]+', '_' ).Trim('_').ToLower()
    if (-not $slug) { $slug = 'task' }
    return Join-Path $AutoRoot "$stamp`_$ProjectKey`_$($Task.TaskNum.ToString('000'))`_$slug`_$Suffix"
}

function Get-LatestRun([string]$Pattern = '*agent*') {
    if (-not (Test-Path -LiteralPath $AutoRoot)) { return $null }
    $dirs = Get-ChildItem -LiteralPath $AutoRoot -Directory | Where-Object { $_.Name -like $Pattern }
    if (-not $dirs) { return $null }
    return ($dirs | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}

function Get-GitStatus([string]$RepoPath) {
    $res = Invoke-Process -FileName 'git' -Arguments "-C `"$RepoPath`" status --short --branch" -WorkingDirectory $RepoPath -TimeoutSeconds 30
    return $res.StdOut
}

function Write-RunSummary([string]$Run, [string]$Status, [string]$ModeLabel, [string]$Notes, [string[]]$Changed, [string[]]$Unsafe, [string]$Tests, [string]$Recommendation, [string]$ManualInstruction) {
    $lines = @(
        '# Windows Agent Orchestrator Report',
        '',
        '## Summary',
        "- Status: $Status",
        "- Mode: $ModeLabel",
        "- Notes: $Notes",
        "- Recommended Next Action: $Recommendation",
        '',
        '## Changed Files'
    )
    if ($Changed.Count) { $lines += $Changed | ForEach-Object { "- $_" } } else { $lines += '- none' }
    $lines += ''
    $lines += '## Unsafe Files'
    if ($Unsafe.Count) { $lines += $Unsafe | ForEach-Object { "- $_" } } else { $lines += '- none' }
    $lines += ''
    $lines += '## Tests'
    $lines += $(if ($Tests) { $Tests } else { 'No tests run.' })
    $lines += ''
    $lines += '## Manual Instruction'
    $lines += $(if ($ManualInstruction) { $ManualInstruction } else { 'none' })
    $lines += ''
    Write-Text (Join-Path $Run 'final_report.md') ($lines -join "`n")
}

function Run-Canary {
    Ensure-Dir $AutoRoot
    Ensure-Dir $ScratchRoot
    $run = Join-Path $AutoRoot ("{0}_agent_canary" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    Ensure-Dir $run
    Write-Text (Join-Path $run 'status.txt') "STARTED`n"
    Heartbeat $run 'agent canary started'

    $baseline = "# Agent Canary`n`nBASELINE $(Get-Date).`n"
    Write-Text $CodexCanaryScratch $baseline
    Write-Text (Join-Path $run 'scratch_before.md') $baseline

    $prompt = @"
# Agent Canary Work Order

Modify only `scratch/agent_canary.md`.
Add one line containing `AGENT_CANARY_OK` and the current timestamp.
Do not modify any other file.
Stop after editing.
"@
    $workOrder = Join-Path $run 'agent_canary_work_order.md'
    Write-Text $workOrder $prompt
    Write-Text (Join-Path $run 'codex_prompt.md') $prompt

    $codex = Get-Command codex -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $codex) {
        Write-Text (Join-Path $run 'status.txt') "AGENT_CANARY_FAILED`n"
        Save-CanaryCache 'FAIL' $run 'codex command not found'
        Write-RunSummary $run 'AGENT_CANARY_FAILED' 'canary' 'codex command not found' @() @() 'No tests run.' 'handoff' 'Open Windows Terminal and run codex login or repair Codex.' 
        return $run
    }

    $repo = Join-Path $WSHome '.'
    $promptText = Get-Content -LiteralPath $workOrder -Raw
    $codexArgs = @('exec','--skip-git-repo-check','--ignore-user-config','--ephemeral','--dangerously-bypass-approvals-and-sandbox','--sandbox','danger-full-access','-C',$WSHome,'--output-last-message',(Join-Path $run 'codex_response.md'),'-')
    $argLine = ($codexArgs | ForEach-Object {
        if ($_ -match '\s|\"') { '"' + ($_ -replace '"','\"') + '"' } else { $_ }
    }) -join ' '
    $result = Invoke-Process -FileName 'cmd.exe' -Arguments "/c $($codex.Source) $argLine" -WorkingDirectory $WSHome -StdInText $promptText -TimeoutSeconds 180 -Run $run -Label 'codex canary'
    Write-Text (Join-Path $run 'codex_stdout.md') $result.StdOut
    Write-Text (Join-Path $run 'codex_stderr.md') $result.StdErr
    Write-Text (Join-Path $run 'codex_exit_code.txt') ([string]$result.ExitCode)

    $final = Get-Content -LiteralPath $CodexCanaryScratch -Raw -ErrorAction SilentlyContinue
    $passed = $false
    $status = 'AGENT_CANARY_FAILED'
    $notes = 'canary did not complete'
    if ($result.TimedOut) {
        $status = 'AGENT_CANARY_TIMEOUT'
        $notes = 'Codex exceeded timeout'
    }
    elseif ($result.ExitCode -ne 0) {
        $combo = ($result.StdOut + "`n" + $result.StdErr).ToLowerInvariant()
        if ($combo -match '401 unauthorized|missing bearer|authentication|required') {
            $status = 'AGENT_CANARY_AUTH_REQUIRED'
            $notes = 'Codex authentication required'
        }
        elseif ($combo -match 'interactive|stdin|tty|terminal') {
            $status = 'AGENT_CANARY_INTERACTIVE_REQUIRED'
            $notes = 'Codex requested interactive input'
        }
    }
    elseif ($final -match 'AGENT_CANARY_OK') {
        $passed = $true
        $status = 'AGENT_CANARY_PASSED'
        $notes = 'Codex edited the scratch canary successfully'
    }
    else {
        $status = 'AGENT_CANARY_FAILED'
        $notes = 'Canary file did not change as expected'
    }

    Write-Text (Join-Path $run 'status.txt') "$status`n"
    $cacheStatus = 'FAIL'
    if ($status -eq 'AGENT_CANARY_PASSED') { $cacheStatus = 'PASS' }
    $changedFiles = @()
    if ($passed) { $changedFiles = @('scratch/agent_canary.md') }
    $modeLabel = 'handoff'
    if ($passed) { $modeLabel = 'codex' }
    Save-CanaryCache $cacheStatus $run $notes
    Write-RunSummary $run $status 'canary' $notes $changedFiles @() 'No tests run.' $modeLabel 'Use ws agent-run or ws agent-handoff workflow.'
    return $run
}

function Build-WorkOrder([string]$RepoPath, [string]$Run, [psobject]$Project, [psobject]$Task, [string[]]$Allowed, [string]$Route, [string]$BranchName, [string]$TestCommand) {
    $taskBlock = @(
        '# Work Order',
        '',
        '## Project',
        $Project.project_key,
        '',
        '## Task',
        $Task.Body.Trim(),
        '',
        '## Route',
        $Route,
        '',
        '## Branch',
        ($(if ($BranchName) { $BranchName } else { 'none' })),
        '',
        '## Allowed Files'
    )
    if ($Allowed.Count) { $taskBlock += $Allowed | ForEach-Object { "- $_" } } else { $taskBlock += '- not specified' }
    $taskBlock += ''
    $taskBlock += '## Denied Files'
    if ($Task.Denied.Count) { $taskBlock += $Task.Denied | ForEach-Object { "- $_" } } else { $taskBlock += '- none' }
    $taskBlock += ''
    $taskBlock += '## Acceptance Criteria'
    if ($Task.Acceptance.Count) { $taskBlock += $Task.Acceptance | ForEach-Object { "- $_" } } else { $taskBlock += '- not specified' }
    $taskBlock += ''
    $taskBlock += '## Working Rules'
    $taskBlock += '- Modify only allowed files.'
    $taskBlock += '- Make the smallest change that satisfies the acceptance criteria.'
    $taskBlock += '- Do not delete files.'
    $taskBlock += '- Do not touch secrets, credentials, tokens, raw datasets, or model files.'
    $taskBlock += '- Do not install packages.'
    $taskBlock += '- Do not commit.'
    $taskBlock += '- Do not push.'
    $taskBlock += '- Stop after edits.'
    if ($TestCommand) {
        $taskBlock += ''
        $taskBlock += '## Test Command'
        $taskBlock += $TestCommand
    }
    $taskBlock += ''
    $taskBlock += '## Exact Instruction'
    $taskBlock += 'Modify only the allowed files. If you cannot produce a safe edit, return NO_PATCH.'
    return ($taskBlock -join "`n") + "`n"
}

function Snapshot-Baseline([string]$RepoPath, [string]$Run, [string[]]$Paths) {
    $baselineDir = Join-Path $Run 'baseline'
    Ensure-Dir $baselineDir
    $manifest = @()
    foreach ($rel in ($Paths | Sort-Object -Unique)) {
        $norm = $rel -replace '\\','/'
        $full = Join-Path $RepoPath $norm
        try { $resolved = Resolve-Path -LiteralPath $full -ErrorAction Stop } catch { $resolved = $null }
        if ($resolved -and (Test-Path -LiteralPath $resolved.Path -PathType Leaf)) {
            $content = Get-Content -LiteralPath $resolved.Path -Raw
            $snapPath = Join-Path $baselineDir $norm
            Ensure-Dir (Split-Path -Parent $snapPath)
            Write-Text $snapPath $content
            $manifest += [ordered]@{ path = $norm; exists = $true; snapshot = ($norm -replace '\\','/'); size = ([IO.FileInfo]$resolved.Path).Length }
        } else {
            $manifest += [ordered]@{ path = $norm; exists = $false; snapshot = ''; size = 0 }
        }
    }
    Write-Text (Join-Path $Run 'baseline_manifest.json') ($manifest | ConvertTo-Json -Depth 6)
    Write-Text (Join-Path $Run 'baseline_paths.json') (($Paths | Sort-Object -Unique) | ConvertTo-Json -Depth 3)
}

function Get-AllowedFilesFromTask([psobject]$Task) {
    if ($Task.Allowed.Count) { return $Task.Allowed }
    return @($KnownDocs | Where-Object { $Task.Body -like "*$_*" })
}

function Run-Import([string]$RunFolderArg) {
    $run = $RunFolderArg
    if (-not $run -or $run -eq 'latest') {
        $latest = Get-LatestRun '*codex_handoff*'
        if (-not $latest) { $latest = Get-LatestRun '*agent*' }
        $run = $latest
    }
    if (-not $run -or -not (Test-Path -LiteralPath $run)) {
        throw "No agent run found."
    }

    $taskPath = Join-Path $run 'task.md'
    if (-not (Test-Path -LiteralPath $taskPath)) { throw "Missing task.md in $run" }
    $task = Parse-Task $taskPath 'workstation_control_plane'
    $project = Load-ProjectMeta $task.Project
    $repo = Normalize-Path $project.wsl_path
    $allowed = Get-AllowedFilesFromTask $task
    if (-not $allowed.Count) { throw 'Task allowlist missing.' }

    $beforeStatus = Invoke-Process -FileName 'git' -Arguments "-C `"$repo`" status --short --branch" -WorkingDirectory $repo -TimeoutSeconds 30 -Run $run -Label 'git status before'
    Write-Text (Join-Path $run 'git_status_before.md') ($beforeStatus.StdOut + "`n")

    $porcelain = (Invoke-Process -FileName 'git' -Arguments "-C `"$repo`" status --porcelain" -WorkingDirectory $repo -TimeoutSeconds 30 -Run $run -Label 'git porcelain').StdOut
    $changed = @()
    $unsafe = @()
    foreach ($line in ($porcelain -split "`r?`n")) {
        if (-not $line.Trim()) { continue }
        if ($line.StartsWith('?? ')) {
            $path = $line.Substring(3).Trim()
        } else {
            $parts = $line -split '\s+', 2
            $path = if ($parts.Count -gt 1) { $parts[1].Trim() } else { $line.Trim() }
            if ($path -match ' -> ') { $path = ($path -split ' -> ', 2)[1].Trim() }
        }
        if ($allowed -contains $path) { $changed += $path } else { $unsafe += $path }
    }

    if ($unsafe.Count) {
        try {
            $restore = $unsafe | Where-Object { $_ -and -not $_.StartsWith('?? ') }
            if ($restore.Count) {
                Invoke-Process -FileName 'git' -Arguments ("-C `"$repo`" restore --worktree --staged -- " + ($restore -join ' ')) -WorkingDirectory $repo -TimeoutSeconds 120 -Run $run -Label 'restore unsafe'
            }
        } catch {}
        Write-Text (Join-Path $run 'git_status_after.md') ((Get-GitStatus $repo) + "`n")
        Write-Text (Join-Path $run 'changed_files.txt') (($changed -join "`n") + ($(if ($changed.Count) { "`n" } else { "" })))
        Write-Text (Join-Path $run 'unsafe_files.txt') (($unsafe -join "`n") + ($(if ($unsafe.Count) { "`n" } else { "" })))
        Write-Text (Join-Path $run 'final_diff.patch') ''
        Write-Text (Join-Path $run 'status.txt') "SAFETY_BLOCKED`n"
        Write-RunSummary $run 'SAFETY_BLOCKED' 'import' 'Unsafe files detected during import and were reverted.' $changed $unsafe 'No tests run.' 'review' 'Review allowlist and manual Codex output.'
        return $run
    }

    $afterStatus = Invoke-Process -FileName 'git' -Arguments "-C `"$repo`" status --short --branch" -WorkingDirectory $repo -TimeoutSeconds 30 -Run $run -Label 'git status after'
    Write-Text (Join-Path $run 'git_status_after.md') ($afterStatus.StdOut + "`n")
    Write-Text (Join-Path $run 'changed_files.txt') (($changed -join "`n") + ($(if ($changed.Count) { "`n" } else { "" })))
    Write-Text (Join-Path $run 'unsafe_files.txt') (($unsafe -join "`n") + ($(if ($unsafe.Count) { "`n" } else { "" })))

    if (-not $changed.Count) {
        Write-Text (Join-Path $run 'status.txt') "CODEX_NO_CHANGES`n"
        Write-Text (Join-Path $run 'final_diff.patch') ''
        Write-RunSummary $run 'CODEX_NO_CHANGES' 'import' 'No file changes detected.' @() @() 'No tests run.' 'review' 'No changes to import.'
        return $run
    }

    $diffArgs = @('-C', $repo, 'diff', '--')
    $diffArgs += $changed
    $diffProc = Invoke-Process -FileName 'git' -Arguments (($diffArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ') -WorkingDirectory $repo -TimeoutSeconds 120 -Run $run -Label 'git diff'
    Write-Text (Join-Path $run 'final_diff.patch') ($diffProc.StdOut + "`n")

    $testCommand = if ($Tests) { $Tests } else { $task.TestCommand }
    $testsText = if ($testCommand) { "Test command present but import path does not run tests automatically." } else { 'No test command found.' }
    $status = 'NEEDS_USER_REVIEW'
    Write-Text (Join-Path $run 'status.txt') "$status`n"
    Write-RunSummary $run $status 'import' 'Imported allowed changes.' $changed $unsafe $testsText 'review' 'Inspect final_diff.patch and review manually.'
    return $run
}

function Run-Agent {
    if (-not $ProjectKey -or -not $TaskFile) { throw 'Project key and task file are required.' }
    $project = Load-ProjectMeta $ProjectKey
    $repo = Normalize-Path $project.wsl_path
    if (-not (Test-Path -LiteralPath $repo)) { throw "Project path not found: $repo" }
    $taskPath = Normalize-Path $TaskFile
    if (-not (Test-Path -LiteralPath $taskPath)) { throw "Task file not found: $taskPath" }

    $task = Parse-Task $taskPath $ProjectKey
    $allowed = Get-AllowedFilesFromTask $task
    if (-not $allowed.Count) { throw 'Task allowlist missing. Add Allowed Files or explicit docs references.' }
    $route = Get-Route $task $allowed
    if ($route -eq 'restricted') {
        $run = New-RunFolder $ProjectKey $task 'agent_restricted'
        Ensure-Dir $run
        Write-Text (Join-Path $run 'status.txt') "SAFETY_BLOCKED`n"
        Write-RunSummary $run 'SAFETY_BLOCKED' 'restricted' 'Task references restricted files.' @() @() 'No tests run.' 'review' 'Update the task spec.'
        return $run
    }

    $run = New-RunFolder $ProjectKey $task 'agent_run'
    Ensure-Dir $run
    Heartbeat $run 'agent run started'
    Write-Text (Join-Path $run 'task.md') (Get-Content -LiteralPath $taskPath -Raw)
    Write-Text (Join-Path $run 'status.txt') "STARTED`n"
    $branchName = ''
    if ($Branch) {
        $branchName = "agent/$ProjectKey/$($task.TaskNum.ToString('000'))-$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        $branchProc = Invoke-Process -FileName 'git' -Arguments "-C `"$repo`" checkout -B $branchName" -WorkingDirectory $repo -TimeoutSeconds 60 -Run $run -Label 'git branch create'
        Write-Text (Join-Path $run 'branch_create.log') (($branchProc.StdOut + "`n" + $branchProc.StdErr).Trim() + "`n")
    }

    $before = Get-GitStatus $repo
    Write-Text (Join-Path $run 'git_status_before.md') ($before + "`n")
    $baseline = @($allowed)
    Snapshot-Baseline $repo $run $baseline

    $canary = Get-CanaryCache
    $canaryPass = $false
    if ($canary -and $canary.status -eq 'AGENT_CANARY_PASSED') { $canaryPass = $true }

    $routeMode = $Mode
    if ($Mode -eq 'detect') {
        $routeMode = if ($canaryPass) { 'codex' } else { 'handoff' }
    }

    $testCommand = if ($Tests) { $Tests } else { $task.TestCommand }
    $workOrder = Build-WorkOrder $repo $run $project $task $allowed $route $branchName $testCommand
    $workOrderPath = Join-Path $run 'codex_work_order.md'
    Write-Text $workOrderPath $workOrder
    Write-Text (Join-Path $run 'codex_prompt.md') $workOrder

    if ($DryRun) {
        Write-Text (Join-Path $run 'status.txt') "PLAN_ONLY`n"
        Write-RunSummary $run 'PLAN_ONLY' $routeMode 'Dry run completed.' @() @() 'No tests run.' 'review' 'Review work order only.'
        return $run
    }

    if ($routeMode -eq 'local') {
        Write-Text (Join-Path $run 'local_plan.md') @"
# Local Plan

- Project: $ProjectKey
- Task: $($task.Title)
- Route: local
- Goal: $($task.Goal)
"@
        Write-Text (Join-Path $run 'status.txt') "PLAN_ONLY`n"
        Write-RunSummary $run 'PLAN_ONLY' 'local' 'Local planning only.' @() @() 'No tests run.' 'review' 'Use plan-only output.'
        return $run
    }

    if (-not $canaryPass -or $routeMode -eq 'handoff') {
        $clipboardOk = $false
        try { Set-Clipboard -Value $workOrder; $clipboardOk = $true } catch {}
        Write-Text (Join-Path $run 'clipboard_status.md') ("# Clipboard Status`n`n- Copied: " + ($(if ($clipboardOk) { 'yes' } else { 'no' })) + "`n")
        Write-Text (Join-Path $run 'status.txt') "CODEX_HANDOFF_READY`n"
        Write-RunSummary $run 'CODEX_HANDOFF_READY' 'handoff' 'Manual Codex handoff required.' @() @() 'No tests run.' 'handoff' 'Run the work order in Windows Codex, then use ws agent-import latest.'
        return $run
    }

    $codex = Get-Command codex -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $codex) {
        Write-Text (Join-Path $run 'status.txt') "CODEX_UNAVAILABLE`n"
        Write-RunSummary $run 'CODEX_UNAVAILABLE' 'codex' 'Codex command not found.' @() @() 'No tests run.' 'handoff' 'Use handoff mode.'
        return $run
    }

    Write-Text (Join-Path $run 'status.txt') "CODEX_RUNNING`n"
    $promptText = $workOrder
    $responsePath = Join-Path $run 'codex_response.md'
    $codexArgs = @('exec','--skip-git-repo-check','--ignore-user-config','--ephemeral','--dangerously-bypass-approvals-and-sandbox','--sandbox','danger-full-access','-C',$repo,'--output-last-message',$responsePath,'-')
    $argLine = ($codexArgs | ForEach-Object { if ($_ -match '\s|\"') { '"' + ($_ -replace '"','\"') + '"' } else { $_ } }) -join ' '
    $result = Invoke-Process -FileName 'cmd.exe' -Arguments "/c $($codex.Source) $argLine" -WorkingDirectory $repo -StdInText $promptText -TimeoutSeconds ($MaxMinutes * 60) -Run $run -Label 'codex run'
    Write-Text (Join-Path $run 'codex_stdout.md') $result.StdOut
    Write-Text (Join-Path $run 'codex_stderr.md') $result.StdErr
    Write-Text (Join-Path $run 'codex_exit_code.txt') ([string]$result.ExitCode)

    if ($result.TimedOut) {
        Write-Text (Join-Path $run 'status.txt') "CODEX_TIMEOUT`n"
        Write-RunSummary $run 'CODEX_TIMEOUT' 'codex' 'Codex exceeded timeout.' @() @() 'No tests run.' 'review' 'Retry with longer timeout or handoff.'
        return $run
    }

    $combo = ($result.StdOut + "`n" + $result.StdErr).ToLowerInvariant()
    if ($result.ExitCode -ne 0) {
        if ($combo -match '401 unauthorized|missing bearer|authentication') {
            Write-Text (Join-Path $run 'status.txt') "CODEX_AUTH_REQUIRED`n"
            Write-RunSummary $run 'CODEX_AUTH_REQUIRED' 'codex' 'Codex authentication required.' @() @() 'No tests run.' 'handoff' 'Open Windows Terminal and run codex login.'
            return $run
        }
        if ($combo -match 'interactive|stdin|tty|terminal') {
            Write-Text (Join-Path $run 'status.txt') "CODEX_INTERACTIVE_REQUIRED`n"
            Write-RunSummary $run 'CODEX_INTERACTIVE_REQUIRED' 'codex' 'Codex requested interactive input.' @() @() 'No tests run.' 'handoff' 'Use ws agent-import after manual Codex.'
            return $run
        }
        Write-Text (Join-Path $run 'status.txt') "FAILED_INTERNAL`n"
        Write-RunSummary $run 'FAILED_INTERNAL' 'codex' 'Codex exited non-zero.' @() @() 'No tests run.' 'handoff' 'Inspect codex_stdout.md and codex_stderr.md.'
        return $run
    }

    $beforeStatus = Get-GitStatus $repo
    $afterPorcelain = (Invoke-Process -FileName 'git' -Arguments "-C `"$repo`" status --porcelain" -WorkingDirectory $repo -TimeoutSeconds 30 -Run $run -Label 'git porcelain').StdOut
    $changed = @()
    $unsafe = @()
    foreach ($line in ($afterPorcelain -split "`r?`n")) {
        if (-not $line.Trim()) { continue }
        if ($line.StartsWith('?? ')) {
            $path = $line.Substring(3).Trim()
        } else {
            $parts = $line -split '\s+', 2
            $path = if ($parts.Count -gt 1) { $parts[1].Trim() } else { $line.Trim() }
            if ($path -match ' -> ') { $path = ($path -split ' -> ', 2)[1].Trim() }
        }
        if ($allowed -contains $path) { $changed += $path } else { $unsafe += $path }
    }

    Write-Text (Join-Path $run 'git_status_after.md') ((Get-GitStatus $repo) + "`n")
    Write-Text (Join-Path $run 'changed_files.txt') (($changed -join "`n") + ($(if ($changed.Count) { "`n" } else { "" })))
    Write-Text (Join-Path $run 'unsafe_files.txt') (($unsafe -join "`n") + ($(if ($unsafe.Count) { "`n" } else { "" })))

    if ($unsafe.Count) {
        try {
            $restore = @()
            foreach ($u in $unsafe) {
                if (-not ($u.StartsWith('??'))) { $restore += $u }
            }
            if ($restore.Count) {
                Invoke-Process -FileName 'git' -Arguments ("-C `"$repo`" restore --worktree --staged -- " + ($restore -join ' ')) -WorkingDirectory $repo -TimeoutSeconds 120 -Run $run -Label 'restore unsafe'
            }
        } catch {}
        Write-Text (Join-Path $run 'status.txt') "SAFETY_BLOCKED`n"
        Write-Text (Join-Path $run 'final_diff.patch') ''
        Write-RunSummary $run 'SAFETY_BLOCKED' 'codex' 'Unsafe files detected and reverted.' $changed $unsafe 'No tests run.' 'review' 'Review allowlist and workspace state.'
        return $run
    }

    if (-not $changed.Count) {
        Write-Text (Join-Path $run 'status.txt') "CODEX_NO_CHANGES`n"
        Write-Text (Join-Path $run 'final_diff.patch') ''
        Write-RunSummary $run 'CODEX_NO_CHANGES' 'codex' 'Codex made no file changes.' @() @() 'No tests run.' 'review' 'If Codex was supposed to edit files, rerun with a clearer work order.'
        return $run
    }

    $diff = ''
    foreach ($rel in $changed) {
        $diff += "--- a/$rel`n+++ b/$rel`n"
    }
    Write-Text (Join-Path $run 'final_diff.patch') $diff

    $testsText = ''
    $testsPassed = $false
    if ($testCommand) {
        $testsText = "No automated test runner is wired in this minimal agent path."
    } else {
        $testsText = 'No test command found.'
    }

    $status = if ($testCommand) { 'NEEDS_USER_REVIEW' } else { 'NEEDS_USER_REVIEW' }
    Write-Text (Join-Path $run 'status.txt') "$status`n"
    Write-RunSummary $run $status 'codex' 'Codex completed and diff validated.' $changed @() $testsText 'review' 'Review diff and mark task complete or blocked.'
    return $run
}

try {
    Ensure-Dir $AutoRoot
    Ensure-Dir $ReportsRoot
    Ensure-Dir $ScratchRoot
    switch ($Command) {
        'Status' {
            $cache = Get-CanaryCache
            $codexExists = $false
            try { $codexExists = [bool](Get-Command codex -ErrorAction SilentlyContinue) } catch {}
            $recommended = 'handoff'
            $canaryStatus = 'not_run'
            $authStatus = 'unknown'
            if ($cache) {
                $canaryStatus = $cache.status
                if ($cache.status -eq 'AGENT_CANARY_PASSED') { $recommended = 'codex' }
                elseif ($cache.status -eq 'AGENT_CANARY_AUTH_REQUIRED') { $authStatus = 'no' }
                elseif ($cache.status -eq 'AGENT_CANARY_PASSED') { $authStatus = 'yes' }
            }
            $lines = @(
                'Windows Agent Orchestrator Status',
                '---------------------------------',
                "Codex command exists: " + ($(if ($codexExists) { 'yes' } else { 'no' })),
                "CLI auth appears available: $authStatus",
                "Recommended mode: $recommended",
                "Canary cache: $canaryStatus"
            )
            if ($cache) {
                $lines += "Canary timestamp: $($cache.timestamp_utc)"
                $lines += "Canary run: $($cache.run_folder)"
            }
            Write-Output ($lines -join "`n")
            break
        }
        'Canary' {
            $run = Run-Canary
            Write-Output ("{0}: {1}" -f (Get-Content -LiteralPath (Join-Path $run 'status.txt') -Raw).Trim(), $run)
            break
        }
        'Import' {
            $run = Run-Import $RunFolder
            Write-Output ((Get-Content -LiteralPath (Join-Path $run 'status.txt') -Raw).Trim())
            Write-Output $run
            break
        }
        default {
            $run = Run-Agent
            Write-Output ((Get-Content -LiteralPath (Join-Path $run 'status.txt') -Raw).Trim())
            Write-Output $run
            break
        }
    }
}
catch {
    $msg = $_.Exception.Message
    Write-Error $msg
    exit 1
}
