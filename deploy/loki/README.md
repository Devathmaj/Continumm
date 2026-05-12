# Loki Configuration

Loki provides log aggregation for the Continumm stack. Backend structured JSON logs are collected by Docker's log driver and queryable through Grafana.

## Configuration (`loki.yml`)

- **Listen port:** 3100
- **Storage:** Local filesystem (`/loki/chunks`, `/loki/rules`)
- **Schema:** `v11` with `boltdb-shipper` index
- **Index period:** 24 hours
- **Replication factor:** 1 (single-node)
- **Auth:** Disabled (internal network only)

## Access

Loki is internal-only (no host port binding). Query logs via Grafana → Explore → Loki datasource.

## Example LogQL Queries

```logql
# All backend logs
{container="continumm-backend"}

# Errors only
{container="continumm-backend"} |= "ERROR"

# Parse JSON and filter by status code
{container="continumm-backend"} | json | status_code >= 500

# Nginx access logs
{container="continumm-nginx"}
```

## Storage

- Docker volume: `loki-data`
- K8s: emptyDir (ephemeral) or PVC depending on cluster config

