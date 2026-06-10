"""Explicit first/last name (verified order) so we never greet by the surname."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest
from sqlalchemy import select

from azul.db.models import Prospect
from azul.db.session import session_scope
from azul.domain import ProspectBrief
from azul.orchestrator import campaign as camp
from azul.orchestrator.graph import build_pipeline
from azul.sourcing.person_resolver import PersonResolver, ResolvedPerson


def test_brief_prefers_explicit_given_name_over_split() -> None:
    # "Hassani Karim" looks family-first; the explicit given name wins.
    brief = ProspectBrief(
        email="k@acme.fr", full_name="Hassani Karim", given_name="Karim", family_name="Hassani"
    )
    assert brief.first_name == "Karim"


def test_brief_falls_back_to_split_without_explicit() -> None:
    brief = ProspectBrief(email="a@b.fr", full_name="Anna Roy")
    assert brief.first_name == "Anna"


def test_resolver_splits_name_with_verified_order() -> None:
    import json
    import os
    from contextlib import contextmanager

    import httpx
    import respx

    from azul.config import get_settings
    from azul.sourcing.person_resolver import TavilyPersonResolver
    from tests.test_brief import writer_env as _writer_env

    @contextmanager
    def keys():  # type: ignore[no-untyped-def]
        os.environ["TAVILY_API_KEY"] = "tk"
        try:
            with _writer_env():
                yield
        finally:
            os.environ.pop("TAVILY_API_KEY", None)
            get_settings.cache_clear()

    payload = {
        "founder_name": "Karim Hassani",
        "first_name": "Karim",
        "last_name": "Hassani",
        "founder_role": "CEO",
        "confidence": 0.9,
    }
    with keys(), respx.mock() as router:
        router.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json={"results": [{"content": "Karim Hassani, CEO"}]})
        )
        router.post("https://api.tavily.com/extract").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        router.post("https://api.deepseek.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200, json={"choices": [{"message": {"content": json.dumps(payload)}}]}
            )
        )
        person = TavilyPersonResolver().resolve("Acme", "acme.fr")
    assert person.first_name == "Karim"
    assert person.last_name == "Hassani"


class _FakeResolver(PersonResolver):
    name: ClassVar[str] = "fake"

    def __init__(self, person: ResolvedPerson) -> None:
        self._person = person

    def resolve(self, company: str | None, domain: str | None) -> ResolvedPerson:
        return self._person


def test_resolved_name_parts_persisted_and_greeting_uses_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolver = _FakeResolver(
        ResolvedPerson("Karim Hassani", "CEO", 0.9, first_name="Karim", last_name="Hassani")
    )
    pipeline = build_pipeline(person_resolver=resolver)
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)

    rows = [camp.CsvRow(email="", company="Acme", company_domain="acme.fr")]
    with session_scope() as s:
        camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows)

    with session_scope() as s:
        prospect = s.scalars(select(Prospect)).one()
        assert prospect.first_name == "Karim"
        assert prospect.last_name == "Hassani"
        # The brief the writer sees greets by the given name, not the surname.
        brief = camp._brief_from_prospect(prospect)  # pyright: ignore[reportPrivateUsage]
        assert brief.first_name == "Karim"
