param([switch]$Install)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$downloadDirectory = Join-Path $projectRoot 'tools\downloads'
New-Item -ItemType Directory -Path $downloadDirectory -Force | Out-Null
$partialPath = Join-Path $downloadDirectory 'Docker Desktop Installer.exe.part'
$installerPath = Join-Path $downloadDirectory 'Docker Desktop Installer.exe'
if (-not (Test-Path -LiteralPath $installerPath)) {
    & curl.exe --location --fail --silent --show-error --continue-at - --max-time 300 --output $partialPath 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe'
    if ($LASTEXITCODE -ne 0) {
        throw 'Download incomplete. The partial file is retained; rerun this script to resume.'
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $partialPath
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Docker') {
        throw 'Installer signature is invalid or not from Docker. Do not execute it.'
    }
    Move-Item -LiteralPath $partialPath -Destination $installerPath
}
$signature = Get-AuthenticodeSignature -LiteralPath $installerPath
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Docker') {
    throw 'Installer verification failed.'
}
[pscustomobject]@{signature=$signature.Status.ToString();publisher=$signature.SignerCertificate.Subject;sha256=(Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash} |
    ConvertTo-Json | Set-Content (Join-Path $projectRoot 'docs\docker-installer-verification.json')
if ($Install) {
    $process = Start-Process -FilePath $installerPath -ArgumentList 'install --user --quiet' -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Docker installer exited with code $($process.ExitCode)." }
}
Write-Output 'Official Docker installer downloaded and signature verified.'
