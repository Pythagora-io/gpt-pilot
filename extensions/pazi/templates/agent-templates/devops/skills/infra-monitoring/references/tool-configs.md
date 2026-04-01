# Monitoring Tool Configurations

Detailed setup for each monitoring tool. **Never include actual tokens or credentials here — those go in `.credentials.env`.**

## Sentry

<!-- If connected -->

- **Org:** _not configured_
- **Projects:** _not configured_
- **Access:** `SENTRY_AUTH_TOKEN` in `.credentials.env`

### Useful queries:

```
# Via Sentry API:
# curl -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" https://sentry.io/api/0/projects/{org}/{project}/issues/
# curl -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" https://sentry.io/api/0/projects/{org}/{project}/events/
```

## Better Stack / Logging Tool

<!-- If connected -->

- **Access:** _not configured_
- **Log sources:** _not configured_

## PostHog / Analytics

<!-- If connected -->

- **Access:** _not configured_
- **Project:** _not configured_

## Uptime Monitoring

<!-- If connected -->

- **Monitors:** _not configured_
- **Check interval:** _not configured_

## APM (Datadog / New Relic / etc.)

<!-- If connected -->

- **Access:** _not configured_
- **Services tracked:** _not configured_
