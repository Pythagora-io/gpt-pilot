#!/bin/bash
# Script to update your local branch with upstream changes

echo "🔄 Fetching latest changes from upstream..."
git fetch origin main

echo "📊 Current branch: $(git branch --show-current)"
echo "📈 Commits behind upstream: $(git rev-list --count HEAD..origin/main)"

echo ""
echo "Choose an option:"
echo "1) Rebase onto latest upstream (recommended)"
echo "2) Merge upstream changes"
echo "3) Just view the differences"
echo "4) Cancel"

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "🔧 Rebasing onto origin/main..."
        git rebase origin/main
        if [ $? -eq 0 ]; then
            echo "✅ Rebase successful!"
        else
            echo "⚠️  Conflicts detected. Resolve them and run 'git rebase --continue'"
        fi
        ;;
    2)
        echo "🔧 Merging origin/main..."
        git merge origin/main
        if [ $? -eq 0 ]; then
            echo "✅ Merge successful!"
        else
            echo "⚠️  Conflicts detected. Resolve them and commit."
        fi
        ;;
    3)
        echo "📝 Showing differences..."
        git log --oneline HEAD..origin/main
        echo ""
        echo "To see detailed changes: git diff HEAD...origin/main"
        ;;
    4)
        echo "❌ Cancelled"
        ;;
    *)
        echo "Invalid choice"
        ;;
esac