"""A failing adapter on one prospect must not roll back the rest of the campaign."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest
from sqlalchemy import select

from azul.db.models import CampaignProspect
from azul.db.session import session_scope
from azul.enums import MembershipStatus
from azul.errors import WritingError
from azul.orchestrator import campaign as camp
from azul.orchestrator.graph import build_pipeline
from azul.writing.base import Draft, DraftRequest, Writer
from azul.writing.stub import StubWriter

CSV = "email,full_name,company,segment\n" + "\n".join(
    f"p{i}@acme.com,Person {i},Acme,saas" for i in range(1, 6)
)


class FlakyWriter(Writer):
    """Raises on one specific prospect; behaves like the stub otherwise."""

    name: ClassVar[str] = "flaky"

    def __init__(self, fail_email: str) -> None:
        self._fail_email = fail_email
        self._inner = StubWriter()

    def write(self, request: DraftRequest) -> Draft:
        if request.prospect.email == self._fail_email:
            raise WritingError("model returned garbage")
        return self._inner.write(request)


def test_one_failing_prospect_keeps_the_other_drafts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "p.csv"
    p.write_text(CSV, encoding="utf-8")
    rows = camp.load_prospects_csv(str(p))

    pipeline = build_pipeline(writer=FlakyWriter("p2@acme.com"))
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)

    with session_scope() as s:
        cid = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows).id

    with session_scope() as s:
        drafts = camp.list_drafts(s, cid)
        assert len(drafts) == 4
        assert "p2@acme.com" not in {m.prospect.email for m in drafts}
        failed = s.scalars(
            select(CampaignProspect).where(
                CampaignProspect.campaign_id == cid,
                CampaignProspect.status == MembershipStatus.FAILED,
            )
        ).all()
        assert len(failed) == 1
