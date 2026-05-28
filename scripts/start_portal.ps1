$ErrorActionPreference = "Stop"

$port = 8090
$portalRoot = Resolve-Path (Join-Path $PSScriptRoot "..\portal")
$serverScript = Join-Path $portalRoot "server.py"

$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    Start-Process -WindowStyle Hidden -WorkingDirectory $portalRoot -FilePath "python" -ArgumentList $serverScript
    Start-Sleep -Seconds 2
}

$response = Invoke-WebRequest -Uri "http://localhost:$port" -UseBasicParsing -TimeoutSec 10
if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
    throw "Portal lokal gagal dibuka pada http://localhost:$port"
}

Write-Output "Portal lokal aktif: http://localhost:$port"
