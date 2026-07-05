$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

docker compose up -d --build
docker compose ps

Write-Output ""
Write-Output "Cluster lakehouse aktif pada network lakehouse_net."
Write-Output "Portal lokal: http://localhost:8090"
Write-Output "Dashboard lokal: http://localhost:8090/local-dashboard/"
Write-Output "Portal backend API: http://localhost:8091/api/health"
Write-Output "Superset: http://localhost:8089"
Write-Output "MinIO Console: http://localhost:9001"
