#!/bin/bash

# This script counts all lines of code in a Node.js repository
# including HTML, CSS, JS, Pug, etc., while excluding irrelevant folders and files.
# It then sorts the files by the number of lines of code in ascending order
# and prints the total number of processed files.

# Check if an argument is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_nodejs_repo>"
    exit 1
fi

# Use the first argument as the repository directory
REPO_DIR="$1"

# Find and store the relevant files in a temporary file to avoid processing them multiple times
tempfile=$(mktemp)
find "$REPO_DIR" \
     \( -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.pug' -o -name '*.ejs' -o -name '*.svelte' -o -name '*.py' -o -name '*.ts' -o -name '*.xml' -o -name '*.java' -o -name '*.less' -o -name '*.json' -o -name '*.sample' \) \
     ! -path '*/node_modules/*' ! -path '*/.git/*' \
     ! -name '.gitignore' ! -name 'package-lock.json' \
     -print0 > "$tempfile"

# Count the lines for each file and sort them
xargs -0 wc -l < "$tempfile" | sort -n

# Count and print the total number of processed files
total_files=$(xargs -0 echo < "$tempfile" | wc -w)
echo "Total processed files: $total_files"

# Clean up by removing the temporary file
rm "$tempfile"

