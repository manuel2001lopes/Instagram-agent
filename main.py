"""
Instagram Welcome Agent
-----------------------
Polls Instagram for new followers and sends each one a short,
Claude-generated welcome DM.

Setup:
  1. Copy .env.example to .env and fill in your credentials.
  2. pip install -r requirements.txt
  3. python main.py

Required environment variables:
  INSTAGRAM_ACCESS_TOKEN  - Long-lived Instagram Graph API token
  INSTAGRAM_USER_ID       - Your Instagram Business/Creator account ID
  ANTHROPIC_API_KEY       - Anthropic API key

Optional:
  POLL_INTERVAL_SECONDS   - Seconds between follower checks (default: 60)
  WELCOME_TONE            - Tone for the welcome message (default: "friendly and warm")
"""

import os
import time
import logging

import anthropic
from dotenv import load_dotenv

from instagram_client import InstagramClient
from message_generator import generate_welcome_message
from state import load_known_followers, save_known_followers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def check_and_welcome_new_followers(
    ig: InstagramClient,
    claude: anthropic.Anthropic,
    known_ids: set[str],
    tone: str,
) -> set[str]:
    """
    Fetches current followers, detects new ones, sends welcome DMs,
    and returns the updated set of known follower IDs.
    """
    log.info("Fetching current followers...")
    current_followers = ig.get_followers()
    current_ids = {f["id"] for f in current_followers}
    followers_by_id = {f["id"]: f for f in current_followers}

    new_ids = current_ids - known_ids

    if not new_ids:
        log.info("No new followers.")
        return current_ids

    log.info(f"Found {len(new_ids)} new follower(s).")

    for follower_id in new_ids:
        follower = followers_by_id[follower_id]
        username = follower.get("username", follower_id)

        log.info(f"Generating welcome message for @{username}...")
        try:
            message = generate_welcome_message(claude, username, tone)
            log.info(f"  → Message: {message!r}")
        except Exception as e:
            log.error(f"  Failed to generate message for @{username}: {e}")
            continue

        log.info(f"  Sending DM to @{username} (id={follower_id})...")
        try:
            ig.send_message(follower_id, message)
            log.info(f"  ✓ Welcome DM sent to @{username}.")
        except Exception as e:
            log.error(f"  Failed to send DM to @{username}: {e}")

    return current_ids


def main():
    load_dotenv()

    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    poll_interval = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))
    tone = os.environ.get("WELCOME_TONE", "friendly and warm")

    missing = [
        name
        for name, val in [
            ("INSTAGRAM_ACCESS_TOKEN", access_token),
            ("INSTAGRAM_USER_ID", user_id),
            ("ANTHROPIC_API_KEY", anthropic_api_key),
        ]
        if not val
    ]
    if missing:
        raise SystemExit(
            f"Missing required environment variable(s): {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your credentials."
        )

    ig = InstagramClient(access_token, user_id)
    claude = anthropic.Anthropic(api_key=anthropic_api_key)

    log.info("Instagram Welcome Agent started.")
    log.info(f"Polling every {poll_interval}s | Tone: {tone!r}")

    known_ids = load_known_followers()

    if not known_ids:
        # First run: seed the state without sending messages to everyone
        log.info(
            "No existing follower state found. "
            "Seeding with current followers (no DMs will be sent on first run)."
        )
        try:
            followers = ig.get_followers()
            known_ids = {f["id"] for f in followers}
            save_known_followers(known_ids)
            log.info(f"Seeded {len(known_ids)} existing follower(s).")
        except Exception as e:
            log.error(f"Failed to seed followers: {e}")

    while True:
        try:
            updated_ids = check_and_welcome_new_followers(ig, claude, known_ids, tone)
            if updated_ids != known_ids:
                save_known_followers(updated_ids)
            known_ids = updated_ids
        except Exception as e:
            log.error(f"Error during follower check: {e}")

        log.info(f"Sleeping {poll_interval}s until next check...")
        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
