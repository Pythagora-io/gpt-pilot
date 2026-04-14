#!/usr/bin/env python3
"""
QA Queue Manager — deterministic queue operations.

Usage:
  python3 queue.py status
  python3 queue.py add --id PAZ-XXX --type ticket --description "..." [--prs repo#501,agent#141] [--env qa] [--requestedBy <name>] [--slackChannel <channel-id>] [--slackThread 1775...]
  python3 queue.py complete --result "13 PASS, 0 FAIL" [--reportUrl https://...]
  python3 queue.py block --reason "Needs OpenAI OAuth credentials"
  python3 queue.py update-phase --phase phase3 [--notes "Completed TC-1.1 through TC-2.3"]
  python3 queue.py edit --field testFolder --value "test-runs/qa-PAZ-XXX-20260409"
  python3 queue.py cancel
  python3 queue.py unblock --id PAZ-XXX
  python3 queue.py start-next

All list transitions (complete, block, cancel) automatically promote the first
todo item to current. This is atomic — one read, one write, no dropped items.
"""

import json
import sys
import os
import shutil
from datetime import datetime, timezone

QUEUE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "qa-queue.json"
)
MAX_COMPLETED = 15


def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return {"current": None, "todo": [], "blocked": [], "completed": []}
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(q):
    with open(QUEUE_FILE, "w") as f:
        json.dump(q, f, indent=2, ensure_ascii=False)
        f.write("\n")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def promote_next(q):
    """Move first todo item to current. Returns the promoted item or None."""
    if q["todo"]:
        item = q["todo"].pop(0)
        item["phase"] = "qa-phase0"
        item["lastPhaseUpdate"] = now_iso()
        if "startedAt" not in item:
            item["startedAt"] = now_iso()
        q["current"] = item
        return item
    else:
        q["current"] = None
        return None


def trim_completed(q):
    """Enforce max completed items, delete old test folders."""
    while len(q["completed"]) > MAX_COMPLETED:
        old = q["completed"].pop()  # remove oldest (last in list)
        folder = old.get("testFolder")
        if folder:
            full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", folder)
            full_path = os.path.normpath(full_path)
            if os.path.isdir(full_path):
                shutil.rmtree(full_path, ignore_errors=True)


def cmd_status(q, args):
    current_id = q["current"]["id"] if q["current"] else "none"
    current_phase = q["current"].get("phase", "?") if q["current"] else ""
    todo_ids = [t["id"] for t in q["todo"]]
    blocked_ids = [t["id"] for t in q["blocked"]]
    completed_count = len(q["completed"])

    print(f"current: {current_id}" + (f" ({current_phase})" if current_phase else ""))
    print(f"todo: {todo_ids if todo_ids else '[]'}")
    print(f"blocked: {blocked_ids if blocked_ids else '[]'}")
    print(f"completed: {completed_count} items")

    if q["current"]:
        last = q["current"].get("lastPhaseUpdate", "")
        print(f"current.lastPhaseUpdate: {last}")
        notes = q["current"].get("notes", "")
        if notes:
            print(f"current.notes: {notes}")


def cmd_add(q, args):
    if not args.get("id"):
        print("ERROR: --id is required", file=sys.stderr)
        sys.exit(1)

    entry = {
        "id": args["id"],
        "type": args.get("type", "ticket"),
        "description": args.get("description", ""),
        "prs": args.get("prs", "").split(",") if args.get("prs") else [],
        "environment": args.get("env", "qa"),
        "requestedBy": args.get("requestedBy", ""),
        "slackChannel": args.get("slackChannel", ""),
        "slackThreadTs": args.get("slackThread", ""),
        "addedAt": now_iso(),
    }

    if q["current"] is None:
        # No test running — start immediately
        entry["phase"] = "qa-phase0"
        entry["startedAt"] = now_iso()
        entry["lastPhaseUpdate"] = now_iso()
        q["current"] = entry
        save_queue(q)
        print(f"STARTED: {entry['id']} set as current (queue was empty)")
    else:
        q["todo"].append(entry)
        save_queue(q)
        position = len(q["todo"])
        print(f"QUEUED: {entry['id']} added to todo (position #{position})")
        print(f"CURRENT: {q['current']['id']} is running")


def cmd_complete(q, args):
    if not q["current"]:
        print("ERROR: nothing is current — can't complete", file=sys.stderr)
        sys.exit(1)

    item = q["current"]
    item["completedAt"] = now_iso()
    item["result"] = args.get("result", "completed")
    if args.get("reportUrl"):
        item["reportUrl"] = args["reportUrl"]

    # Insert at beginning of completed (newest first)
    q["completed"].insert(0, item)
    trim_completed(q)

    # Promote next — atomic with the completion
    promoted = promote_next(q)
    save_queue(q)

    print(f"COMPLETED: {item['id']} — {item['result']}")
    if promoted:
        print(f"NEXT: {promoted['id']} promoted to current")
    else:
        print("NEXT: none (queue empty)")


def cmd_block(q, args):
    if not q["current"]:
        print("ERROR: nothing is current — can't block", file=sys.stderr)
        sys.exit(1)

    item = q["current"]
    item["blockedReason"] = args.get("reason", "Blocked — needs input")
    item["blockedAt"] = now_iso()

    q["blocked"].append(item)

    # Promote next — atomic
    promoted = promote_next(q)
    save_queue(q)

    print(f"BLOCKED: {item['id']} — {item['blockedReason']}")
    if promoted:
        print(f"NEXT: {promoted['id']} promoted to current")
    else:
        print("NEXT: none (queue empty)")


def cmd_update_phase(q, args):
    if not q["current"]:
        print("ERROR: nothing is current — can't update phase", file=sys.stderr)
        sys.exit(1)

    if args.get("phase"):
        q["current"]["phase"] = args["phase"]
    q["current"]["lastPhaseUpdate"] = now_iso()
    if args.get("notes"):
        q["current"]["notes"] = args["notes"]

    save_queue(q)
    print(f"UPDATED: {q['current']['id']} → phase={q['current']['phase']}")


def cmd_edit(q, args):
    if not q["current"]:
        print("ERROR: nothing is current — can't edit", file=sys.stderr)
        sys.exit(1)

    field = args.get("field")
    value = args.get("value")
    if not field or value is None:
        print("ERROR: --field and --value are required", file=sys.stderr)
        sys.exit(1)

    q["current"][field] = value
    save_queue(q)
    print(f"EDITED: {q['current']['id']}.{field} = {value}")


def cmd_cancel(q, args):
    if not q["current"]:
        print("ERROR: nothing is current — can't cancel", file=sys.stderr)
        sys.exit(1)

    item = q["current"]
    item["completedAt"] = now_iso()
    item["result"] = "CANCELLED"

    q["completed"].insert(0, item)
    trim_completed(q)

    promoted = promote_next(q)
    save_queue(q)

    print(f"CANCELLED: {item['id']}")
    if promoted:
        print(f"NEXT: {promoted['id']} promoted to current")
    else:
        print("NEXT: none (queue empty)")


def cmd_unblock(q, args):
    target_id = args.get("id")
    if not target_id:
        print("ERROR: --id is required", file=sys.stderr)
        sys.exit(1)

    # Find in blocked list
    found = None
    for i, item in enumerate(q["blocked"]):
        if item["id"] == target_id:
            found = q["blocked"].pop(i)
            break

    if not found:
        print(f"ERROR: {target_id} not found in blocked list", file=sys.stderr)
        sys.exit(1)

    # Remove blocked fields
    found.pop("blockedReason", None)
    found.pop("blockedAt", None)

    if q["current"] is None:
        # Start immediately
        found["phase"] = "qa-phase0"
        found["lastPhaseUpdate"] = now_iso()
        q["current"] = found
        save_queue(q)
        print(f"UNBLOCKED: {target_id} → set as current (nothing was running)")
    else:
        # Add to front of todo
        q["todo"].insert(0, found)
        save_queue(q)
        print(f"UNBLOCKED: {target_id} → added to front of todo")
        print(f"CURRENT: {q['current']['id']} is still running")


def cmd_start_next(q, args):
    """For watchdog: if current is null and todo has items, promote."""
    if q["current"] is not None:
        print(f"SKIP: {q['current']['id']} is already running")
        return

    if not q["todo"]:
        print("SKIP: todo is empty, nothing to start")
        return

    promoted = promote_next(q)
    save_queue(q)
    print(f"STARTED: {promoted['id']} promoted from todo to current")


def parse_args(argv):
    """Simple arg parser: command + --key value pairs."""
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = argv[1]
    args = {}
    i = 2
    while i < len(argv):
        if argv[i].startswith("--"):
            key = argv[i][2:]
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                args[key] = argv[i + 1]
                i += 2
            else:
                args[key] = True
                i += 1
        else:
            i += 1

    return command, args


def main():
    command, args = parse_args(sys.argv)
    q = load_queue()

    commands = {
        "status": cmd_status,
        "add": cmd_add,
        "complete": cmd_complete,
        "block": cmd_block,
        "update-phase": cmd_update_phase,
        "edit": cmd_edit,
        "cancel": cmd_cancel,
        "unblock": cmd_unblock,
        "start-next": cmd_start_next,
    }

    if command not in commands:
        print(f"ERROR: unknown command '{command}'", file=sys.stderr)
        print(f"Available: {', '.join(commands.keys())}", file=sys.stderr)
        sys.exit(1)

    commands[command](q, args)


if __name__ == "__main__":
    main()
