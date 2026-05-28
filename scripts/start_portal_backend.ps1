$ErrorActionPreference = "Stop"

$frontendPort = 8090
$backendPort = 8091
$root = Resolve-Path (Join-Path $PSScriptRoot "..")

if (!(Test-Path (Join-Path $root ".env")) -and (Test-Path (Join-Path $root ".env.example"))) {
    Copy-Item (Join-Path $root ".env.example") (Join-Path $root ".env")
}

$backendListener = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
if (-not $backendListener) {
    Start-Process -WindowStyle Hidden -WorkingDirectory $root -FilePath "python" -ArgumentList "-m", "portal_backend.app"
    Start-Sleep -Seconds 2
}

$frontendListener = Get-NetTCPConnection -LocalPort $frontendPort -State Listen -ErrorAction SilentlyContinue
if (-not $frontendListener) {
    & (Join-Path $PSScriptRoot "start_portal.ps1") | Out-Null
}

$health = Invoke-WebRequest -Uri "http://localhost:$backendPort/api/health" -UseBasicParsing -TimeoutSec 10
if ($health.StatusCode -lt 200 -or $health.StatusCode -ge 400) {
    throw "Portal backend gagal dibuka pada http://localhost:$backendPort/api/health"
}

$frontend = Invoke-WebRequest -Uri "http://localhost:$frontendPort" -UseBasicParsing -TimeoutSec 10
if ($frontend.StatusCode -lt 200 -or $frontend.StatusCode -ge 400) {
    throw "Portal frontend gagal dibuka pada http://localhost:$frontendPort"
}

Write-Output "Portal frontend aktif: http://localhost:$frontendPort"
Write-Output "Portal backend aktif: http://localhost:$backendPort/api/health"
