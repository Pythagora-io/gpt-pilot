---
name: qa-phase4
description: >-
  Phase 4: Report and Deliver. Use when Phase 3 is finished. Verify phase 3 is fully complete, post text results to Linear/GitHub/Slack, get Tech Lead sign-off, THEN generate the final HTML report with screenshot evidence, upload to S3, update knowledge base, update queue.
---

# Phase 4: Report & Deliver

**Goal:** Verify testing is complete, post results for review, get Tech Lead sign-off,
_then_ generate the final HTML report, update the knowledge base, and close out the queue entry.

**Before starting:** Read `environment.md` in the template root to resolve all
environment-specific values.

## Hard Rules

1. **Phase 3 must be fully complete before starting.** If any test is still PENDING, go back to phase 3.
2. **The HTML report is only built AFTER the Tech Lead confirms sign-off.** Do NOT build the report before sign-off. Post text summaries to Linear/GitHub/Slack first, get confirmation, then use the `qa-report` skill to build the final report.
3. **Post to Linear AND GitHub.** Slack summary alone is not sufficient.
4. **Update the knowledge base.** Every QA run leaves the KB better than it found it.
5. **Update the queue.** Move to completed, pick next if any.

## Prerequisites

- Phase 3 completed — all tests have results in `{testFolder}/test-cases.json`
- Queue shows `phase: "phase3-done"`

## Workflow

### 4.1 Verify Phase 3 Completeness (MANDATORY — first step)

Read `{testFolder}/test-cases.json` and check BOTH sections:

**API Tests (`apiTests`):**

- [ ] Zero tests have `"status": "PENDING"`
- [ ] Zero tests have `"status": "RUNNING"`
- [ ] Every `"FAIL"` has notes and error explaining what happened
- [ ] Every `"BLOCKED"` has a documented reason

**Browser Tests (`browserTests`):**

- [ ] Zero tests have `"status": "PENDING"`
- [ ] Zero tests have `"status": "RUNNING"`
- [ ] Every `"FAIL"` has notes and error explaining what happened
- [ ] Every `"BLOCKED"` has a documented reason
- [ ] Every test has screenshots in `{testFolder}/screenshots/{PW-id}/`
- [ ] **Every browser test has at least one screenshot file** on disk. If missing, go back to phase 3.
- [ ] **Every browser test has a non-empty `screenshots` array** in test-cases.json with actual file paths.
- [ ] **Every browser test has `screenshotVerification` filled in.** If empty, it's invalid — go back to phase 3.
- [ ] **Every browser test has `screenshotMatchesExpected` set to `true` or `false`** (not `null`). If any is `null`, go back to phase 3.
- [ ] **⚠️ HARD GATE: No browser test has `screenshotMatchesExpected: false` with `status: "PASS"`.** If you find one, it's a false PASS — flip it to FAIL immediately.
- [ ] **⚠️ MANDATORY RE-VERIFICATION: For every PASS browser test, load its screenshot from `{testFolder}/screenshots/` using the `image` tool and verify it matches `expected`.** This is not a spot-check — check ALL of them. If any screenshot doesn't match what was expected, flip the test to FAIL.

**If ANY check fails → go back to `qa-phase3` and finish.** Do not proceed.

### 4.2 Post Results to Linear (text summary — no report yet)

Post a **short text comment** to the Linear ticket. No HTML report link yet — that comes after sign-off.

```bash
python3 skills/linear/scripts/linear_api.py --api-key "$LINEAR_KEY" comment \
  --issue-id "PAZ-XXX" \
  --body "## 🔍 QA Results: X bugs found (Y HIGH, Z MEDIUM)

### Test Summary
- **Total:** N tests
- **Pass:** X | **Fail:** Y | **Blocked:** Z
- **Pass rate:** XX%

### Bugs Found
| # | Severity | Description |
|---|----------|-------------|
| BUG-1 | 🔴 HIGH | ... |

Summary: <1-2 line summary>
Awaiting Tech Lead sign-off. Full report will be generated after confirmation."
```

If 0 bugs:

```markdown
## 🔍 QA Results: All N tests passed

Awaiting Tech Lead sign-off. Full report will be generated after confirmation.
```

### 4.3 Post Results to GitHub PRs (text summary — no report yet)

```bash
gh pr comment <number> --repo {GITHUB_ORG}/{PLATFORM_REPO} --body "## 🔍 QA Results ..."
```

Post to all companion PRs (both repos if applicable). No report link yet.

### 4.4 Sign-Off & Handoff

**All tests pass → Hand off to Tech Lead for confirmation:**

1. Tag Tech Lead in the Slack thread:

   ```
   <@{TECH_LEAD_SLACK_ID}> QA complete — all tests passing. Can you please check and confirm?
   ```

2. Move ticket to "Ready for Review" in Linear:
   ```bash
   python3 skills/linear/scripts/linear_api.py --api-key "$LINEAR_KEY" update-issue \
     --id "PAZ-XXX" \
     --assignee-id "{TEAM_LEAD_LINEAR_ID}"
   ```

**Tests fail → Loop with developer:**

Tag developer agent in Slack with specific failures:

```
<@{SLACK_DEVELOPER_AGENT_ID}> PAZ-XXX QA found issues — X tests failed.
Key failures: <brief list>
```

Do NOT build the report for failed runs — loop with the developer to fix, then re-test.
Only build the report once everything passes and Tech Lead confirms.

### 4.5 Build Final Report (ONLY after Tech Lead confirms)

⚠️ _Do NOT proceed to this step until the Tech Lead has confirmed sign-off in Slack._

**Read and follow the `qa-report` skill.** It handles everything:

- Screenshot validation and collection
- Visual re-verification of every screenshot
- S3 upload (screenshots + report)
- HTML report generation with embedded screenshot evidence
- Posting report links to Linear, GitHub, and Slack

Do NOT improvise the report build — the `qa-report` skill is the single source of truth
for how reports are built. Load it and follow it step by step.

### 4.6 Update Knowledge Base

Update the QA knowledge base with findings. This is mandatory — every run improves the KB.

#### New bugs → `{KNOWLEDGEBASE_PATH}/bugs/known-issues.md`

```markdown
### [BUG-XXX] Short Description

- **Severity**: High / Medium / Low
- **Found**: YYYY-MM-DD
- **Area**: platform/feature-name
- **Description**: What's broken
- **Reproduction**: Steps
- **Tracking**: Linear ticket / PR link
```

#### New patterns → `{KNOWLEDGEBASE_PATH}/bugs/patterns.md`

If you discovered a recurring pattern, add it.

#### New edge cases → `{KNOWLEDGEBASE_PATH}/platform/*.md`

Add to the "Edge Cases & Gotchas" section of the relevant file.

#### Resolved bugs → move from `known-issues.md` to `bugs/resolved/YYYY-MM/`

#### Commit

```bash
cd {PLATFORM_REPO_PATH}
git add knowledgebase/
git commit -m "docs(knowledgebase): update from QA run on PAZ-XXX"
git push
```

### 4.7 Update Queue — FINAL STEP

```bash
python3 skills/qa-queue/queue.py complete \
  --result "X/Y PASS, Z FAIL, W BLOCKED" \
  --reportUrl "{S3_REPORTS_URL_BASE}/{run-id}/report.html"
```

The script automatically promotes the next todo item to current.
If it prints `NEXT: PAZ-YYY promoted to current` → announce in Slack and start qa-phase0.
If it prints `NEXT: none` → done, queue is empty.

## Bug Severity Levels

| Severity  | Meaning                                                  |
| --------- | -------------------------------------------------------- |
| 🔴 HIGH   | Feature doesn't work, data loss, security issue, blocker |
| 🟡 MEDIUM | Partially works, missing code path, edge case failure    |
| 🟢 LOW    | Cosmetic, minor UX issue, non-blocking                   |

## Bug Categories

| Category           | Description                               |
| ------------------ | ----------------------------------------- |
| 🐛 Real Bug        | App misbehaves — needs code fix           |
| 🔗 Integration Bug | Dependency broken/missing                 |
| 🕳️ Missing Path    | Works via one entry point but not another |
| 🔧 Missing Feature | Not built yet                             |
| 🧪 Test Issue      | Test setup or environment limitation      |
