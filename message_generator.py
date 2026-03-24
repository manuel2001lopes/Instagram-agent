"""
Uses Claude (claude-opus-4-6) to generate a short, personalized
welcome message for a new Instagram follower.
"""

import anthropic


def generate_welcome_message(
    client: anthropic.Anthropic,
    username: str,
    tone: str = "friendly and warm",
) -> str:
    """
    Asks Claude to write a concise welcome DM for a new follower.

    Returns the plain text message to send.
    """
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=256,
        thinking={"type": "adaptive"},
        system=(
            "You write short, genuine Instagram direct messages welcoming new followers. "
            "Keep messages under 3 sentences. Never use generic filler like 'So excited to connect!' "
            "Do not use hashtags. Do not add emojis unless they feel natural. "
            "Output only the message text — no quotes, no labels, no explanation."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write a {tone} welcome DM for a new follower whose username is @{username}. "
                    "Make it feel personal and human, not like a bot."
                ),
            }
        ],
    )

    # Extract the text block from the response
    for block in response.content:
        if block.type == "text":
            return block.text.strip()

    raise ValueError("Claude returned no text block in the response")
