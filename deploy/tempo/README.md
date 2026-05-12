# Tempo Configuration

Tempo provides distributed trace storage for the Continumm backend. It receives OpenTelemetry traces via OTLP gRPC and makes them queryable through Grafana.

## Configuration (`tempo.yml`)

- **HTTP port:** 3200 (API)
- **OTLP gRPC port:** 4317 (trace receiver)
- **Storage:** Local filesystem (`/var/tempo`)

## How Traces Flow

1. Backend Flask app is instrumented with `opentelemetry-instrumentation-flask`
2. `BatchSpanProcessor` exports spans via OTLP gRPC to `tempo:4317`
3. Traces are stored locally in Tempo
4. Grafana queries Tempo via its HTTP API on port 3200
5. Trace IDs are included in structured JSON logs, enabling log-to-trace correlation

## Enabling Tracing

Set in the backend environment:
```env
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=tempo:4317
OTEL_SERVICE_NAME=continumm-backend
```

## Access

Internal only. Query traces via Grafana → Explore → Tempo datasource.

