"""
Instagram Graph API client.

Requires a Business or Creator account linked to a Facebook Page,
and a long-lived access token with the following permissions:
  - instagram_basic
  - instagram_manage_messages
"""

import requests


GRAPH_API_BASE = "https://graph.instagram.com/v21.0"


class InstagramClient:
    def __init__(self, access_token: str, user_id: str):
        self.access_token = access_token
        self.user_id = user_id
        self._session = requests.Session()

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{GRAPH_API_BASE}/{path}"
        params = params or {}
        params["access_token"] = self.access_token
        response = self._session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, json: dict) -> dict:
        url = f"{GRAPH_API_BASE}/{path}"
        json["access_token"] = self.access_token
        response = self._session.post(url, json=json)
        response.raise_for_status()
        return response.json()

    def get_followers(self) -> list[dict]:
        """
        Returns a list of followers as dicts with 'id' and 'username'.
        Paginates through all pages automatically.

        Requires: instagram_basic permission.
        Note: Only returns followers of Business/Creator accounts.
        """
        followers = []
        params = {"fields": "id,username"}
        path = f"{self.user_id}/followers"

        while True:
            data = self._get(path, params)
            followers.extend(data.get("data", []))

            # Follow pagination cursors
            next_cursor = (
                data.get("paging", {})
                .get("cursors", {})
                .get("after")
            )
            if not next_cursor or not data.get("paging", {}).get("next"):
                break
            params["after"] = next_cursor

        return followers

    def send_message(self, recipient_id: str, text: str) -> dict:
        """
        Sends a direct message to an Instagram user.

        Requires: instagram_manage_messages permission.
        The recipient must follow your account or have DMs from
        non-followers enabled in their settings.
        """
        return self._post(
            f"{self.user_id}/messages",
            {
                "recipient": {"id": recipient_id},
                "message": {"text": text},
            },
        )
