"""
Persists the set of known follower IDs to a local JSON file
so the agent can detect new followers across restarts.
"""

import json
import os

STATE_FILE = "known_followers.json"


def load_known_followers() -> set[str]:
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, "r") as f:
        data = json.load(f)
    return set(data.get("follower_ids", []))


def save_known_followers(follower_ids: set[str]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump({"follower_ids": list(follower_ids)}, f, indent=2)
