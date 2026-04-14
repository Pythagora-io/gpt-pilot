#!/usr/bin/env bash
# figma-api.sh — Figma REST API wrapper
# Usage:
#   figma-api.sh me                           — Current user info
#   figma-api.sh file <FILE_KEY>              — Get full file structure
#   figma-api.sh file-nodes <FILE_KEY> <IDS>  — Get specific nodes (comma-separated IDs)
#   figma-api.sh images <FILE_KEY> <IDS> [format] [scale] — Export images (png/svg/jpg/pdf, scale 1-4)
#   figma-api.sh comments <FILE_KEY>          — Get comments on a file
#   figma-api.sh components <FILE_KEY>        — Get components in a file
#   figma-api.sh styles <FILE_KEY>            — Get styles in a file
#   figma-api.sh team-projects <TEAM_ID>      — List projects in a team
#   figma-api.sh project-files <PROJECT_ID>   — List files in a project
#   figma-api.sh variables <FILE_KEY>         — Get local variables
#   figma-api.sh search <FILE_KEY> <QUERY>    — Search node names in file (local grep)

set -euo pipefail

FIGMA_API_KEY="${FIGMA_API_KEY:-}"
BASE="https://api.figma.com/v1"

cmd="${1:-help}"

# Allow help without API key
if [[ "$cmd" == "help" ]]; then
  echo "Figma API CLI — Usage:"
  echo "  figma-api.sh me"
  echo "  figma-api.sh file <FILE_KEY> [depth]"
  echo "  figma-api.sh file-nodes <FILE_KEY> <IDS>"
  echo "  figma-api.sh images <FILE_KEY> <IDS> [format] [scale]"
  echo "  figma-api.sh comments <FILE_KEY>"
  echo "  figma-api.sh components <FILE_KEY>"
  echo "  figma-api.sh styles <FILE_KEY>"
  echo "  figma-api.sh team-projects <TEAM_ID>"
  echo "  figma-api.sh project-files <PROJECT_ID>"
  echo "  figma-api.sh variables <FILE_KEY>"
  echo "  figma-api.sh search <FILE_KEY> <QUERY>"
  exit 0
fi

if [[ -z "$FIGMA_API_KEY" ]]; then
  echo "Error: FIGMA_API_KEY not set" >&2
  exit 1
fi

_curl() {
  curl -sS -H "X-Figma-Token: $FIGMA_API_KEY" "$@"
}
shift || true

case "$cmd" in
  me)
    _curl "$BASE/me" | python3 -m json.tool
    ;;

  file)
    FILE_KEY="${1:?Missing FILE_KEY}"
    # Optional: depth, geometry, plugin_data
    DEPTH="${2:-}"
    URL="$BASE/files/$FILE_KEY"
    [[ -n "$DEPTH" ]] && URL="$URL?depth=$DEPTH"
    _curl "$URL" | python3 -m json.tool
    ;;

  file-nodes)
    FILE_KEY="${1:?Missing FILE_KEY}"
    IDS="${2:?Missing node IDS (comma-separated)}"
    _curl "$BASE/files/$FILE_KEY/nodes?ids=$IDS" | python3 -m json.tool
    ;;

  images)
    FILE_KEY="${1:?Missing FILE_KEY}"
    IDS="${2:?Missing node IDS}"
    FORMAT="${3:-png}"
    SCALE="${4:-2}"
    _curl "$BASE/images/$FILE_KEY?ids=$IDS&format=$FORMAT&scale=$SCALE" | python3 -m json.tool
    ;;

  comments)
    FILE_KEY="${1:?Missing FILE_KEY}"
    _curl "$BASE/files/$FILE_KEY/comments" | python3 -m json.tool
    ;;

  components)
    FILE_KEY="${1:?Missing FILE_KEY}"
    _curl "$BASE/files/$FILE_KEY/components" | python3 -m json.tool
    ;;

  styles)
    FILE_KEY="${1:?Missing FILE_KEY}"
    _curl "$BASE/files/$FILE_KEY/styles" | python3 -m json.tool
    ;;

  team-projects)
    TEAM_ID="${1:?Missing TEAM_ID}"
    _curl "$BASE/teams/$TEAM_ID/projects" | python3 -m json.tool
    ;;

  project-files)
    PROJECT_ID="${1:?Missing PROJECT_ID}"
    _curl "$BASE/projects/$PROJECT_ID/files" | python3 -m json.tool
    ;;

  variables)
    FILE_KEY="${1:?Missing FILE_KEY}"
    _curl "$BASE/files/$FILE_KEY/variables/local" | python3 -m json.tool
    ;;

  search)
    FILE_KEY="${1:?Missing FILE_KEY}"
    QUERY="${2:?Missing search query}"
    # Fetch file with depth=2 for speed, grep node names
    _curl "$BASE/files/$FILE_KEY?depth=3" | python3 -c "
import json, sys, re
data = json.load(sys.stdin)
query = '${QUERY}'.lower()
def walk(node, path=''):
    name = node.get('name', '')
    full_path = f'{path}/{name}' if path else name
    if query in name.lower():
        ntype = node.get('type', '?')
        nid = node.get('id', '?')
        print(f'  [{ntype}] id={nid}  {full_path}')
    for child in node.get('children', []):
        walk(child, full_path)
doc = data.get('document', {})
walk(doc)
"
    ;;

  *)
    echo "Unknown command: $cmd — run 'figma-api.sh help' for usage" >&2
    exit 1
    ;;
esac
