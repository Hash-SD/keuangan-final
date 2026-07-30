from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
names = subprocess.check_output(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], text=True)
services = {
    "portal": "HEALTHY" if "keuangan-portal-frontend Up" in names and "keuangan-portal-backend Up" in names else "UNHEALTHY",
    "airflow": "HEALTHY" if "keuangan-airflow-webserver Up" in names and "keuangan-airflow-scheduler Up" in names else "UNHEALTHY",
    "postgresql": "HEALTHY" if "keuangan-postgres-metastore Up" in names else "UNHEALTHY",
    "minio": "HEALTHY" if "keuangan-minio Up" in names else "UNHEALTHY",
    "trino": "HEALTHY" if "keuangan-trino Up" in names else "UNHEALTHY",
    "superset": "HEALTHY" if "keuangan-superset Up" in names else "UNHEALTHY",
}
payload = {"checked_at": datetime.now(timezone.utc).isoformat(), "services": services, "docker_ps": names.splitlines()}
(ROOT / "outputs/reports/service_health_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload))
