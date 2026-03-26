# Monitoring Tool Configurations

Detailed setup for each monitoring tool. **Never include actual tokens or credentials here — those go in `.credentials.env`.**

## Sentry

<!-- If connected -->

- **Org:** _not configured_
- **Projects:** _not configured_
- **Access:** Pipedream integration or `SENTRY_AUTH_TOKEN` in `.credentials.env`

### Useful queries:

```
# Via Pipedream:
# pipedream_use_integration sentry list-project-issues
# pipedream_use_integration sentry list-project-events
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
