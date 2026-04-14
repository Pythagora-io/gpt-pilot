---
name: linear-ticket-cleanup
description: "Clean up worktrees and feature directory after a Linear ticket PR is merged or closed. Use when told a PR was merged, when cleaning up a feature, or when a ticket is done."
---

# Linear Ticket Cleanup

Clean up the dev environment after a PR is merged or closed.

## Quick Path

```bash
local-worktree destroy <FEATURE>
```

This handles worktree removal, branch cleanup, and directory deletion.

Then do the post-cleanup steps manually.

## Manual Steps (if local-worktree destroy isn't available)

### 1. Remove Worktrees

```bash
cd $PRIMARY_REPO
git worktree remove "$FEATURES_DIR/$FEATURE/$REPO_NAME" --force 2>/dev/null

# If using a secondary repo:
cd $SECONDARY_REPO
git worktree remove "$FEATURES_DIR/$FEATURE/$SECONDARY_REPO_NAME" --force 2>/dev/null
```

### 2. Clean Branches

```bash
cd $PRIMARY_REPO
git branch -D "feature/${FEATURE}" 2>/dev/null

# If using a secondary repo:
cd $SECONDARY_REPO
git branch -D "feature/${FEATURE}" 2>/dev/null
```

### 3. Clean Registry

```python
import json
f = '$FEATURES_DIR/port-assignments.json'
data = json.load(open(f))
data['features'].pop(FEATURE, None)
json.dump(data, open(f, 'w'), indent=2)
```

### 4. Remove Feature Directory

```bash
rm -rf "$FEATURES_DIR/$FEATURE"
```

## Post-Cleanup Steps

### 5. Post Closing Comments

**On the PR:**

```
🧹 Cleanup complete:
- Worktrees and branches removed
- Feature directory deleted
```

**On the Linear ticket (if merged):**

```
✅ PR #{N} has been merged!

🧹 Dev environment cleaned up:
- Worktrees and branches removed
- Feature directory deleted

Ticket moved to Done.
```

**On the Linear ticket (if closed without merge):**

```
❌ PR #{N} was closed without merging.

🧹 Dev environment cleaned up:
- Worktrees and branches removed
- Feature directory deleted
```

### 6. Update Linear Ticket State

- If **merged**: Move to "Done" (use your workspace's Done state ID)
- If **closed**: Leave in current state

### 7. Notify User

```
📍 {TICKET_ID}: PR #{N} {merged/closed}. Dev environment cleaned up.
{If merged: Ticket moved to Done.}
```
