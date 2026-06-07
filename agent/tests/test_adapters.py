"""Adapter-level unit tests (stub backends, no network)."""

from __future__ import annotations

from azul.domain import ProspectBrief
from azul.enums import EmailStatus
from azul.research import get_research_engine
from azul.sourcing import get_verifier
from azul.writing import DraftRequest, get_writer


def test_stub_verifier_distinguishes_valid_and_invalid() -> None:
    verifier = get_verifier()
    assert verifier.verify("a@b.com").status == EmailStatus.VERIFIED
    assert verifier.verify("not-an-email").status == EmailStatus.INVALID


def test_stub_research_returns_a_hook() -> None:
    result = get_research_engine().research(
        ProspectBrief(email="a@b.com", company="Acme", signals={"recent_signal": "raised seed"})
    )
    assert result.hooks
    assert result.top_hook


def test_stub_writer_personalises_on_name_and_hook() -> None:
    draft = get_writer().write(
        DraftRequest(
            prospect=ProspectBrief(email="a@b.com", full_name="Ann Lee", company="Acme"),
            hook="Acme just raised a seed round",
        )
    )
    assert "Ann" in draft.body
    assert "Acme just raised a seed round" in draft.body
    assert draft.subject
