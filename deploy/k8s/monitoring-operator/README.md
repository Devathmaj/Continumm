<![CDATA[# Monitoring Operator Resources

Optional Kubernetes CRDs for clusters running the [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack) Helm chart (Prometheus Operator).

These resources are **not required** for the standard deployment — they provide native integration if your cluster already runs the Prometheus Operator.

## Resources

| File | Kind | Purpose |
|------|------|---------|
| `backend-servicemonitor.yaml` | ServiceMonitor | Auto-discovers the backend service for Prometheus Operator scraping |
| `continumm-prometheusrule.yaml` | PrometheusRule | Network telemetry alert rules (same as `deploy/prometheus/alert_rules.yml`) |

## Apply

```bash
kubectl apply -k deploy/k8s/monitoring-operator
```

## Prerequisites

- Prometheus Operator installed (via kube-prometheus-stack Helm chart)
- CRDs for `ServiceMonitor` and `PrometheusRule` must exist in the cluster
]]>
