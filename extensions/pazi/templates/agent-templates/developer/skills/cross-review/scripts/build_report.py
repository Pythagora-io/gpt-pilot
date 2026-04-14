#!/usr/bin/env python3
"""Build HTML cross-review report from plan files in a directory.

Usage:
  python3 build_report.py <plans_dir> <output_html> [--title "Report Title"]

Expects files matching these patterns in plans_dir:
  task*.md           → Task section
  claude-plan-v1*.md → Round 1 Claude
  codex-plan-v1*.md  → Round 1 Codex
  claude-plan-v2*.md → Round 2 Claude
  codex-plan-v2*.md  → Round 2 Codex
  *verdict*.md       → Verdict section
"""

import argparse
import glob
import html
import json
import os
import sys


def find_file(plans_dir, patterns):
    """Find first matching file from a list of glob patterns."""
    for pat in patterns:
        matches = sorted(glob.glob(os.path.join(plans_dir, pat)))
        if matches:
            return matches[-1]  # latest if multiple
    return None


def main():
    parser = argparse.ArgumentParser(description="Build cross-review HTML report")
    parser.add_argument("plans_dir", help="Directory containing plan .md files")
    parser.add_argument("output", help="Output HTML file path")
    parser.add_argument("--title", default="Cross-Review Report", help="Report title")
    parser.add_argument("--subtitle", default="", help="Report subtitle")
    args = parser.parse_args()

    file_specs = [
        ("task", ["task*.md"], "Task Description", "", ""),
        ("claude-v1", ["claude-plan-v1*.md", "claude-plan.md"], "Round 1 — Independent Plan", "CLAUDE", ""),
        ("codex-v1", ["codex-plan-v1*.md", "codex-plan.md"], "Round 1 — Independent Plan", "CODEX", ""),
        ("claude-v2", ["claude-plan-v2*.md", "claude-plan-v3*.md"], "Round 2 — Revised Plan", "CLAUDE", ""),
        ("codex-v2", ["codex-plan-v2*.md", "codex-plan-v3*.md"], "Round 2 — Revised Plan", "CODEX", ""),
        ("verdict", ["*verdict*.md", "verdict*.md"], "Final Verdict & Recommendation", "VERDICT", ""),
    ]

    sections_config = [
        ("Task", ["task"]),
        ("Round 1 — Independent Plans", ["claude-v1", "codex-v1"]),
        ("Round 2 — Revised Plans (with cross-input)", ["claude-v2", "codex-v2"]),
        ("Final Verdict", ["verdict"]),
    ]

    # Find files and read content
    files = {}
    file_meta = {}
    for fid, patterns, label, agent, _ in file_specs:
        path = find_file(args.plans_dir, patterns)
        if path:
            with open(path, "r") as f:
                files[fid] = f.read()
            size = os.path.getsize(path)
            size_str = f"{size // 1024}KB" if size >= 1024 else f"{size}B"
            file_meta[fid] = (label, agent, size_str)

    if not files:
        print(f"ERROR: No plan files found in {args.plans_dir}", file=sys.stderr)
        sys.exit(1)

    json_data = json.dumps(files)

    # Build HTML sections
    details_html = []
    for section_name, fids in sections_config:
        items = [fid for fid in fids if fid in files]
        if not items:
            continue
        details_html.append(f'<div class="section"><div class="section-title">{section_name}</div>')
        for fid in items:
            label, agent, size = file_meta[fid]
            tag = ""
            if agent == "CLAUDE":
                tag = '<span class="tag tag-claude">CLAUDE</span>'
            elif agent == "CODEX":
                tag = '<span class="tag tag-codex">CODEX</span>'
            elif agent == "VERDICT":
                tag = '<span class="tag tag-verdict">VERDICT</span>'
            details_html.append(
                f'<details><summary>{tag}<span>{label}</span>'
                f'<span class="tag-size">{size}</span></summary>'
                f'<div class="md" data-md="{fid}"></div></details>'
            )
        details_html.append("</div>")

    body = "\n".join(details_html)
    subtitle_html = f"<br>{args.subtitle}" if args.subtitle else ""

    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(args.title)}</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500;600;700;800&display=swap');
:root{{--bg:#0a0a0f;--surface:#111119;--surface2:#1a1a28;--border:#2a2a3a;--text:#d8d8e8;--muted:#8888a0;--accent:#6c5ce7;--accent2:#a29bfe;--green:#00b894;--orange:#fdcb6e;--pink:#fd79a8;--blue:#74b9ff;--mono:'JetBrains Mono',monospace;--sans:'Inter',system-ui,sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font-family:var(--sans);line-height:1.7;padding:2rem;max-width:1000px;margin:0 auto}}
h1{{font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;margin-bottom:0.3rem}}
.subtitle{{font-size:0.9rem;color:var(--muted);margin-bottom:2rem}}
.section{{margin:1.5rem 0}}
.section-title{{font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);margin-bottom:0.8rem;padding-bottom:0.4rem;border-bottom:1px solid var(--border)}}
details{{background:var(--surface);border:1px solid var(--border);border-radius:10px;margin:0.6rem 0;transition:border-color 0.2s}}
details[open]{{border-color:var(--accent)}}
summary{{padding:1rem 1.5rem;cursor:pointer;font-weight:700;font-size:0.95rem;display:flex;align-items:center;gap:0.8rem;user-select:none;list-style:none}}
summary::-webkit-details-marker{{display:none}}
summary::before{{content:"▶";font-size:0.7rem;color:var(--muted);transition:transform 0.2s}}
details[open] summary::before{{transform:rotate(90deg)}}
summary:hover{{color:var(--accent2)}}
.tag{{font-size:0.65rem;font-family:var(--mono);padding:0.15rem 0.5rem;border-radius:4px;font-weight:700;flex-shrink:0}}
.tag-claude{{background:#6c5ce720;color:var(--accent2);border:1px solid #6c5ce740}}
.tag-codex{{background:#00b89420;color:var(--green);border:1px solid #00b89440}}
.tag-verdict{{background:#fd79a820;color:var(--pink);border:1px solid #fd79a840}}
.tag-size{{color:var(--muted);font-size:0.8rem;font-weight:400;margin-left:auto;font-family:var(--mono)}}
.md{{padding:0 1.5rem 1.5rem;font-size:0.9rem;line-height:1.75;overflow-x:auto}}
.md h1{{font-size:1.4rem;margin:1.5rem 0 0.8rem;color:var(--text);border-bottom:1px solid var(--border);padding-bottom:0.4rem}}
.md h2{{font-size:1.15rem;margin:1.8rem 0 0.6rem;color:var(--accent2)}}
.md h3{{font-size:1rem;margin:1.2rem 0 0.4rem;color:var(--text)}}
.md h4{{font-size:0.9rem;margin:1rem 0 0.3rem;color:var(--muted);font-weight:700}}
.md p{{margin:0.6rem 0;color:var(--muted)}}
.md strong{{color:var(--text)}}
.md em{{color:var(--muted);font-style:italic}}
.md ul,.md ol{{padding-left:1.5rem;margin:0.5rem 0}}
.md li{{margin:0.25rem 0;color:var(--muted)}}
.md li strong{{color:var(--text)}}
.md code{{font-family:var(--mono);background:var(--surface2);padding:0.15rem 0.45rem;border-radius:4px;font-size:0.82em;color:var(--accent2);border:1px solid var(--border)}}
.md pre{{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:1rem;overflow-x:auto;margin:0.8rem 0}}
.md pre code{{background:none;border:none;padding:0;font-size:0.82rem;color:var(--muted);display:block;white-space:pre;overflow-x:auto}}
.md table{{width:100%;border-collapse:collapse;margin:0.8rem 0;font-size:0.85rem}}
.md th{{background:var(--surface2);color:var(--accent2);font-weight:700;text-align:left;padding:0.6rem 0.8rem;border:1px solid var(--border);font-size:0.8rem}}
.md td{{padding:0.5rem 0.8rem;border:1px solid var(--border);color:var(--muted);vertical-align:top}}
.md tr:hover td{{background:var(--surface2)}}
.md blockquote{{border-left:3px solid var(--accent);padding-left:1rem;margin:0.8rem 0;color:var(--muted)}}
.md hr{{border:none;height:1px;background:var(--border);margin:1.5rem 0}}
.md a{{color:var(--blue);text-decoration:none}}
.md a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<h1>{html.escape(args.title)}</h1>
<p class="subtitle">Codex (gpt-5.3-codex) vs Claude Code (claude-opus-4-6){subtitle_html}</p>
{body}
<script>
const docs = {json_data};
document.querySelectorAll('[data-md]').forEach(el => {{
  const key = el.dataset.md;
  if (docs[key]) el.innerHTML = marked.parse(docs[key]);
}});
</script>
</body>
</html>"""

    with open(args.output, "w") as f:
        f.write(template)

    print(f"Report saved: {args.output} ({os.path.getsize(args.output)} bytes)")


if __name__ == "__main__":
    main()
