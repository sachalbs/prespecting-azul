"""Learning schema: hook_type from the writer + style metrics + edit capture."""

from __future__ import annotations

import difflib
from pathlib import Path

from sqlalchemy import select

from azul.cli.chat import ChatSession
from azul.db.models import Message
from azul.db.session import session_scope
from azul.enums import HookType, ReviewDecision
from azul.orchestrator import campaign as camp

CSV = "email,full_name,company,segment\nann@acme.com,Ann Lee,Acme,saas\n"


def _run(tmp_path: Path) -> None:
    p = tmp_path / "p.csv"
    p.write_text(CSV, encoding="utf-8")
    with session_scope() as s:
        camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=camp.load_prospects_csv(str(p)))


def test_message_carries_hook_type_and_metrics(tmp_path: Path) -> None:
    _run(tmp_path)
    with session_scope() as s:
        m = s.scalars(select(Message)).one()
        assert m.hook_type == HookType.AUTRE  # stub writer's bucket
        assert m.subject_len == len(m.subject or "")
        assert m.word_count == len(m.body.split())
        assert m.word_count is not None and m.word_count > 0


def test_writer_hook_type_parsed_and_junk_lands_in_autre() -> None:
    from azul.writing.openai_compat import OpenAICompatWriter

    draft = OpenAICompatWriter._parse(  # pyright: ignore[reportPrivateUsage]
        '{"subject":"s","body":"b","angle":"a","hook_type":"offre_emploi"}'
    )
    assert draft.hook_type == HookType.OFFRE_EMPLOI

    junk = OpenAICompatWriter._parse(  # pyright: ignore[reportPrivateUsage]
        '{"subject":"s","body":"b","angle":"a","hook_type":"vibes"}'
    )
    assert junk.hook_type == HookType.AUTRE


def test_output_contract_documents_the_taxonomy() -> None:
    from azul.writing.prompts import OUTPUT_CONTRACT

    for value in HookType:
        assert value.value in OUTPUT_CONTRACT


def test_human_edit_keeps_draft_and_final_for_a_unified_diff(tmp_path: Path) -> None:
    csv = tmp_path / "p.csv"
    csv.write_text(CSV, encoding="utf-8")
    cs = ChatSession()
    cs.handle(f"campaign Q1 from {csv}")
    cs.handle("show")
    cs.handle("edit 1 Loved your take on usage-based pricing.")

    with session_scope() as s:
        m = s.scalars(select(Message)).one()
        assert m.review_decision == ReviewDecision.EDIT
        assert m.human_edited_body == "Loved your take on usage-based pricing."
        assert m.body != m.human_edited_body  # the original draft is preserved
        diff = "\n".join(
            difflib.unified_diff(
                m.body.splitlines(), m.human_edited_body.splitlines(), lineterm=""
            )
        )
        assert "+Loved your take on usage-based pricing." in diff
