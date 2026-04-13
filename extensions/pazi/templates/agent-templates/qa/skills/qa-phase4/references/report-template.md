# HTML Report Template

Dark-themed HTML report with screenshot evidence.

## Requirements

- Dark theme (background: `#0f0f1a`, text: `#e0e0e0`)
- Overall stats grid: total tests, pass, fail, blocked, pass rate %
- Visual progress bar with colored segments (green=pass, red=fail, orange=blocked, gray=skip)
- Filter buttons: All / Pass / Fail / Blocked
- Failed & Blocked tests summary table at the top (bugs first)
- Each test as an expandable card with:
  - Status badge (colored)
  - Test name and ID
  - Notes/observations
  - Screenshot thumbnails (clickable lightbox)
- Expand/collapse all button
- Bug triage section at bottom (if bugs found)

## Status Colors

- PASS: `#22c55e` (green)
- FAIL: `#ef4444` (red)
- BLOCKED: `#f97316` (orange)
- NEED HELP: `#eab308` (yellow)

## Screenshot Grid & Lightbox

```html
<style>
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
    transition: border-color 0.2s;
  }
  .screenshot-thumb:hover {
    border-color: #3b82f6;
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
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
  }
  .lightbox-caption {
    position: fixed;
    bottom: 1.5rem;
    left: 50%;
    transform: translateX(-50%);
    color: #fff;
    font-size: 0.9rem;
    background: rgba(0, 0, 0, 0.6);
    padding: 0.3rem 1rem;
    border-radius: 6px;
  }
</style>

<div class="lightbox-overlay" id="lightbox" onclick="closeLightbox()">
  <img id="lightbox-img" src="" alt="" />
  <div class="lightbox-caption" id="lightbox-caption"></div>
</div>

<script>
  function openLightbox(src, alt) {
    document.getElementById("lightbox-img").src = src;
    document.getElementById("lightbox-caption").textContent = alt || "";
    document.getElementById("lightbox").classList.add("active");
  }
  function closeLightbox() {
    document.getElementById("lightbox").classList.remove("active");
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeLightbox();
  });
</script>
```

## S3 Upload

```bash
# Screenshots
aws s3 sync "{testFolder}/screenshots/" \
  "s3://{S3_PUBLIC_BUCKET}/{S3_REPORTS_PREFIX}$RUN_ID/screenshots/" \
  --content-type image/png --profile {AWS_PROFILE}

# Report
aws s3 cp "{testFolder}/report.html" \
  "s3://{S3_PUBLIC_BUCKET}/{S3_REPORTS_PREFIX}$RUN_ID/report.html" \
  --content-type "text/html" --profile {AWS_PROFILE}
```

Public URL: `{S3_REPORTS_URL_BASE}/{run-id}/report.html`
