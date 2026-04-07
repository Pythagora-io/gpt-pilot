# Critical Findings — Detailed

Add findings here as they're discovered. Each finding represents hard-won knowledge that shouldn't be lost.

_No findings recorded yet. This archive grows as the agent investigates and resolves complex issues._

<!-- Example:

## CF-001: Database connection pool exhaustion under load

**Discovered:** 2026-01-20
**Component:** API service → MongoDB connection
**Symptoms:** API returning 503 during traffic spikes. No errors in app logs. MongoDB itself healthy.
**Root cause:** Default MongoDB driver connection pool size is 5. Under load (>50 concurrent requests), all connections are consumed. New requests queue up and timeout after 30s.
**Key insight:** MongoDB driver defaults are too low for production. Always set `maxPoolSize` explicitly.
**Workaround/Fix:** Set `maxPoolSize=50` in the MongoDB connection string options.
**References:** https://www.mongodb.com/docs/drivers/node/current/fundamentals/connection/connection-options/

-->
