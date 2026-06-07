"""Prompt construction for the Writer. Anti-template, anti-spray, anti-slop."""

from __future__ import annotations

import json
from typing import Any

from azul.writing.base import DraftRequest

SYSTEM_PROMPT = """\
You are an elite SDR who writes one outbound message at a time, by hand.
Low volume, high quality. The only metric that matters is the reply rate.

Hard rules:
- Lead with the specific hook about THIS person/company. No generic openers.
- Sound like a sharp human peer, not a marketer. No buzzwords, no fluff.
- No "I hope this finds you well", no "I came across", no flattery, no AI tells.
- Max ~80 words for the body. One clear, low-friction ask.
- Never invent facts. If the hook is weak, keep the claim modest.
- Plain text. No markdown, no emojis, no signature block.

Return STRICT JSON only, no prose, with keys:
  "subject": short, specific, lowercase-ish, not clickbait (email only; else "")
  "body": the message
  "angle": 2-4 word label for the angle you took (for the learning log)
"""


def build_messages(request: DraftRequest) -> list[dict[str, str]]:
    p = request.prospect
    context: dict[str, Any] = {
        "channel": request.channel,
        "recipient": {
            "name": p.full_name,
            "first_name": p.first_name,
            "title": p.title,
            "company": p.company,
            "segment": p.segment,
        },
        "hook": request.hook,
        "sender_name": request.sender_name,
        "value_prop": request.value_prop,
    }
    user = (
        "Write one outbound "
        + request.channel
        + " message using this context. Anchor it on the hook.\n\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
