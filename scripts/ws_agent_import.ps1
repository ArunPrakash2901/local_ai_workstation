param(
    [string]$RunFolder = ''
)

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $ScriptRoot 'ws_agent_run.ps1') -Command Import -RunFolder $RunFolder
