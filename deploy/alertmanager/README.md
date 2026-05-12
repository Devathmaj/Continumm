<![CDATA[# Alertmanager Configuration

Alertmanager receives firing alerts from Prometheus and handles deduplication, grouping, and routing to notification channels.

## Configuration (`alertmanager.yml`)

- **Resolve timeout:** 5 minutes
- **Grouping:** By `alertname` and `ip`
- **Group wait:** 10 seconds (buffer before first notification)
- **Group interval:** 5 minutes (time between notifications for a group)
- **Repeat interval:** 3 hours (re-notify if still firing)
- **Default receiver:** No-op (configure webhooks/email/Slack below)

## Adding Notification Channels

Edit `alertmanager.yml`:

```yaml
receivers:
  - name: default
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#alerts'
        send_resolved: true
    # Or webhook:
    # webhook_configs:
    #   - url: 'https://your-webhook.example.com/alert'
```

Restart Alertmanager after changes: `docker-compose restart alertmanager`

## Alert Rules

Alert rules are defined in Prometheus (`deploy/prometheus/alert_rules.yml`), not in Alertmanager. Alertmanager only handles routing and notification delivery.

## Access

Internal only. Check status via:
```bash
docker-compose exec alertmanager wget -qO- http://localhost:9093/api/v2/status
```
]]>
