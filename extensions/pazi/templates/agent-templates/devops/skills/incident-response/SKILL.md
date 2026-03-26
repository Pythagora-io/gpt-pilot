---
name: incident-response
description: Guide incident response and troubleshooting for production outages. Use when the user reports a production issue, needs help debugging a service outage, or wants to establish incident response procedures.
---

# Incident Response

Help users diagnose and resolve production incidents quickly and systematically.

## Triage Steps

1. **Assess impact**: What's broken? Who's affected? Is it partial or full outage?
2. **Check recent changes**: What was deployed in the last 24 hours? Any config changes?
3. **Review metrics**: Check dashboards for error rates, latency, CPU, memory, disk
4. **Check logs**: Look for error patterns, stack traces, unusual log volume
5. **Verify dependencies**: Are databases, caches, and external APIs healthy?

## Common Investigation Commands

Suggest commands appropriate for the user's environment:
- Container logs, resource usage, pod status
- Database connection counts, slow queries, replication lag
- Network connectivity tests, DNS resolution
- Load balancer health check status
- Recent deployment history

## Mitigation Strategies

When the root cause isn't immediately clear, suggest mitigation in this order:
1. **Rollback** — If a recent deployment correlates with the issue
2. **Scale up** — If the issue looks like a capacity problem
3. **Restart** — If a service appears to be in a bad state
4. **Failover** — If a specific node or AZ is unhealthy
5. **Feature flag** — Disable the problematic feature while investigating

## Post-Incident

After resolution, help the user document:
1. Timeline of events
2. Root cause analysis
3. What worked and what didn't in the response
4. Action items to prevent recurrence
5. Monitoring gaps to address
