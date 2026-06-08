"""The chat surface drives the real engine end-to-end (stub adapters)."""

from __future__ import annotations

from pathlib import Path

from azul.cli.chat import ChatSession

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
