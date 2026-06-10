"""The chat surface drives the real engine end-to-end (stub adapters)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from azul.cli.chat import ChatSession
from azul.db.models import Message
from azul.db.session import session_scope
from azul.enums import MessageStatus

CSV = "full_name,company,company_domain,segment\nAnn Lee,Acme,acme.com,saas\n"


def test_chat_runs_a_campaign_to_a_reply_rate(tmp_path: Path) -> None:
    csv = tmp_path / "p.csv"
    csv.write_text(CSV, encoding="utf-8")
    cs = ChatSession()

    assert "drafts ready" in cs.handle(f"campaign Q1 from {csv}")
    assert "[1]" in cs.handle("show")
    assert "Approved 1" in cs.handle("approve all")
    assert "Sent 1" in cs.handle("send")
    assert "REPLY RATE" in cs.handle("report")


def test_chat_help_and_unknown(tmp_path: Path) -> None:
    cs = ChatSession()
    assert "campaign" in cs.handle("help").lower()
    assert "help" in cs.handle("flibbertigibbet").lower()
    assert "campaign" in cs.handle("show").lower()  # no campaign yet -> guidance


def test_chat_edit_logs_signal(tmp_path: Path) -> None:
    csv = tmp_path / "p.csv"
    csv.write_text(CSV, encoding="utf-8")
    cs = ChatSession()
    cs.handle(f"campaign Q1 from {csv}")
    cs.handle("show")
    assert "Edited draft [1]" in cs.handle("edit 1 Loved your take on usage-based pricing.")


def test_nl_interpreted_send_requires_explicit_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import azul.cli.chat as chat_mod

    csv = tmp_path / "p.csv"
    csv.write_text(CSV, encoding="utf-8")
    cs = ChatSession()
    cs.handle(f"campaign Q1 from {csv}")
    cs.handle("approve all")

    def interpret_real_send(line: str) -> str:
        return "send"

    # The NL parser maps free text to a REAL send -> must NOT execute, only ask.
    monkeypatch.setattr(chat_mod, "interpret", interpret_real_send)
    out = cs.handle("envoie tout maintenant")
    assert "send" in out and "confirm" in out.lower()

    with session_scope() as s:
        msgs = s.scalars(select(Message)).all()
        assert all(m.status != MessageStatus.SENT for m in msgs)  # nothing went out

    def interpret_dry_send(line: str) -> str:
        return "send dry"

    # A dry send interpreted from NL is harmless and passes through.
    monkeypatch.setattr(chat_mod, "interpret", interpret_dry_send)
    assert "Would send" in cs.handle("montre-moi ce que tu enverrais")

    # The explicit command, typed by the human, still sends.
    assert "Sent 1" in cs.handle("send")
