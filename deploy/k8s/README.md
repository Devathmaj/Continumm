# Continumm Kubernetes Deployment

This folder contains Kubernetes manifests for the Continumm stack (backend, nginx, prometheus, grafana, node-exporter).

## Prerequisites

- A Kubernetes cluster (kind/minikube/local)
- An Ingress controller installed (nginx recommended)
- The backend image available to the cluster as `continumm-backend:latest`

## Apply

```bash
kubectl apply -k deploy/k8s
```

## Access

- App via Ingress: http://continumm.local (add to /etc/hosts if needed)
- Prometheus (port-forward):
  ```bash
  kubectl -n continumm port-forward svc/prometheus 9090:9090
  ```
- Grafana (port-forward):
  ```bash
  kubectl -n continumm port-forward svc/continumm-grafana 3000:3000
  ```
  Default creds: admin / changeme

## Notes

- Update the backend image tag and `GIT_COMMIT` env as needed.
- Persistent volumes use the default storage class in your cluster.
