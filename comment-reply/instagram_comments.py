"""
Instagram Graph API wrapper for comment-related operations.

Required permissions:
  - instagram_basic              — list media and read comments
  - instagram_manage_comments   — post replies to comments
"""

import requests

GRAPH_API_BASE = "https://graph.instagram.com/v21.0"


class InstagramCommentsClient:
    def __init__(self, access_token: str, user_id: str):
        self.access_token = access_token
        self.user_id = user_id
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{GRAPH_API_BASE}/{path}"
        params = dict(params or {})
        params["access_token"] = self.access_token
        response = self._session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, data: dict) -> dict:
        url = f"{GRAPH_API_BASE}/{path}"
        data = dict(data)
        data["access_token"] = self.access_token
        response = self._session.post(url, data=data)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_recent_media(self, limit: int = 10) -> list[dict]:
        """
        Returns the user's most recent media posts (up to *limit*).

        Each item contains at least: id, timestamp.

        GET /{ig-user-id}/media
        """
        data = self._get(
            f"{self.user_id}/media",
            {"fields": "id,timestamp", "limit": limit},
        )
        return data.get("data", [])

    def get_comments(self, media_id: str) -> list[dict]:
        """
        Returns all comments on a single media post, paging automatically.

        Each item contains: id, text, username, timestamp.

        GET /{media-id}/comments?fields=id,text,username,timestamp
        """
        comments: list[dict] = []
        params: dict = {"fields": "id,text,username,timestamp"}

        while True:
            data = self._get(f"{media_id}/comments", params)
            comments.extend(data.get("data", []))

            # Follow cursor-based pagination
            paging = data.get("paging", {})
            next_cursor = paging.get("cursors", {}).get("after")
            if not next_cursor or not paging.get("next"):
                break
            params["after"] = next_cursor

        return comments

    def reply_to_comment(self, comment_id: str, message: str) -> dict:
        """
        Posts a reply to a specific comment.

        POST /{comment-id}/replies  with fields: message, access_token

        Requires: instagram_manage_comments permission.
        Returns the API response dict (contains 'id' of the new reply).
        """
        return self._post(
            f"{comment_id}/replies",
            {"message": message},
        )
