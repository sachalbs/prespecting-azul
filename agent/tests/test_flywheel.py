"""The flywheel: outcomes -> curator (Wilson eval) -> skills -> Writer hint."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from azul.db.models import Message
from azul.db.session import session_scope
from azul.domain import ProspectBrief
from azul.memory import EpisodicMemory, ProceduralMemory
from azul.memory.flywheel import run_curator, wilson_lower_bound
from azul.orchestrator import campaign as camp
from azul.writing.base import DraftRequest
from azul.writing.prompts import build_messages

CSV = (
    "full_name,company,company_domain,segment\n"
    "Ann Lee,Acme,acme.com,saas\n"
    "Bob Ray,Beta,beta.io,saas\n"
    "Cy Dao,Cee,cee.co,saas\n"
)


def test_wilson_lower_bound_is_conservative() -> None:
    assert wilson_lower_bound(0, 0) == 0.0
    assert wilson_lower_bound(1, 3) < 1 / 3  # discounted for small n
    assert wilson_lower_bound(50, 100) < 0.5


def test_flywheel_learns_a_pattern_and_hints(tmp_path: Path) -> None:
    p = tmp_path / "p.csv"
    p.write_text(CSV, encoding="utf-8")
    rows = camp.load_prospects_csv(str(p))

    with session_scope() as s:
        cid = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows).id
    with session_scope() as s:
        camp.approve(s, campaign_id=cid, approve_all=True)
    with session_scope() as s:
        assert camp.send_approved(s, campaign_id=cid) == 3
    with session_scope() as s:  # one reply comes in
        msg = s.scalars(select(Message).where(Message.campaign_id == cid)).first()
        assert msg is not None
        EpisodicMemory(s).record_outcome(message_id=msg.id, replied=True)

    with session_scope() as s:
        assert run_curator(s) >= 1
    with session_scope() as s:
        hint = ProceduralMemory(s).hint_for("saas")
        assert hint is not None
        assert "saas" in hint


def test_writer_prompt_carries_the_learned_hint() -> None:
    msgs = build_messages(
        DraftRequest(
            prospect=ProspectBrief(email="a@b.com", segment="saas"),
            hook="h",
            procedural_hint="the 'hook-led' angle is landing",
        )
    )
    assert any("hook-led" in m["content"] for m in msgs)
