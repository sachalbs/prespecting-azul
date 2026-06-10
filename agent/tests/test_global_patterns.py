"""global_patterns: de-identified by construction, migrated empty, never fed in v0."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Text, func, select

from azul.db.models import GlobalPattern
from azul.db.session import session_scope
from azul.enums import HookType
from azul.orchestrator import campaign as camp


def test_no_foreign_keys_and_no_free_text_columns() -> None:
    table = GlobalPattern.__table__
    fks = [fk for col in table.columns for fk in col.foreign_keys]
    assert fks == []  # nothing can join back to a tenant or a prospect
    assert not any(isinstance(col.type, Text) for col in table.columns)


def test_unique_on_segment_hook_dow_bucket() -> None:
    import pytest
    from sqlalchemy.exc import IntegrityError

    row = dict(
        segment="saas", hook_type=HookType.OFFRE_EMPLOI, send_dow=1, send_hour_bucket=2
    )
    with session_scope() as s:
        s.add(GlobalPattern(**row, n_sent=1))
    with pytest.raises(IntegrityError), session_scope() as s:
        s.add(GlobalPattern(**row, n_sent=2))
        s.flush()
    # cleanup: the failed scope rolled back; remove the seed row
    with session_scope() as s:
        for gp in s.scalars(select(GlobalPattern)):
            s.delete(gp)


def test_nothing_feeds_the_table_in_v0(tmp_path: Path) -> None:
    """Full campaign + simulated outcomes + curator run -> table stays empty."""
    from azul.memory.flywheel import run_curator

    p = tmp_path / "p.csv"
    p.write_text("email,full_name,company,segment\nann@acme.com,Ann Lee,Acme,saas\n", "utf-8")
    with session_scope() as s:
        cid = camp.run_campaign(
            s, tenant_slug="t1", name="Q1", rows=camp.load_prospects_csv(str(p))
        ).id
    with session_scope() as s:
        camp.approve(s, campaign_id=cid, approve_all=True)
    with session_scope() as s:
        camp.send_approved(s, campaign_id=cid)
    with session_scope() as s:
        camp.simulate_replies(s, campaign_id=cid)
        run_curator(s)
    with session_scope() as s:
        count = s.scalar(select(func.count()).select_from(GlobalPattern))
        assert count == 0
