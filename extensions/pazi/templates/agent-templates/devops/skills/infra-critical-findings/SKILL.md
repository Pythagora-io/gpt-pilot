---
name: infra-critical-findings
description: Archive of critical infrastructure findings that took significant time to discover. Deep root causes and non-obvious system behaviors. Consult when stuck on a puzzling issue or before working on a component with known pitfalls. Add new findings when root cause took >30 min to identify or behavior was counterintuitive. Triggers on "why does X work this way", "root cause", "gotcha", "pitfall", or when debugging stalls.
---

# Critical Findings

Hard-won knowledge. Consult before deep-diving into unfamiliar areas. **Add new findings whenever you discover something non-obvious.**

## When to Add a Finding

- Root cause took > 30 minutes to identify
- Behavior was counterintuitive or undocumented
- The same issue is likely to recur or confuse future investigators
- A workaround exists that isn't obvious

## Finding Index

| ID       | Title                                          | Key Insight                             |
| -------- | ---------------------------------------------- | --------------------------------------- |
| _CF-001_ | _Example: Database connection pool exhaustion_ | _Default pool size is 5, app needs 20+_ |

## Details: `references/findings.md`

## Template for New Findings

```markdown
## CF-NNN: Brief descriptive title

**Discovered:** YYYY-MM-DD
**Component:** Which service/system
**Symptoms:** What you observed that led to this investigation
**Root cause:** The actual underlying issue (be specific)
**Key insight:** One-line summary of what's non-obvious
**Workaround/Fix:** How to handle it
**References:** Links, commits, docs that helped
```
