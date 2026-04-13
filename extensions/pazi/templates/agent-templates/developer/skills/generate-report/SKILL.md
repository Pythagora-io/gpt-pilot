---
name: generate-report
description: Instructions for generating reports. Use this skill EVERY TIME when generating a report.
metadata: { "openclaw": { "emoji": "📊" } }
---

# Generate Report Skill

When thinking about the design of this report, you MUST use the frontend-design skill.

## Before Generating a Report

Check your success criteria first. Before building a report:

1. Review the success criteria you defined at the start of the task
2. Verify you have satisfied all criteria
3. If not satisfied, continue working or ask the user what to do
4. Only proceed to report generation when criteria are met

## Report Format

Unless the user explicitly requests a different format, reports must be HTML files saved to the project folder. This is the default — always generate an HTML file.

## Key Rules

- Keep the structure - main-content with content-wrapper
- Save to the project folder with any name (e.g., report.html, `qa_report.html`)

## Completeness (Critical)

The report is the single deliverable the user receives. It must contain ALL information gathered during task execution — nothing should be left out or summarized away. If a sub-agent found it, it belongs in the report. Do not assume the user has access to anything outside this file. A report missing information is a failed report.

## Source Citations (Critical)

A report without sources is useless. Every claim, data point, and finding MUST link to where it came from. If you cannot cite a source for a piece of information, flag it explicitly as unverified.

Sub-agents attach references to where they obtained information. You MUST use these references to create inline citations:

- DO NOT list references at the end of the report
- DO link each data point directly to its source within the report content
- Use inline hyperlinks so readers can verify information immediately
- If a sub-agent did not provide a source for a finding, go back and get it — do not include unsourced data silently

Example - instead of:

```html
<p>The company raised $50M in funding. [1]</p>
<!-- References at bottom - DON'T DO THIS -->
```

Do this:

```html
<p>The company raised <a href="https://source.com/article" target="_blank">$50M in funding</a>.</p>
```

For multiple facts from the same source, link the most relevant phrase:

```html
<p>
  According to their <a href="https://example.com/report" target="_blank">Q4 earnings report</a>,
  revenue grew 25% while operating costs decreased by 10%.
</p>
```

---

Important:

- Add id attributes to sections for navigation (e.g., `<section id="findings" class="section">`)

## Collapsible Sections

When a section contains a lot of information, use HTML `<details>` and `<summary>` elements to make it collapsible. This keeps the report scannable while preserving all data.

```html
<details>
  <summary>Section Title (click to expand)</summary>
  <!-- detailed content here -->
</details>
```

Use collapsible sections for:

- Long lists of findings or data points
- Detailed methodology or raw data
- Supporting evidence that supplements the main narrative
- Any section with more than ~5 items or substantial content

Keep the most important/summary info visible by default. Nest the details inside collapsibles.

### Collapsible Item Cards

When reporting on multiple items (startups, products, findings, etc.), each item should be a collapsible card. The collapsed summary shows the essential info at a glance — the expanded body has all the details:

```html
<details>
  <summary>
    <span class="item-title">Item Name</span>
    <span class="item-desc">— Short one-line description</span>
    <span class="item-tag">Category</span>
    <a href="https://link.com" target="_blank" onclick="event.stopPropagation()">Link →</a>
  </summary>
  <div class="detail-body">
    <!-- Full description, metadata, integration details, all links -->
  </div>
</details>
```

The summary row should contain:

- **Name** (bold/prominent)
- **Description** (one line, muted)
- **Category tag** (colored badge)
- **Primary link** (clickable without expanding, use `event.stopPropagation()`)

This lets readers scan all items quickly and drill into the ones they care about.

### Output Requirements

- Include reference links for ALL data gathered
- Every fact, finding, or piece of information must cite its source
- For HTML reports, use HTML anchor tags: `<a href="https://example.com" target="_blank">description</a>`
- Only use markdown link format if the user explicitly requests a markdown report
- If information comes from multiple sources, include all relevant links

This ensures the user can verify where all information came from.
