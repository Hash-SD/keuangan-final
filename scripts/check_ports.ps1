$ErrorActionPreference = "Stop"

$checks = @(
    @{ Name = "PostgreSQL metastore"; HostName = "localhost"; Port = 5432; Type = "tcp" },
    @{ Name = "MinIO API"; Url = "http://localhost:9000/minio/health/live"; Type = "http" },
    @{ Name = "MinIO Console"; Url = "http://localhost:9001"; Type = "http" },
    @{ Name = "Spark Master UI"; Url = "http://localhost:8080"; Type = "http" },
    @{ Name = "Spark Worker UI"; Url = "http://localhost:8081"; Type = "http" },
    @{ Name = "Spark Master RPC"; HostName = "localhost"; Port = 7077; Type = "tcp" },
    @{ Name = "Airflow Webserver"; Url = "http://localhost:8085/health"; Type = "http" },
    @{ Name = "Trino"; Url = "http://localhost:8082/v1/info"; Type = "http" },
    @{ Name = "Superset"; Url = "http://localhost:8089/health"; Type = "http" },
    @{ Name = "Portal Lokal"; Url = "http://localhost:8090"; Type = "http" },
    @{ Name = "Portal Backend API"; Url = "http://localhost:8091/api/health"; Type = "http" }
)

foreach ($check in $checks) {
    if ($check.Type -eq "tcp") {
        $result = Test-NetConnection -ComputerName $check.HostName -Port $check.Port -WarningAction SilentlyContinue
        if (-not $result.TcpTestSucceeded) {
            throw "$($check.Name) failed on $($check.HostName):$($check.Port)"
        }
        Write-Output "OK TCP  $($check.Name) $($check.HostName):$($check.Port)"
    }
    else {
        $response = Invoke-WebRequest -Uri $check.Url -UseBasicParsing -TimeoutSec 15
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
            throw "$($check.Name) failed with HTTP $($response.StatusCode)"
        }
        Write-Output "OK HTTP $($check.Name) $($check.Url) -> $($response.StatusCode)"
    }
}
