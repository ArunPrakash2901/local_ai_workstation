param(
    [Parameter(ValueFromRemainingArguments = $true)]
    $RemainingArgs
)

# AI Workstation Unified Command (PowerShell Wrapper)
# This script allows calling the 'ws' bash script from native PowerShell.
# It delegates execution to WSL using an absolute path.

$ErrorActionPreference = 'Stop'

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WSHome = (Resolve-Path (Join-Path $ScriptRoot '..')).Path

# Convert WSHome to WSL path
$WSL_HOME = try {
    $p = wsl wslpath -u $WSHome
    if ($LASTEXITCODE -eq 0) {
        $p.Trim()
    } else {
        # Basic fallback replacement
        $WSHome.Replace('D:\', '/mnt/d/').Replace('\', '/').Replace('C:\', '/mnt/c/')
    }
} catch {
    $WSHome.Replace('D:\', '/mnt/d/').Replace('\', '/').Replace('C:\', '/mnt/c/')
}

$ArgsString = ""
if ($RemainingArgs) {
    # Quote arguments to preserve spaces when passing to bash
    $EscapedArgs = @()
    foreach ($arg in $RemainingArgs) {
        if ($arg -match '\s') {
            $EscapedArgs += "'$arg'"
        } else {
            $EscapedArgs += $arg
        }
    }
    $ArgsString = $EscapedArgs -join ' '
}

# Invoke the bash ws script via wsl using its absolute path
wsl bash -c "$WSL_HOME/scripts/ws $ArgsString"
