"""Language inferred per prospect (LLM) and checked deterministically by the linter."""

from __future__ import annotations

import os
from typing import Any, ClassVar

import httpx
import pytest
import respx

from azul.config import get_settings
from azul.domain import ProspectBrief
from azul.language import detect_language, infer_target_language
from azul.writing.base import Draft, DraftRequest, Writer
from azul.writing.linter import StyleRules, language_mismatch, lint_draft
from tests.test_brief import writer_env

WRITER = "https://api.deepseek.com/v1"


# ── deterministic detector ───────────────────────────────────────────────────


def test_detects_french() -> None:
    body = (
        "Bonjour Karim, vu votre page tarifs : vous facturez à l'usage, mais sans "
        "limite affichée. C'est un sujet chez vous en ce moment ?"
    )
    assert detect_language(body) == "fr"


def test_detects_english() -> None:
    body = (
        "Hi Karim, saw your pricing page: you charge per seat and that surprised me. "
        "Is this something you are looking at right now? Thanks."
    )
    assert detect_language(body) == "en"


def test_detects_spanish() -> None:
    body = (
        "Hola Karim, vi su página de precios para usted. Gracias por compartir, "
        "¿está buscando algo así ahora mismo? Un saludo."
    )
    assert detect_language(body) == "es"


def test_unsure_returns_none() -> None:
    assert detect_language("Karim Hassani Acme 2026 SAS") is None
    assert detect_language("") is None


# ── LLM inference ────────────────────────────────────────────────────────────


def test_infer_uses_llm_and_returns_code() -> None:
    with writer_env(), respx.mock(base_url=WRITER) as router:
        router.post("/chat/completions").mock(
            return_value=httpx.Response(
                200, json={"choices": [{"message": {"content": '{"language":"es"}'}}]}
            )
        )
        code = infer_target_language(brief_hint="cible Barcelone", site_text="agencia de diseño")
    assert code == "es"


def test_infer_returns_none_without_model() -> None:
    old = os.environ.pop("WRITER_API_KEY", None)
    get_settings.cache_clear()
    try:
        assert infer_target_language(brief_hint="x", site_text="y") is None
    finally:
        if old is not None:
            os.environ["WRITER_API_KEY"] = old
        get_settings.cache_clear()


def test_infer_rejects_non_two_letter() -> None:
    with writer_env(), respx.mock(base_url=WRITER) as router:
        router.post("/chat/completions").mock(
            return_value=httpx.Response(
                200, json={"choices": [{"message": {"content": '{"language":"klingon"}'}}]}
            )
        )
        assert infer_target_language(brief_hint="x", site_text="y") == "kl"  # truncated 2-letter


# ── linter coherence ─────────────────────────────────────────────────────────

RULES = StyleRules(forbidden_patterns=(), max_words=120, max_questions=2)


def test_language_mismatch_helper() -> None:
    fr = "Bonjour, vu votre page tarifs, c'est un sujet chez vous ?"
    assert language_mismatch(fr, "fr") is None
    assert language_mismatch(fr, "en") is not None  # wrote fr, expected en
    assert language_mismatch(fr, None) is None  # nothing to enforce
    assert language_mismatch("Acme 2026", "fr") is None  # too little signal


class _ScriptedWriter(Writer):
    name: ClassVar[str] = "scripted"

    def __init__(self, bodies: list[str]) -> None:
        self.bodies = list(bodies)
        self.requests: list[DraftRequest] = []

    def write(self, request: DraftRequest) -> Draft:
        self.requests.append(request)
        return Draft(body=self.bodies.pop(0), subject="s")


_FR_OK = "Bonjour Karim, vu votre page tarifs, vous facturez à l'usage. Un sujet chez vous ?"
_EN_WRONG = "Hi Karim, saw your pricing page, you charge per usage. Is that on your radar?"


def _req(expected: str | None) -> DraftRequest:
    return DraftRequest(
        prospect=ProspectBrief(email="k@acme.fr", full_name="Karim Hassani"),
        hook="pricing",
        target_language=expected,
    )


def test_wrong_language_draft_is_regenerated() -> None:
    writer = _ScriptedWriter([_EN_WRONG, _FR_OK])  # first wrong, then corrected
    draft = lint_draft(writer, _req("fr"), RULES)
    assert detect_language(draft.body) == "fr"
    assert not draft.review_required
    assert len(writer.requests) == 2
    # The regeneration carried the language instruction.
    assert writer.requests[1].lint_feedback is not None
    assert "'fr'" in writer.requests[1].lint_feedback


def test_persistent_wrong_language_flags_review_required() -> None:
    writer = _ScriptedWriter([_EN_WRONG, _EN_WRONG, _EN_WRONG])
    draft = lint_draft(writer, _req("fr"), RULES)
    assert draft.review_required
    assert len(writer.requests) == 3  # initial + 2 regenerations


def test_no_expected_language_never_regenerates() -> None:
    writer = _ScriptedWriter([_EN_WRONG])
    draft = lint_draft(writer, _req(None), RULES)
    assert len(writer.requests) == 1
    assert not draft.review_required
    assert draft.body == _EN_WRONG  # coherence not enforced when expected is unknown


def test_pipeline_persists_inferred_language(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path

    from sqlalchemy import select

    import azul.language as language_mod
    from azul.db.models import Prospect
    from azul.db.session import session_scope
    from azul.orchestrator import campaign as camp

    def fake_infer(*, brief_hint: str | None, site_text: str | None) -> str | None:
        return "fr"

    monkeypatch.setattr(language_mod, "infer_target_language", fake_infer)

    assert isinstance(tmp_path, Path)
    p = tmp_path / "p.csv"
    p.write_text("email,full_name,company\nann@acme.fr,Ann Roy,Acme\n", encoding="utf-8")
    with session_scope() as s:
        camp.run_campaign(
            s, tenant_slug="t1", name="Q1", rows=camp.load_prospects_csv(str(p))
        )
    with session_scope() as s:
        prospect = s.scalars(select(Prospect)).one()
        assert prospect.target_language == "fr"
