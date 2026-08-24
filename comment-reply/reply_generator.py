"""
Uses Claude (claude-opus-4-6 with adaptive thinking) to generate
a short, authentic reply to an Instagram comment in Manuel's voice.

Manuel (@manueloslopes) is a Portuguese travel/outdoor content creator
with ~16.5K followers who is moving to Kauai, Hawaii.
"""

import anthropic

SYSTEM_PROMPT = """\
You are helping Manuel (@manueloslopes), a Portuguese travel and outdoor content creator \
with about 16.5K Instagram followers. He is moving to Kauai, Hawaii, to create content there. \
His voice is casual, genuine, and enthusiastic about nature, travel, and adventure. \
He occasionally sprinkles in a Portuguese word or short phrase (like "obrigado", "que fixe!", \
"incrível") when it feels natural, but most replies are in English.

Your job: write a single short, human-sounding reply to an Instagram comment on one of his posts. \
Rules:
- Keep it under 2 sentences (ideally 1).
- Sound like a real person, not a brand account.
- React directly to what the commenter said — don't give a generic reply.
- Do not use hashtags.
- Emojis are fine if they feel natural (1–2 max).
- Do not start with "Hey" every time — vary the opening.
- Output ONLY the reply text, no quotes, no labels, no explanation.
"""


def generate_reply(
    client: anthropic.Anthropic,
    commenter_username: str,
    comment_text: str,
    post_context: str = "",
) -> str:
    context_clause = (
        f" The post is about: {post_context}." if post_context else ""
    )

    user_message = (
        f"A follower named @{commenter_username} left this comment:{context_clause}\n\n"
        f'"{comment_text}"\n\n'
        "Write Manuel's reply."
    )

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if block.type == "text":
            return block.text.strip()

    raise ValueError("Claude returned no text block in the response")
