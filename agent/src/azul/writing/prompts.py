"""Prompt construction for the Writer.

The system prompt = the cold-outreach playbook (WRITER_PLAYBOOK_PATH) — the
writer's brain — with a strict JSON output contract always appended so parsing
stays stable regardless of the playbook's prose. If the file is absent, a built-in
anti-slop fallback is used so the pipeline still runs.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from azul.config import get_settings
from azul.writing.base import DraftRequest

# Fallback playbook (used only if WRITER_PLAYBOOK_PATH is missing).
FALLBACK_PLAYBOOK = """\
You are an elite SDR who writes one outbound message at a time, by hand.
Low volume, high quality. The only metric that matters is the reply rate.

Hard rules:
- Lead with the specific hook about THIS person/company. No generic openers.
- Body in 4 beats: hook (about THEM, never "I/we") -> bridge (what the observation
  implies or costs for them, still their world) -> offer in one sentence -> CTA.
- Sound like a sharp human peer, not a marketer. No buzzwords, no fluff.
- No "I hope this finds you well", no "I came across", no flattery, no AI tells.
- Max ~80 words for the body. One clear, low-friction ask.
- The CTA asks for interest only ("worth a longer note?"), never a meeting,
  a time slot, or a calendar link on first contact.
- Never invent facts. If the hook is weak, keep the claim modest.
- Plain text. No markdown, no emojis, no signature block.
"""

# Always appended — defines the machine-readable output we parse.
OUTPUT_CONTRACT = """\
Return STRICT JSON only, no prose, with exactly these keys:
  "subject": short, specific, not clickbait (email only; else "")
  "body": the message
  "angle": a 2-4 word label for the angle you took (for the learning log)
  "hook_type": which kind of hook the message leads with — exactly one of
    "incoherence_site" | "actu_entreprise" | "contenu_publie" | "offre_emploi"
    | "avis_clients" | "autre"
"""


@lru_cache(maxsize=4)
def _load_playbook(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else FALLBACK_PLAYBOOK


def system_prompt() -> str:
    return _load_playbook(get_settings().writer_playbook_path) + "\n\n" + OUTPUT_CONTRACT


def build_messages(request: DraftRequest) -> list[dict[str, str]]:
    p = request.prospect
    context: dict[str, Any] = {
        "channel": request.channel,
        "recipient": {
            "name": p.full_name,
            # Verified split when known — greet by the GIVEN name, never the family one.
            "first_name": p.first_name,
            "last_name": p.family_name,
            "title": p.title,
            "company": p.company,
            "segment": p.segment,
        },
        "hook": request.hook,
        "dossier": dict(p.signals),
        "whats_worked": request.procedural_hint,
        "relationship": request.relationship_note,
        "sender_name": request.sender_name,
        "value_prop": request.value_prop,
        # Inferred from the brief + the prospect's site (playbook §0 decides the final call).
        "target_language": request.target_language,
    }
    if request.step > 1:
        context["prior_message"] = request.prior_body
        instruction = (
            f"Write follow-up #{request.step} (they didn't reply). Keep it shorter than the "
            "first, reference the prior note lightly, add ONE new angle, no guilt-trip."
        )
    elif request.weak_hook:
        # No strong, specific signal was found — do NOT pretend to have spotted one.
        instruction = (
            f"Write one outbound {request.channel} message. No strong specific signal was "
            "found on this prospect, so do NOT invent or claim one. Open soberly on their "
            "métier/positioning (what they do, who they serve) and bridge to the offer "
            "honestly. Never build the message around a minor technical detail (SEO, alt "
            "tag, typo)."
        )
    else:
        instruction = (
            f"Write one outbound {request.channel} message. Anchor it on the hook — the "
            "strongest, freshest, most specific signal. Never make a minor technical detail "
            "(SEO, alt tag, typo) the main hook or the bridge to the offer."
        )
    if request.lint_feedback:
        instruction += " " + request.lint_feedback
    user = instruction + "\n\n" + json.dumps(context, ensure_ascii=False, indent=2, default=str)
    return [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": user},
    ]
