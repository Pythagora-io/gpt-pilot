# HTML Report Template

The Manager generates this report after all tests complete.

## Report Requirements

- Dark theme (background: `#0f0f1a`, text: `#e0e0e0`)
- Overall stats grid: total tests, pass, fail, blocked, skip, pass rate %
- Visual progress bar with colored segments (green=pass, red=fail, orange=blocked, gray=skip)
- Filter buttons: All / Pass / Fail / Blocked / Skip
- Failed & Blocked tests summary table at the very top (bugs first)
- Each test as an expandable card with:
  - Status badge (colored)
  - Test name and ID
  - Notes/observations
  - Embedded screenshots
- Expand/collapse all button
- Bug triage section at bottom (if bugs found):
  - 🐛 Real Bug — app misbehaves, needs code fix
  - 🔧 Missing Feature — test expects something not built yet
  - 🧪 Test Issue — test has wrong setup or env limitation
  - Each bug: severity (HIGH/MEDIUM/LOW), reproduction steps, expected vs actual

## Minimal HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>QA Report: {run-id}</title>
    <style>
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      body {
        background: #0f0f1a;
        color: #e0e0e0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        padding: 2rem;
      }
      .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
      }
      .stat-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
      }
      .stat-value {
        font-size: 2rem;
        font-weight: bold;
      }
      .pass {
        color: #4ade80;
      }
      .fail {
        color: #f87171;
      }
      .blocked {
        color: #fb923c;
      }
      .skip {
        color: #94a3b8;
      }
      .progress-bar {
        height: 8px;
        border-radius: 4px;
        display: flex;
        overflow: hidden;
        margin-bottom: 2rem;
        background: #1a1a2e;
      }
      .progress-segment {
        height: 100%;
      }
      .filters {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 2rem;
        flex-wrap: wrap;
      }
      .filter-btn {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        border: 1px solid #333;
        background: #1a1a2e;
        color: #e0e0e0;
        cursor: pointer;
      }
      .filter-btn.active {
        background: #3b82f6;
        border-color: #3b82f6;
      }
      .test-card {
        background: #1a1a2e;
        border-radius: 12px;
        margin-bottom: 1rem;
        overflow: hidden;
      }
      .test-header {
        padding: 1rem 1.5rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 1rem;
      }
      .test-body {
        padding: 0 1.5rem 1.5rem;
        display: none;
      }
      .test-card.open .test-body {
        display: block;
      }
      .badge {
        padding: 0.25rem 0.75rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
      }
      .badge.pass {
        background: rgba(74, 222, 128, 0.2);
      }
      .badge.fail {
        background: rgba(248, 113, 113, 0.2);
      }
      .badge.blocked {
        background: rgba(251, 146, 60, 0.2);
      }
      .badge.skip {
        background: rgba(148, 163, 184, 0.2);
      }
      .screenshot-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.5rem;
      }
      .screenshot-thumb {
        width: 220px;
        height: 140px;
        object-fit: cover;
        border-radius: 6px;
        border: 1px solid #333;
        cursor: pointer;
      }
      .screenshot-thumb:hover {
        border-color: #3b82f6;
      }
      .bug-section {
        margin-top: 3rem;
        border-top: 1px solid #333;
        padding-top: 2rem;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      th,
      td {
        padding: 0.75rem;
        text-align: left;
        border-bottom: 1px solid #222;
      }
      th {
        color: #94a3b8;
      }
      .lightbox-overlay {
        display: none;
        position: fixed;
        inset: 0;
        z-index: 9999;
        background: rgba(0, 0, 0, 0.85);
        align-items: center;
        justify-content: center;
        cursor: pointer;
      }
      .lightbox-overlay.active {
        display: flex;
      }
      .lightbox-overlay img {
        max-width: 95vw;
        max-height: 90vh;
        border-radius: 8px;
      }
    </style>
  </head>
  <body>
    <h1>QA Report: {run-id}</h1>
    <p style="color: #94a3b8; margin-bottom: 2rem;">Target: {appUrl} | {date}</p>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{total}</div>
        <div>Total</div>
      </div>
      <div class="stat-card">
        <div class="stat-value pass">{pass}</div>
        <div>Pass</div>
      </div>
      <div class="stat-card">
        <div class="stat-value fail">{fail}</div>
        <div>Fail</div>
      </div>
      <div class="stat-card">
        <div class="stat-value blocked">{blocked}</div>
        <div>Blocked</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{passRate}%</div>
        <div>Pass Rate</div>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="progress-bar">
      <div class="progress-segment" style="width:{passPct}%;background:#4ade80"></div>
      <div class="progress-segment" style="width:{failPct}%;background:#f87171"></div>
      <div class="progress-segment" style="width:{blockedPct}%;background:#fb923c"></div>
      <div class="progress-segment" style="width:{skipPct}%;background:#94a3b8"></div>
    </div>

    <!-- Filters -->
    <div class="filters">
      <button class="filter-btn active" onclick="filter('all')">All</button>
      <button class="filter-btn" onclick="filter('pass')">Pass</button>
      <button class="filter-btn" onclick="filter('fail')">Fail</button>
      <button class="filter-btn" onclick="filter('blocked')">Blocked</button>
      <button class="filter-btn" onclick="filter('skip')">Skip</button>
      <button class="filter-btn" onclick="toggleAll()">Expand All</button>
    </div>

    <!-- Test Cards -->
    <div class="test-card" data-status="{status}">
      <div class="test-header" onclick="this.parentElement.classList.toggle('open')">
        <span class="badge {status}">{STATUS}</span>
        <span>{testId}: {testName}</span>
      </div>
      <div class="test-body">
        <p>{notes}</p>
        <div class="screenshot-grid">
          <img
            src="{screenshotUrl}"
            alt="{description}"
            class="screenshot-thumb"
            onclick="openLightbox(this.src, this.alt)"
          />
        </div>
      </div>
    </div>

    <!-- Bug Triage (if any) -->
    <div class="bug-section">
      <h2>Bug Triage</h2>
      <table>
        <tr>
          <th>#</th>
          <th>Severity</th>
          <th>Category</th>
          <th>Test</th>
          <th>Description</th>
        </tr>
        <tr>
          <td>BUG-1</td>
          <td>🔴 HIGH</td>
          <td>🐛 Real Bug</td>
          <td>{testId}</td>
          <td>{description}</td>
        </tr>
      </table>
    </div>

    <!-- Lightbox -->
    <div class="lightbox-overlay" id="lightbox" onclick="closeLightbox()">
      <img id="lightbox-img" src="" alt="" />
    </div>

    <script>
      function filter(status) {
        document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
        event.target.classList.add("active");
        document.querySelectorAll(".test-card").forEach((c) => {
          c.style.display = status === "all" || c.dataset.status === status ? "" : "none";
        });
      }
      function toggleAll() {
        const cards = document.querySelectorAll(".test-card");
        const allOpen = [...cards].every((c) => c.classList.contains("open"));
        cards.forEach((c) => (allOpen ? c.classList.remove("open") : c.classList.add("open")));
      }
      function openLightbox(src, alt) {
        document.getElementById("lightbox-img").src = src;
        document.getElementById("lightbox").classList.add("active");
      }
      function closeLightbox() {
        document.getElementById("lightbox").classList.remove("active");
      }
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeLightbox();
      });
    </script>
  </body>
</html>
```
