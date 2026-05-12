<![CDATA[# Kubernetes Deployment

Kustomize-based Kubernetes manifests for deploying the complete Continumm stack into a dedicated namespace.

---

## What Gets Deployed

| Resource | Kind | Replicas | Notes |
|----------|------|----------|-------|
| `namespace.yaml` | Namespace | — | `continumm` namespace |
| `backend` | Deployment + Service | 2 | API-only (telemetry disabled) |
| `backend-telemetry` | Deployment + Service | 1 | Telemetry workers with leader lock |
| `nginx` | Deployment + Service | 1 | Reverse proxy (ClusterIP) |
| `postgres` | Deployment + Secret | 1 | PostgreSQL 16 with PVC |
| `prometheus` | Deployment + Service + ConfigMap | 1 | Metrics with 50Gi PVC |
| `grafana` | Deployment + Service + ConfigMap | 1 | Dashboards + datasources |
| `loki` | Deployment + Service + ConfigMap | 1 | Log aggregation |
| `tempo` | Deployment + Service + ConfigMap | 1 | Trace storage |
| `alertmanager` | Deployment + Service + ConfigMap | 1 | Alert routing |
| `node-exporter` | DaemonSet + Service | per-node | Host metrics collection |
| `ingress` | Ingress | — | `continumm.local` → nginx:80 |

---

## Prerequisites

1. **Kubernetes cluster** — kind, minikube, or managed (EKS/AKS/GKE)
2. **Nginx Ingress Controller** installed
3. **Backend Docker image** available to the cluster

### Build and Load Image

```bash
# Build
docker build -t continumm-backend:latest ./backend

# kind
kind load docker-image continumm-backend:latest

# minikube
minikube image load continumm-backend:latest
```

---

## Deploy

```bash
kubectl apply -k deploy/k8s
```

All resources are created in the `continumm` namespace (defined in `kustomization.yaml`).

### Verify

```bash
kubectl -n continumm get pods
kubectl -n continumm get svc
kubectl -n continumm get ingress
```

---

## Access

### Application

Add to `/etc/hosts` (or `C:\Windows\System32\drivers\etc\hosts`):
```
127.0.0.1 continumm.local
```

Then: http://continumm.local

### Prometheus (port-forward)

```bash
kubectl -n continumm port-forward svc/prometheus 9090:9090
# Access: http://localhost:9090
```

### Grafana (port-forward)

```bash
kubectl -n continumm port-forward svc/continumm-grafana 3000:3000
# Access: http://localhost:3000  (admin / changeme)
```

---

## Telemetry Configuration

Edit `telemetry-configmap.yaml` before applying:

```yaml
data:
  TELEMETRY_ENABLED: "true"
  SCAN_SUBNETS: "192.168.1.0/24,10.0.0.0/24"
  DISCOVERY_INTERVAL_SECONDS: "300"
  POLL_INTERVAL_SECONDS: "30"
```

The `backend-telemetry` deployment mounts this ConfigMap and runs a single replica with `TELEMETRY_ENABLED=true`. It acquires a PostgreSQL advisory lock so only one pod performs scanning, even if accidentally scaled.

---

## Secrets

| Secret | Keys | Purpose |
|--------|------|---------|
| `postgres-secret` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Database credentials |
| `snmp-secret` | `SNMP_COMMUNITY` | SNMP community string (for future use) |

**Important:** Replace the default base64-encoded values before production use:

```bash
echo -n 'your-secure-password' | base64
# Update postgres-secret.yaml with the result
```

---

## Scaling

```bash
# Scale API replicas (safe — telemetry is separate)
kubectl -n continumm scale deployment backend --replicas=4

# DO NOT scale backend-telemetry beyond 1 (advisory lock handles it, but wasteful)
```

---

## Rollout Management

```bash
# Update backend image
kubectl -n continumm set image deployment/backend backend=continumm-backend:new-sha

# Check rollout status
kubectl -n continumm rollout status deployment/backend

# Rollback
kubectl -n continumm rollout undo deployment/backend

# View rollout history
kubectl -n continumm rollout history deployment/backend
```

---

## Monitoring Operator (Optional)

The `monitoring-operator/` subdirectory contains CRDs for clusters running [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack):

- `backend-servicemonitor.yaml` — ServiceMonitor for auto-discovery by Prometheus Operator
- `continumm-prometheusrule.yaml` — PrometheusRule with network alerting rules

Apply separately:
```bash
kubectl apply -k deploy/k8s/monitoring-operator
```

---

## Troubleshooting

```bash
# Pod logs
kubectl -n continumm logs -f deployment/backend
kubectl -n continumm logs -f deployment/backend-telemetry

# Describe failing pod
kubectl -n continumm describe pod <pod-name>

# Check events
kubectl -n continumm get events --sort-by='.lastTimestamp'

# Exec into a pod
kubectl -n continumm exec -it deployment/backend -- /bin/sh

# Test internal connectivity
kubectl -n continumm exec deployment/nginx -- wget -qO- http://backend:8000/health
```

---

## File Reference

```
k8s/
├── kustomization.yaml              # Kustomize resource list
├── namespace.yaml                  # continumm namespace
├── backend-deployment.yaml         # API pods (2 replicas)
├── backend-service.yaml            # ClusterIP for API
├── backend-telemetry-deployment.yaml # Telemetry worker (1 replica)
├── backend-telemetry-service.yaml  # ClusterIP for telemetry metrics
├── nginx-configmap.yaml            # Nginx config (matches deploy/nginx/nginx.conf)
├── nginx-deployment.yaml           # Nginx pod
├── nginx-service.yaml              # ClusterIP for Nginx
├── ingress.yaml                    # Ingress → nginx:80
├── postgres-deployment.yaml        # PostgreSQL with PVC
├── postgres-secret.yaml            # Database credentials
├── telemetry-configmap.yaml        # Scan subnets and intervals
├── snmp-secret.yaml                # SNMP community string
├── prometheus-configmap.yaml       # Scrape config
├── prometheus-deployment.yaml      # Prometheus with PVC
├── prometheus-service.yaml
├── grafana-configmap.yaml          # Datasources + dashboard JSON
├── grafana-deployment.yaml         # Grafana with PVC
├── grafana-service.yaml
├── loki-configmap.yaml
├── loki-deployment.yaml / service
├── tempo-configmap.yaml
├── tempo-deployment.yaml / service
├── alertmanager-configmap.yaml
├── alertmanager-deployment.yaml / service
├── node-exporter-daemonset.yaml    # DaemonSet (one per node)
├── node-exporter-service.yaml
└── monitoring-operator/            # Optional kube-prometheus-stack CRDs
```
]]>
