---
name: figma
description: "Fetch design details from Figma — file structure, components, styles, images, variables, and node search. Use when the user asks to look at a Figma design, extract design tokens, export assets, inspect a frame/component, or reference a Figma file during implementation. Triggers on phrases like 'check the Figma', 'get the design from Figma', 'export this frame', 'what does the Figma show', or when a Figma file URL is shared."
---

# Figma

Interact with Figma designs via the REST API. Use this skill to inspect files, extract design details, export images, and search for specific frames or components.

## Setup

1. Retrieve the API key: `get_credential(service="figma")`
2. Export it: `export FIGMA_API_KEY="<key>"`
3. Run commands via the script at `scripts/figma-api.sh` (paths relative to this skill directory)

## Extracting a File Key from a Figma URL

Figma URLs follow this pattern:

```
https://www.figma.com/design/<FILE_KEY>/<file-name>?node-id=<NODE_ID>
https://www.figma.com/file/<FILE_KEY>/<file-name>
```

Extract the `FILE_KEY` segment. Node IDs in the URL use `-` as separator; convert to `:` for API calls (e.g. `1-234` → `1:234`).

## Commands

All commands go through `scripts/figma-api.sh`:

| Command                               | Description                                              |
| ------------------------------------- | -------------------------------------------------------- |
| `me`                                  | Current authenticated user info                          |
| `file <KEY> [depth]`                  | Get file structure (use depth=1 or 2 to limit)           |
| `file-nodes <KEY> <IDS>`              | Get specific nodes (comma-separated, e.g. `1:234,5:678`) |
| `images <KEY> <IDS> [format] [scale]` | Export node images (png/svg/jpg/pdf, scale 1-4)          |
| `comments <KEY>`                      | Get file comments                                        |
| `components <KEY>`                    | List components in file                                  |
| `styles <KEY>`                        | List styles in file                                      |
| `team-projects <TEAM_ID>`             | List team projects                                       |
| `project-files <PROJECT_ID>`          | List project files                                       |
| `variables <KEY>`                     | Get local variables/design tokens                        |
| `search <KEY> <QUERY>`                | Search node names in file                                |

## Common Workflows

### Inspect a design for implementation

```bash
# 1. Get high-level structure (depth=1 for pages only)
./scripts/figma-api.sh file <KEY> 1

# 2. Find the frame you need
./scripts/figma-api.sh search <KEY> "Dashboard"

# 3. Get detailed node info
./scripts/figma-api.sh file-nodes <KEY> "123:456"

# 4. Export as image for reference
./scripts/figma-api.sh images <KEY> "123:456" png 2
```

### Extract design tokens

```bash
# Get variables (colors, spacing, typography tokens)
./scripts/figma-api.sh variables <KEY>

# Get styles (fill styles, text styles, effect styles)
./scripts/figma-api.sh styles <KEY>
```

### Export assets

```bash
# Export as SVG for icons
./scripts/figma-api.sh images <KEY> "node1,node2" svg 1

# Export as PNG @2x for raster assets
./scripts/figma-api.sh images <KEY> "node1" png 2
```

## Tips

- **Depth parameter:** Large files can return huge JSON. Always use `depth=1` or `depth=2` for initial exploration, then drill into specific nodes with `file-nodes`.
- **Node IDs:** Use colon format (`1:234`) not dash format (`1-234`). Convert from URL format if needed.
- **Image export:** Returns URLs that expire. Download them promptly if you need to keep them.
- **Rate limits:** Figma API has rate limits. Space out requests; avoid tight loops over many nodes.
- **Credential:** Always retrieve via `get_credential(service="figma")` — never hardcode the key.
