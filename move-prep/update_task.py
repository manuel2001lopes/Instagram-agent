#!/usr/bin/env python3
"""
Update task status in checklist.json
Usage:
  python update_task.py <task_id> done           — mark task as done
  python update_task.py <task_id> pending        — mark task as pending (undo)
  python update_task.py <task_id> note "text"   — add/update notes on a task
  python update_task.py list                     — list all tasks with IDs and status
  python update_task.py list <category>          — list tasks in a specific category

Examples:
  python update_task.py visa_002 done
  python update_task.py flight_001 done
  python update_task.py accom_001 pending
  python update_task.py visa_001 note "Picked up on Aug 25, all good"
  python update_task.py list
  python update_task.py list documents_visa
"""

import json
import sys
from datetime import datetime
from pathlib import Path

CHECKLIST_PATH = Path(__file__).parent / "checklist.json"

CATEGORY_LABELS = {
    "documents_visa": "Documents & Visa",
    "flights": "Flights",
    "accommodation": "Accommodation",
    "finances": "Finances",
    "phone_connectivity": "Phone & Connectivity",
    "health_insurance": "Health & Insurance",
    "content_creation": "Content Creation",
    "packing": "Packing",
    "admin_logistics": "Admin & Logistics",
}

STATUS_ICON = {True: "[x]", False: "[ ]"}
PRIORITY_ICON = {"critical": "!!!!", "high": "!! ", "medium": "!  ", "low": "   "}


def load_checklist() -> dict:
    with open(CHECKLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_checklist(data: dict) -> None:
    data["meta"]["last_updated"] = datetime.today().date().isoformat()
    with open(CHECKLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_task(tasks: list, task_id: str) -> dict | None:
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def cmd_mark_done(task_id: str, done: bool) -> None:
    data = load_checklist()
    task = find_task(data["tasks"], task_id)
    if task is None:
        print(f"ERROR: Task '{task_id}' not found.", file=sys.stderr)
        print("Run 'python update_task.py list' to see all task IDs.", file=sys.stderr)
        sys.exit(1)
    old_status = "done" if task["done"] else "pending"
    new_status = "done" if done else "pending"
    if task["done"] == done:
        print(f"Task '{task_id}' is already {new_status}. No change.")
        return
    task["done"] = done
    save_checklist(data)
    print(f"Updated: [{task['id']}] {task['title']}")
    print(f"  Status: {old_status} -->> {new_status}")


def cmd_add_note(task_id: str, note: str) -> None:
    data = load_checklist()
    task = find_task(data["tasks"], task_id)
    if task is None:
        print(f"ERROR: Task '{task_id}' not found.", file=sys.stderr)
        sys.exit(1)
    old_note = task.get("notes", "")
    task["notes"] = note
    save_checklist(data)
    print(f"Updated notes for: [{task['id']}] {task['title']}")
    if old_note:
        print(f"  Old notes: {old_note}")
    print(f"  New notes: {note}")


def cmd_list(category_filter: str | None = None) -> None:
    data = load_checklist()
    tasks = data["tasks"]
    if category_filter:
        tasks = [t for t in tasks if t["category"] == category_filter]
        if not tasks:
            tasks = [t for t in data["tasks"] if category_filter.lower() in t["category"].lower()]
        if not tasks:
            print(f"No tasks found for category '{category_filter}'.")
            return
    by_category: dict[str, list] = {}
    for t in tasks:
        by_category.setdefault(t["category"], []).append(t)
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    print(f"\nMove Prep Checklist — {data['meta']['move_date']} — {data['meta']['destination']}")
    print(f"Progress: {done_count}/{total} tasks complete\n")
    for cat_key in sorted(by_category.keys()):
        cat_label = CATEGORY_LABELS.get(cat_key, cat_key)
        cat_tasks = by_category[cat_key]
        cat_done = sum(1 for t in cat_tasks if t["done"])
        print(f"\n{'='*55}")
        print(f"  {cat_label.upper()} ({cat_done}/{len(cat_tasks)} done)")
        print(f"{'='*55}")
        for t in sorted(cat_tasks, key=lambda x: (x["done"], x["deadline"])):
            status = STATUS_ICON[t["done"]]
            priority = PRIORITY_ICON.get(t["priority"], "   ")
            print(f"  {status} {priority} [{t['id']}]  {t['title']}")
            print(f"           Deadline: {t['deadline']}  |  Priority: {t['priority']}")
            if t.get("notes") and not t["done"]:
                note_preview = t['notes'][:100] + ('...' if len(t.get('notes', '')) > 100 else '')
                print(f"           Note: {note_preview}")
    print()


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0)
    if args[0] == "list":
        cmd_list(args[1] if len(args) > 1 else None)
        return
    if len(args) < 2:
        print("ERROR: Not enough arguments.", file=sys.stderr)
        sys.exit(1)
    task_id, action = args[0], args[1].lower()
    if action == "done":
        cmd_mark_done(task_id, done=True)
    elif action == "pending":
        cmd_mark_done(task_id, done=False)
    elif action == "note":
        if len(args) < 3:
            print("ERROR: Please provide note text after 'note'.", file=sys.stderr)
            sys.exit(1)
        cmd_add_note(task_id, args[2])
    else:
        print(f"ERROR: Unknown action '{action}'. Use: done, pending, or note", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
