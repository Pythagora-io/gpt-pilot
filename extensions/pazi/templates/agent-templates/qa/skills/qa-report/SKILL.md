---
name: qa-report
description: >-
  Build the final QA report with screenshots after Tech Lead sign-off. This is the
  ONLY skill that builds QA reports. Collects screenshots, validates every one exists
  on disk, uploads to S3, generates HTML report with embedded screenshot evidence,
  and posts the report link to Linear/GitHub/Slack. Triggered after Tech Lead confirms
  sign-off in Phase 4.
---

# QA Report — Final Report with Screenshots

**This skill does ONE thing:** Build the signed-off QA report with screenshot evidence.

It is called from Phase 4 _after_ the Tech Lead has confirmed sign-off. Do NOT use
this skill before sign-off. Do NOT use this skill if tests are still running.

**Before starting:** Read `environment.md` in the template root to resolve all
environment-specific values.

## Hard Rules

1. **Tech Lead must have confirmed before you start.** If they haven't said "confirmed" / "approved" / "looks good" in the Slack thread, STOP.
2. **Every browser test MUST have screenshot files on disk.** No files = go back to Phase 3.
3. **Every screenshot MUST be visually verified.** Load each one with the `image` tool and confirm it shows what the test expected.
4. **Every screenshot MUST appear in the final HTML report as an `<img>` tag.** The report is the deliverable — if a screenshot isn't in the report, it doesn't exist.
5. **Zero exceptions.** No "the screenshot was verified in Phase 3 so I'll skip it." Verify again here with fresh eyes.

## Prerequisites

- Phase 3 fully complete — all tests in `test-cases.json` have results
- Tech Lead has confirmed sign-off in Slack
- `{testFolder}/test-cases.json` exists with final results

## Workflow

### Step 1: Validate Screenshots Exist on Disk

```bash
# Check the test folder for screenshot files
find {testFolder}/screenshots/ -name "*.png" -type f | sort
```

**For every browser test in `test-cases.json`:**

- Check that the `screenshots` array is non-empty
- Check that every file path in `screenshots` actually exists on disk
- If ANY screenshot file is missing → collect it from `~/.openclaw/media/browser/`

**If `{testFolder}/screenshots/` is empty or has fewer files than expected:**

The browser tool auto-saves every screenshot to `~/.openclaw/media/browser/<uuid>.png`.
Collect them:

```bash
# List recent screenshots (sorted newest first)
ls -lt ~/.openclaw/media/browser/*.png | head -40

# Copy and rename to test folder — match to test cases by timestamp order
cp ~/.openclaw/media/browser/<uuid>.png {testFolder}/screenshots/PW-1.1/001-description.png
```

**HARD GATE:** If you cannot find screenshot files for a browser test — not in the test
folder AND not in `~/.openclaw/media/browser/` — that test is INVALID. Go back to Phase 3
and re-run it.

### Step 2: Visually Verify Every Screenshot

For EVERY browser test marked PASS, load its screenshot(s) using the `image` tool:

```
image(image="{testFolder}/screenshots/PW-1.1/001-dashboard.png", prompt="Describe what this screenshot shows. Any errors, 404 pages, or unexpected content?")
```

**Check for:**

- 404 pages, error pages, blank screens
- Login/signup page when expecting dashboard
- Error banners, "out of credits" messages
- Wrong page entirely
- Broken layouts, missing content

**After verifying each screenshot, update `test-cases.json`:**

- `screenshotVerification`: brief description of what the screenshot actually shows
- `screenshotMatchesExpected`: `true` or `false`

**HARD GATE:** If any screenshot doesn't match what was expected:

- Flip the test status to `FAIL`
- Set `screenshotMatchesExpected: false`
- STOP the report build — go back to Phase 4 to reassess results and potentially loop with developer

### Step 3: Upload Screenshots to S3

```bash
RUN_ID="{run-id}"

# Batch upload all screenshots
aws s3 sync "{testFolder}/screenshots/" \
  "s3://{S3_PUBLIC_BUCKET}/{S3_REPORTS_PREFIX}$RUN_ID/screenshots/" \
  --content-type "image/png" --profile {AWS_PROFILE}
```

**Verify the upload worked** — spot-check at least one URL returns 200:

```bash
curl -sf -o /dev/null -w "%{http_code}" \
  "{S3_REPORTS_URL_BASE}/$RUN_ID/screenshots/<filename>"
```

Screenshot URLs follow this pattern:
`{S3_REPORTS_URL_BASE}/{run-id}/screenshots/{filename}`

### Step 4: Generate the HTML Report

Use the QA report template from `skills/build-report/references/qa-report-template.html`
(if available). Also read `skills/build-report/SKILL.md` for the full template reference.

Save to: `{testFolder}/report.html`

#### Report Structure

1. **Summary cards** — total tests, pass, fail, blocked, pass rate %
2. **Environment info** — URL, PR links, date, test account
3. **Bug summary** (if any) — count, severities, one-line descriptions
4. **Bug details** (if any) — full reproduction steps, evidence, severity, root cause hypothesis
5. **Before vs After** (bug tickets) — pre-QA reproduction screenshots vs post-fix screenshots
6. **Test results** — each test case with:
   - Status badge (PASS/FAIL/BLOCKED)
   - Test steps
   - Notes and observations
   - **Screenshot thumbnails** (clickable, opens lightbox)
7. **Observations** — anything noticed that wasn't in the plan

#### Screenshot Embedding — MANDATORY

Every browser test case MUST have its screenshots embedded as visible `<img>` thumbnails.
Use the screenshot grid pattern:

```html
<div class="screenshot-grid" data-group="PW-1.1">
  <img
    src="{S3_REPORTS_URL_BASE}/{run-id}/screenshots/PW-1.1/001-login.png"
    alt="Login page"
    title="Login page"
    class="screenshot-thumb"
  />
  <img
    src="{S3_REPORTS_URL_BASE}/{run-id}/screenshots/PW-1.1/002-dashboard.png"
    alt="Dashboard loaded"
    title="Dashboard loaded"
    class="screenshot-thumb"
  />
</div>
```

**Rules:**

- All screenshots visible as thumbnails — never hidden behind carousels or accordions
- Every browser test has at least one screenshot in the report
- Lightbox with arrow navigation for multiple screenshots per test
- Use S3 URLs (not base64) to keep report size manageable
- Alt text and title should describe what the screenshot shows

#### Self-Check Before Saving

Before writing the final HTML file, count:

- Number of `<img` tags with `screenshot-thumb` class
- Number of browser tests in `test-cases.json`

**If img count < browser test count → you're missing screenshots. Fix it.**

### Step 5: Upload the Report to S3

```bash
aws s3 cp "{testFolder}/report.html" \
  "s3://{S3_PUBLIC_BUCKET}/{S3_REPORTS_PREFIX}$RUN_ID/report.html" \
  --content-type "text/html" --profile {AWS_PROFILE}
```

Report URL: `{S3_REPORTS_URL_BASE}/$RUN_ID/report.html`

**Verify it loads:**

```bash
curl -sf -o /dev/null -w "%{http_code}" \
  "{S3_REPORTS_URL_BASE}/$RUN_ID/report.html"
```

### Step 6: Post the Report Link Everywhere

**Linear:**

```bash
python3 skills/linear/scripts/linear_api.py --api-key "$LINEAR_KEY" comment \
  --issue-id "PAZ-XXX" \
  --body "✅ Tech Lead confirmed. Final QA report: <report-url>"
```

**GitHub:**

```bash
gh pr comment <number> --repo {GITHUB_ORG}/{PLATFORM_REPO} \
  --body "✅ QA signed off. Final report: <report-url>"
```

**Slack:** Post the report link in the original Slack thread:

```
✅ Final QA report: <report-url>
Summary: X/Y tests passed. <1-2 line summary of findings>
```

## Checklist (verify before considering this skill complete)

- [ ] Every browser test has screenshot files on disk
- [ ] Every screenshot was visually verified with the `image` tool
- [ ] Screenshots uploaded to S3 and URLs return 200
- [ ] HTML report contains `<img>` tags for every browser test's screenshots
- [ ] Report uploaded to S3 and URL returns 200
- [ ] Report link posted to Linear
- [ ] Report link posted to GitHub PR
- [ ] Report link posted in Slack thread
