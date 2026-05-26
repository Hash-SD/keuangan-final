$ErrorActionPreference = "Stop"

$port = 8090
$root = Resolve-Path (Join-Path $PSScriptRoot "..\portal")

$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    Start-Process -WindowStyle Hidden -WorkingDirectory $root -FilePath "python" -ArgumentList "-m", "http.server", "$port"
    Start-Sleep -Seconds 2
}

$response = Invoke-WebRequest -Uri "http://localhost:$port" -UseBasicParsing -TimeoutSec 10
if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
    throw "Portal lokal gagal dibuka pada http://localhost:$port"
}

Write-Output "Portal lokal aktif: http://localhost:$port"
