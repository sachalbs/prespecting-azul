"""Founder resolution runs before the finder: a name unlocks email permutations;
no name skips with `no_founder_found` while the other prospects keep going (A2)."""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, ClassVar

import httpx
import pytest
import respx
from sqlalchemy import select

from azul.config import get_settings
from azul.db.models import CampaignProspect, Message, Prospect
from azul.db.session import session_scope
from azul.enums import MembershipStatus
from azul.orchestrator import campaign as camp
from azul.orchestrator.graph import build_pipeline
from azul.sourcing.person_resolver import (
    PersonResolver,
    ResolvedPerson,
    TavilyPersonResolver,
)
from tests.test_brief import writer_env as _writer_only_env

TAVILY = "https://api.tavily.com"
WRITER = "https://api.deepseek.com/v1"


@contextmanager
def keys_env() -> Generator[None, None, None]:
    old = os.environ.get("TAVILY_API_KEY")
    os.environ["TAVILY_API_KEY"] = "tk"
    try:
        with _writer_only_env():
            yield
    finally:
        if old is None:
            os.environ.pop("TAVILY_API_KEY", None)
        else:
            os.environ["TAVILY_API_KEY"] = old
        get_settings.cache_clear()


def _llm(payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200, json={"choices": [{"message": {"content": json.dumps(payload)}}]}
    )


# ── the resolver itself (Tavily + LLM mocked) ───────────────────────────────


def test_resolver_returns_name_role_confidence() -> None:
    search = {"results": [{"content": "Acme a été fondée par Jean Dupont, CEO."}]}
    extract = {"results": [{"raw_content": "Notre équipe: Jean Dupont, dirigeant."}]}
    with keys_env(), respx.mock() as router:
        router.post(f"{TAVILY}/search").mock(return_value=httpx.Response(200, json=search))
        router.post(f"{TAVILY}/extract").mock(return_value=httpx.Response(200, json=extract))
        router.post(f"{WRITER}/chat/completions").mock(
            return_value=_llm(
                {"founder_name": "Jean Dupont", "founder_role": "CEO", "confidence": 0.9}
            )
        )
        person = TavilyPersonResolver().resolve("Acme", "acme.fr")
    assert person.founder_name == "Jean Dupont"
    assert person.founder_role == "CEO"
    assert person.confidence == 0.9


def test_resolver_caps_tavily_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSON_RESOLVE_MAX_SEARCHES", "1")
    get_settings.cache_clear()
    with keys_env(), respx.mock(assert_all_called=False) as router:
        search = router.post(f"{TAVILY}/search").mock(
            return_value=httpx.Response(200, json={"results": [{"content": "x"}]})
        )
        extract = router.post(f"{TAVILY}/extract").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        router.post(f"{WRITER}/chat/completions").mock(
            return_value=_llm({"founder_name": "", "founder_role": "", "confidence": 0.0})
        )
        TavilyPersonResolver().resolve("Acme", "acme.fr")
    assert search.call_count + extract.call_count == 1  # one call, cap respected


def test_resolver_low_confidence_reported_as_is() -> None:
    with keys_env(), respx.mock() as router:
        router.post(f"{TAVILY}/search").mock(
            return_value=httpx.Response(200, json={"results": [{"content": "vague"}]})
        )
        router.post(f"{TAVILY}/extract").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        router.post(f"{WRITER}/chat/completions").mock(
            return_value=_llm({"founder_name": "Peut-être X", "confidence": 0.2})
        )
        person = TavilyPersonResolver().resolve("Flou", "flou.io")
    assert person.confidence == 0.2  # the pipeline decides the 0.5 cutoff, not here


# ── pipeline: resolver -> finder ─────────────────────────────────────────────
# Discovery feeds the pipeline company-only rows (full_name=None), exactly like
# approve_list builds them from campaign.leads — no email, no founder yet.


def _company_rows() -> list[camp.CsvRow]:
    return [camp.CsvRow(email="", company="Pixel Agence", company_domain="pixel.fr")]


class FakeResolver(PersonResolver):
    name: ClassVar[str] = "fake"

    def __init__(self, person: ResolvedPerson) -> None:
        self._person = person
        self.calls = 0

    def resolve(self, company: str | None, domain: str | None) -> ResolvedPerson:
        self.calls += 1
        return self._person


def test_resolved_founder_unlocks_finder_permutations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    from azul.enums import EmailStatus
    from azul.sourcing.base import EmailVerification, EmailVerifier

    class CapturingVerifier(EmailVerifier):
        name: ClassVar[str] = "capture"

        def verify(
            self, email: str, *, full_name: str | None = None, company_domain: str | None = None
        ) -> EmailVerification:
            from azul.sourcing.finder import candidates

            seen["full_name"] = full_name
            seen["permutations"] = candidates(full_name or "", company_domain or "")
            return EmailVerification(
                email="jean.dupont@pixel.fr", status=EmailStatus.VERIFIED, provider=self.name
            )

    resolver = FakeResolver(ResolvedPerson("Jean Dupont", "CEO", 0.9))
    pipeline = build_pipeline(verifier=CapturingVerifier(), person_resolver=resolver)
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)

    with session_scope() as s:
        cid = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=_company_rows()).id

    assert resolver.calls == 1
    assert seen["full_name"] == "Jean Dupont"
    assert "jean.dupont@pixel.fr" in seen["permutations"]
    with session_scope() as s:
        prospect = s.scalars(select(Prospect)).one()
        assert prospect.full_name == "Jean Dupont"  # persisted on the prospect
        assert prospect.title == "CEO"
        assert len(camp.list_drafts(s, cid)) == 1


def test_no_founder_skips_with_distinct_reason_and_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Two companies need resolution; the resolver finds one, misses the other.
    rows = [
        camp.CsvRow(email="", company="Pixel Agence", company_domain="pixel.fr"),
        camp.CsvRow(email="", company="Boite Fantome", company_domain="fantome.fr"),
    ]

    class SelectiveResolver(PersonResolver):
        name: ClassVar[str] = "selective"

        def resolve(self, company: str | None, domain: str | None) -> ResolvedPerson:
            if domain == "pixel.fr":
                return ResolvedPerson("Jean Dupont", "CEO", 0.9)
            return ResolvedPerson(None, None, 0.0)  # nothing found -> no_founder

    pipeline = build_pipeline(person_resolver=SelectiveResolver())
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)

    with session_scope() as s:
        cid = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows).id

    with session_scope() as s:
        # The resolvable one produced a draft; the other was skipped, not fatal.
        drafts = camp.list_drafts(s, cid)
        assert len(drafts) == 1
        assert drafts[0].prospect.company == "Pixel Agence"

        skipped = s.scalars(
            select(CampaignProspect).where(
                CampaignProspect.campaign_id == cid,
                CampaignProspect.status == MembershipStatus.SKIPPED,
            )
        ).all()
        assert len(skipped) == 1  # fantome.fr skipped with no_founder_found
        fantome = s.scalars(
            select(Prospect).where(Prospect.company_domain == "fantome.fr")
        ).one()
        assert fantome.full_name is None  # never invented a name

    # Isolation A2: a skip is not a crash — the campaign still has its draft.
    with session_scope() as s:
        assert s.scalars(select(Message)).first() is not None


def test_existing_founder_skips_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolver = FakeResolver(ResolvedPerson("Should Not Run", None, 1.0))
    pipeline = build_pipeline(person_resolver=resolver)
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)

    p = tmp_path / "p.csv"
    p.write_text(
        "email,full_name,company,company_domain\nann@known.fr,Ann Lee,Known,known.fr\n",
        encoding="utf-8",
    )
    with session_scope() as s:
        camp.run_campaign(
            s, tenant_slug="t1", name="Q1", rows=camp.load_prospects_csv(str(p))
        )
    assert resolver.calls == 0  # a name was already present, resolver untouched


def test_email_without_name_does_not_trigger_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A row that already carries an email needs no founder lookup.
    resolver = FakeResolver(ResolvedPerson("Should Not Run", None, 1.0))
    pipeline = build_pipeline(person_resolver=resolver)
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)

    rows = [camp.CsvRow(email="info@known.fr", company="Known", company_domain="known.fr")]
    with session_scope() as s:
        camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows)
    assert resolver.calls == 0  # email present -> resolver untouched
