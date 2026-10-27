# Run elevated. Enables prerequisites without restarting Windows.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$logPath = Join-Path $projectRoot 'docs\sandbox-setup.log'
Start-Transcript -Path $logPath -Append
try {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Administrator rights are required to enable the Windows virtualization features.'
    }
    $restartNeeded = $false
    foreach ($feature in @('Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform')) {
        $result = Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart
        $restartNeeded = $restartNeeded -or $result.RestartNeeded
    }
    [pscustomobject]@{features_enabled=$true;restart_required=$restartNeeded;automatic_restart=$false} |
        ConvertTo-Json | Set-Content (Join-Path $projectRoot 'docs\sandbox-setup-status.json')
    Write-Output 'Windows features prepared. No automatic restart was requested.'
} catch {
    [pscustomobject]@{features_enabled=$false;error=$_.Exception.Message;automatic_restart=$false} |
        ConvertTo-Json | Set-Content (Join-Path $projectRoot 'docs\sandbox-setup-status.json')
    throw
} finally {
    Stop-Transcript
}
