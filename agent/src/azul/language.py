"""Outreach language: inferred per prospect (LLM), checked deterministically (linter).

Two concerns live here:
- `infer_target_language` decides which language to WRITE in, from the tenant's
  brief plus the prospect's own web presence (their site wins on doubt). It is an
  LLM call, computed once per prospect and persisted — never a blind default; on
  any uncertainty it returns None and the coherence check simply stands down.
- `detect_language` is a dependency-free detector used by the style linter to
  catch a draft written in the wrong language (a real defect seen on the dry run).
"""

from __future__ import annotations

import re

from azul.config import get_settings
from azul.errors import AzulError
from azul.llm import chat_json
from azul.logging import get_logger

log = get_logger(__name__)

SUPPORTED = ("fr", "en", "es", "de", "it", "pt", "nl")

# Distinctive function words per language — chosen to avoid cross-language
# collisions (e.g. no bare "la"/"de"/"un" that French and Spanish share).
_MARKERS: dict[str, set[str]] = {
    "fr": {
        "vous", "votre", "vos", "nous", "notre", "êtes", "avez", "pour", "avec",
        "qui", "chez", "merci", "bonjour", "cordialement", "ferait", "serait",
        "auriez", "ça", "été", "très", "aussi", "donc",
    },
    "en": {
        "you", "your", "the", "and", "with", "our", "we", "that", "this", "are",
        "have", "would", "thanks", "hello", "regards", "about", "just", "here",
    },
    "es": {
        "usted", "ustedes", "nuestra", "nuestro", "está", "para", "gracias",
        "hola", "saludos", "cómo", "tiene", "tienes", "porque", "también", "muy",
    },
    "de": {"sie", "ihre", "und", "mit", "wir", "haben", "wäre", "danke", "grüße", "sehr"},
    "it": {"lei", "vostra", "grazie", "saluti", "perché", "anche", "molto", "siete", "avete"},
    "pt": {"você", "vocês", "obrigado", "nossa", "está", "porque", "também", "muito", "saudações"},
    "nl": {"jij", "jouw", "bedankt", "groeten", "onze", "hebben", "ook", "zeer", "omdat"},
}

_WORD_RE = re.compile(r"[a-zà-ÿ]+", re.IGNORECASE)


def detect_language(text: str) -> str | None:
    """Best-guess language code, or None when the signal is too weak to be sure."""
    tokens = _WORD_RE.findall(text.lower())
    if not tokens:
        return None
    counts = {lang: sum(1 for t in tokens if t in markers) for lang, markers in _MARKERS.items()}
    best = max(counts, key=lambda k: counts[k])
    best_score = counts[best]
    runner_up = max((v for k, v in counts.items() if k != best), default=0)
    # Need a real signal and a clear margin — otherwise stay silent (no false flag).
    if best_score < 2 or best_score <= runner_up:
        return None
    return best


_SYSTEM = """\
You decide the SINGLE language a cold outreach email should be written in.
Inputs: the seller's targeting brief, and the prospect's own web presence.
Rule: write in the language the PROSPECT communicates in (their site/posts).
If the brief clearly targets one country/language, that wins. The language of
incidental SOURCES (directories) never decides.
Return STRICT JSON: {"language": "<ISO 639-1 two-letter code>"} e.g. "fr","en","es".
"""


def infer_target_language(*, brief_hint: str | None, site_text: str | None) -> str | None:
    """Infer the writing language once per prospect; None if it can't/shouldn't decide."""
    s = get_settings()
    if not (s.writer_base_url and s.writer_api_key and s.writer_model):
        return None  # no model wired — don't guess, let the playbook handle it
    if not (brief_hint or site_text):
        return None
    user = f"Targeting brief:\n{brief_hint or '-'}\n\nProspect web presence:\n{site_text or '-'}"
    try:
        data = chat_json(
            [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}]
        )
    except AzulError as exc:
        log.warning("language_infer_failed", error=str(exc))
        return None
    code = str(data.get("language") or "").strip().lower()[:2]
    if len(code) != 2 or not code.isalpha():
        return None
    log.info("language_inferred", language=code)
    return code
