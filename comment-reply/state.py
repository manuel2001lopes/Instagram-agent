"""
Persists the set of replied-to comment IDs to a local JSON file so the
agent never double-replies across restarts.
"""

import json
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "replied_comments.json")


def load_replied_ids() -> set[str]:
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, "r") as f:
        data = json.load(f)
    return set(data.get("replied_comment_ids", []))


def save_replied_ids(replied_ids: set[str]) -> None:
    tmp_path = STATE_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump({"replied_comment_ids": sorted(replied_ids)}, f, indent=2)
    os.replace(tmp_path, STATE_FILE)


def mark_replied(replied_ids: set[str], comment_id: str) -> set[str]:
    updated = replied_ids | {comment_id}
    save_replied_ids(updated)
    return updated
