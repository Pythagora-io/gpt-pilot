#!/bin/bash

set -e

# Directory to monitor
MONITOR_DIR="$HOME/.vscode-server/cli/servers"
PATTERN="Stable-*"
EXCLUDE_SUFFIX=".staging"

# Command to execute when a new directory is detected
COMMAND="echo 'New Stable directory detected:'"

# Ensure inotify-tools is installed
if ! command -v inotifywait >/dev/null 2>&1; then
  echo "Error: inotifywait is not installed. Please install inotify-tools." >&2
  exit 1
fi

# Monitor for directory creation
echo "Monitoring $MONITOR_DIR for new directories matching $PATTERN..."

inotifywait -m -e create -e moved_to --format '%f' "$MONITOR_DIR" | while read -r NEW_ITEM; do
  # Check if the created item matches the pattern
  if [[ "$NEW_ITEM" == $PATTERN && "$NEW_ITEM" != *$EXCLUDE_SUFFIX ]]; then
    echo "Detected new directory: $NEW_ITEM"
    # Run the specified command
    # $COMMAND "$MONITOR_DIR/$NEW_ITEM"
    while [ ! -f "$HOME/.vscode-server/cli/servers/$NEW_ITEM/server/bin/code-server" ]; do
      sleep 1
    done
    mkdir -p /pythagora/pythagora-core/workspace/.vscode && printf '{\n  "gptPilot.isRemoteWs": true,\n  "gptPilot.useRemoteWs": false\n}' >  /pythagora/pythagora-core/workspace/.vscode/settings.json
    $HOME/.vscode-server/cli/servers/$NEW_ITEM/server/bin/code-server --install-extension /var/init_data/pythagora-vs-code.vsix
  fi
done
