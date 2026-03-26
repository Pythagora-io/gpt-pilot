# Issue Database

Past issues and resolutions. **Add every new issue here** after resolving it. Future-you will thank you.

## Template

```markdown
## ISS-NNN: Brief title

**Date:** YYYY-MM-DD
**Severity:** P0/P1/P2/P3
**Service:** Which service was affected
**Symptoms:** What was observed (errors, user reports, monitoring alerts)
**Root cause:** Why it happened
**Resolution:** What fixed it
**Prevention:** How to prevent recurrence
**Time to resolve:** How long it took
```

## Issues

_No issues recorded yet. This database grows as issues are investigated and resolved._

<!-- Example:
## ISS-001: API returning 503 after deploy
**Date:** 2026-01-15
**Severity:** P1
**Service:** API
**Symptoms:** All API requests returning 503. Health check failing. No errors in application logs.
**Root cause:** New dependency added to package.json wasn't installed during deploy. Node process crashed on startup.
**Resolution:** SSH'd in, ran `npm install`, restarted service.
**Prevention:** Added `npm ci` to deploy script before restart.
**Time to resolve:** 15 minutes
-->
