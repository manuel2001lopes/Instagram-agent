"""
Instagram Comment Reply Agent
------------------------------
Polls Manuel's recent Instagram posts for new comments and replies to
each one with a Claude-generated message in his voice.

Setup:
  1. Copy ../.env.example to ../.env and fill in your credentials.
  2. pip install -r ../requirements.txt
  3. python comment_agent.py          # run from the comment-reply/ directory

Required environment variables (loaded from ../.env):
  INSTAGRAM_ACCESS_TOKEN    — Long-lived Instagram Graph API token
  INSTAGRAM_USER_ID         — Your Instagram Business/Creator account ID
  ANTHROPIC_API_KEY         — Anthropic API key

Optional:
  COMMENT_POLL_INTERVAL_SECONDS  — Seconds between comment checks (default: 300)

Required Instagram permissions:
  instagram_basic             — list media, read comments
  instagram_manage_comments   — post replies
"""

import logging
import os
import re
import time

import anthropic
from dotenv import load_dotenv

from instagram_comments import InstagramCommentsClient
from reply_generator import generate_reply
from state import load_replied_ids, mark_replied


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_HASHTAG_RE = re.compile(r"#\w+")
_EMOJI_ONLY_RE = re.compile(
    r"^[\U00010000-\U0010ffff"
    r"\U0001F300-\U0001F9FF"
    r"☀-➿"
    r"︀-️"
    r"‍"
    r"\s]*$"
)

MIN_COMMENT_LENGTH = 3
MAX_HASHTAGS_ALLOWED = 3


def should_skip_comment(comment_text: str) -> tuple[bool, str]:
    stripped = comment_text.strip()

    if len(stripped.replace(" ", "")) < MIN_COMMENT_LENGTH:
        return True, "too short"

    if _EMOJI_ONLY_RE.match(stripped):
        return True, "emoji-only"

    if _URL_RE.search(stripped):
        return True, "contains URL (possible spam)"

    hashtag_count = len(_HASHTAG_RE.findall(stripped))
    if hashtag_count > MAX_HASHTAGS_ALLOWED:
        return True, f"excessive hashtags ({hashtag_count})"

    return False, ""


def process_comments(
    ig: InstagramCommentsClient,
    claude: anthropic.Anthropic,
    user_id: str,
    replied_ids: set[str],
) -> set[str]:
    media_items = ig.get_recent_media(limit=10)
    log.info(f"Checking {len(media_items)} recent post(s) for new comments...")

    for media in media_items:
        media_id = media["id"]

        try:
            comments = ig.get_comments(media_id)
        except Exception as exc:
            log.error(f"  Could not fetch comments for {media_id}: {exc}")
            continue

        new_comments = [c for c in comments if c["id"] not in replied_ids]
        if not new_comments:
            continue

        log.info(f"  {len(new_comments)} new comment(s) on post {media_id}.")

        for comment in new_comments:
            comment_id = comment["id"]
            username = comment.get("username", "unknown")
            text = comment.get("text", "")

            if comment.get("from", {}).get("id") == user_id:
                log.debug(f"    Skipping own comment {comment_id}.")
                replied_ids = mark_replied(replied_ids, comment_id)
                continue

            skip, reason = should_skip_comment(text)
            if skip:
                log.info(f"    Skipping @{username}: {reason}.")
                replied_ids = mark_replied(replied_ids, comment_id)
                continue

            log.info(f"    Replying to @{username}: {text!r}")

            try:
                reply_text = generate_reply(claude, commenter_username=username, comment_text=text)
                log.info(f"      → {reply_text!r}")
            except Exception as exc:
                log.error(f"      Failed to generate reply: {exc}")
                continue

            try:
                ig.reply_to_comment(comment_id, reply_text)
                log.info(f"      Reply posted.")
            except Exception as exc:
                log.error(f"      Failed to post reply: {exc}")
                continue

            replied_ids = mark_replied(replied_ids, comment_id)

    return replied_ids


def main() -> None:
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(dotenv_path=env_path)

    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    poll_interval = int(os.environ.get("COMMENT_POLL_INTERVAL_SECONDS", "300"))

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

    ig = InstagramCommentsClient(access_token, user_id)
    claude = anthropic.Anthropic(api_key=anthropic_api_key)

    log.info("Instagram Comment Reply Agent started.")
    log.info(f"Polling every {poll_interval}s for new comments.")

    replied_ids = load_replied_ids()
    log.info(f"Loaded {len(replied_ids)} already-replied comment ID(s) from state.")

    while True:
        try:
            replied_ids = process_comments(ig, claude, user_id, replied_ids)
        except Exception as exc:
            log.error(f"Error during comment check: {exc}")

        log.info(f"Sleeping {poll_interval}s until next check...")
        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
