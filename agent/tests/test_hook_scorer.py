"""Hook strength scoring: minor technical = low, real events = high, never force."""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
import respx

from azul.config import get_settings
from azul.research.base import Hook
from azul.research.hook_scorer import (
    is_minor_technical,
    score_hooks,
    select_hook,
    strongest,
)
from tests.test_brief import writer_env

WRITER = "https://api.deepseek.com/v1"


def _llm(scores: list[dict[str, Any]]) -> httpx.Response:
    content = json.dumps({"scores": scores}, ensure_ascii=False)
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


@contextmanager
def _no_writer() -> Generator[None, None, None]:
    old = os.environ.get("WRITER_API_KEY")
    os.environ.pop("WRITER_API_KEY", None)
    get_settings.cache_clear()
    try:
        yield
    finally:
        if old is not None:
            os.environ["WRITER_API_KEY"] = old
        get_settings.cache_clear()


# ── deterministic minor-technical guard (item 3) ────────────────────────────


def test_minor_technical_patterns_detected() -> None:
    assert is_minor_technical("votre site a une balise alt non optimisée")
    assert is_minor_technical("a typo on your homepage")
    assert is_minor_technical("votre SEO pourrait être amélioré")
    assert is_minor_technical("meta description manquante")
    assert not is_minor_technical("vous recrutez un SDR")
    assert not is_minor_technical("vous avez levé une série A")


def test_minor_technical_is_capped_even_if_llm_scores_high() -> None:
    hook = Hook(text="votre balise alt n'est pas optimisée", confidence=0.9)
    with writer_env(), respx.mock(base_url=WRITER) as router:
        router.post("/chat/completions").mock(
            return_value=_llm(
                [{"index": 0, "freshness": 0.9, "specificity": 0.9,
                  "relevance": 0.9, "reason": "looks specific"}]
            )
        )
        score_hooks([hook], offer="audit RGPD", prospect_label="Acme")
    assert hook.strength is not None and hook.strength <= 0.3
    assert "minor technical" in (hook.strength_reason or "")


# ── LLM scoring orders weak vs strong correctly ─────────────────────────────


def test_recruitment_outscores_alt_tag() -> None:
    alt = Hook(text="balise alt non optimisée sur la home", confidence=0.8)
    hiring = Hook(text="Acme recrute un SDR à Paris", confidence=0.6)
    with writer_env(), respx.mock(base_url=WRITER) as router:
        router.post("/chat/completions").mock(
            return_value=_llm(
                [
                    {"index": 0, "freshness": 0.2, "specificity": 0.2,
                     "relevance": 0.2, "reason": "trivial SEO nit"},
                    {"index": 1, "freshness": 0.9, "specificity": 0.8,
                     "relevance": 0.9, "reason": "dated hiring event, on-offer"},
                ]
            )
        )
        score_hooks([alt, hiring], offer="prospection externalisée", prospect_label="Acme")
    assert hiring.strength is not None and alt.strength is not None
    assert hiring.strength > alt.strength
    assert strongest([alt, hiring]) is hiring
    text, weak, chosen = select_hook([alt, hiring], 0.5)
    assert not weak and chosen is hiring
    assert text is not None and "SDR" in text


# ── threshold: weak batch => don't force ────────────────────────────────────


def test_all_weak_hooks_yield_weak_flag_and_no_selection() -> None:
    alt = Hook(text="balise alt manquante", confidence=0.4)
    slogan = Hook(text="leur slogan parle d'excellence", confidence=0.3)
    with writer_env(), respx.mock(base_url=WRITER) as router:
        router.post("/chat/completions").mock(
            return_value=_llm(
                [
                    {"index": 0, "freshness": 0.1, "specificity": 0.1,
                     "relevance": 0.1, "reason": "nit"},
                    {"index": 1, "freshness": 0.3, "specificity": 0.1,
                     "relevance": 0.2, "reason": "generic"},
                ]
            )
        )
        score_hooks([alt, slogan], offer="x", prospect_label="Acme")
    text, weak, chosen = select_hook([alt, slogan], 0.5)
    assert weak and text is None and chosen is None


def test_no_writer_falls_back_to_confidence_proxy_and_caps() -> None:
    strong = Hook(text="Acme vient de lever 5M", confidence=0.8)
    alt = Hook(text="balise alt non optimisée", confidence=0.9)
    with _no_writer():
        score_hooks([strong, alt])  # no LLM: strength = confidence, then cap
    assert strong.strength == 0.8
    assert alt.strength is not None and alt.strength <= 0.3  # capped despite high confidence
    assert strongest([strong, alt]) is strong


def test_score_hooks_returns_same_list_drops_nothing() -> None:
    hooks = [Hook(text="a", confidence=0.5), Hook(text="b", confidence=0.2)]
    with _no_writer():
        out = score_hooks(hooks)
    assert out is hooks and len(out) == 2


def test_llm_failure_keeps_hooks_via_confidence_proxy() -> None:
    h = Hook(text="Acme recrute", confidence=0.6)
    with writer_env(), respx.mock(base_url=WRITER) as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(500))
        score_hooks([h], offer="x", prospect_label="Acme")
    assert h.strength == 0.6  # fell back to confidence, not dropped


# ── pipeline end-to-end: weak hook => weak_hook persisted, no forced signal ──


def test_pipeline_marks_weak_hook_when_only_trivial_signal(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path
    from typing import ClassVar

    from sqlalchemy import select

    from azul.db.models import Message
    from azul.db.session import session_scope
    from azul.domain import ProspectBrief
    from azul.orchestrator import campaign as camp
    from azul.orchestrator.graph import build_pipeline
    from azul.research.base import ResearchEngine, ResearchResult
    from azul.writing.base import Draft, DraftRequest, Writer

    class AltTagOnly(ResearchEngine):
        name: ClassVar[str] = "alt"

        def research(self, prospect: ProspectBrief) -> ResearchResult:
            return ResearchResult(
                engine=self.name,
                hooks=[Hook(text="balise alt non optimisée", confidence=0.9)],
            )

    class CapturingWriter(Writer):
        name: ClassVar[str] = "cap"
        seen: ClassVar[list[DraftRequest]] = []

        def write(self, request: DraftRequest) -> Draft:
            CapturingWriter.seen.append(request)
            return Draft(body="sober body", subject="s", angle="sober")

    pipeline = build_pipeline(research_engine=AltTagOnly(), writer=CapturingWriter())
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)

    assert isinstance(tmp_path, Path)
    p = tmp_path / "p.csv"
    p.write_text("email,full_name,company\nann@acme.fr,Ann Roy,Acme\n", encoding="utf-8")
    with session_scope() as s:
        camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=camp.load_prospects_csv(str(p)))

    # The alt-tag hook is capped (<0.5) -> weak_hook, writer told no precise signal.
    req = CapturingWriter.seen[-1]
    assert req.weak_hook is True
    assert req.hook is None
    with session_scope() as s:
        m = s.scalars(select(Message)).one()
        assert m.weak_hook is True
