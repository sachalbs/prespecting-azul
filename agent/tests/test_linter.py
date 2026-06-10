"""Style linter: deterministic rules, regeneration loop, review_required flag."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from azul.domain import ProspectBrief
from azul.writing.base import Draft, DraftRequest, Writer
from azul.writing.linter import StyleRules, lint, lint_draft, load_rules

RULES = StyleRules(
    forbidden_patterns=("—", "je me permets", "synergie"),
    max_words=120,
    max_questions=1,
)

_REQ = DraftRequest(prospect=ProspectBrief(email="a@b.com", full_name="Ann"), hook="h")


class ScriptedWriter(Writer):
    """Returns bodies in order; records the requests it received."""

    name: ClassVar[str] = "scripted"

    def __init__(self, bodies: list[str]) -> None:
        self.bodies = list(bodies)
        self.requests: list[DraftRequest] = []

    def write(self, request: DraftRequest) -> Draft:
        self.requests.append(request)
        return Draft(body=self.bodies.pop(0), subject="s")


# ── lint() unit rules ────────────────────────────────────────────────────────


def test_lint_flags_em_dash_and_filler() -> None:
    violations = lint("Bonjour — je me permets de vous écrire.", RULES)
    assert any("—" in v for v in violations)
    assert any("je me permets" in v for v in violations)


def test_lint_flags_word_and_question_budgets() -> None:
    body = "mot " * 121 + "? deux ?"
    violations = lint(body, RULES)
    assert any("words" in v for v in violations)
    assert any("questions" in v for v in violations)


def test_lint_is_case_insensitive() -> None:
    assert lint("Une vraie SYNERGIE entre nous.", RULES)


def test_clean_body_passes() -> None:
    assert lint("Vu votre billet sur le pricing. On en parle 15 min mardi ?", RULES) == []


# ── regeneration loop ────────────────────────────────────────────────────────


def test_em_dash_draft_regenerated_without_it() -> None:
    writer = ScriptedWriter(
        ["Salut — j'ai vu votre billet.", "Salut, j'ai vu votre billet. On échange ?"]
    )
    draft = lint_draft(writer, _REQ, RULES)
    assert "—" not in draft.body
    assert not draft.review_required
    # The regeneration carried the offending pattern as a negative instruction.
    assert writer.requests[1].lint_feedback is not None
    assert "—" in writer.requests[1].lint_feedback


def test_three_bad_drafts_flag_review_required() -> None:
    writer = ScriptedWriter(["a — b", "c — d", "e — f"])
    draft = lint_draft(writer, _REQ, RULES)
    assert draft.review_required
    assert len(writer.requests) == 3  # initial + exactly 2 regenerations


def test_clean_first_draft_writes_once() -> None:
    writer = ScriptedWriter(["Vu votre billet. On échange ?"])
    draft = lint_draft(writer, _REQ, RULES)
    assert len(writer.requests) == 1
    assert not draft.review_required


# ── rules file ───────────────────────────────────────────────────────────────


def test_rules_load_from_yaml(tmp_path: Path) -> None:
    p = tmp_path / "rules.yaml"
    p.write_text(
        'forbidden_patterns:\n  - "blockchain"\nmax_words: 50\nmax_questions: 2\n',
        encoding="utf-8",
    )
    rules = load_rules(str(p))
    assert rules.forbidden_patterns == ("blockchain",)
    assert rules.max_words == 50
    assert lint("On adore la Blockchain ici.", rules)


def test_missing_rules_file_uses_defaults(tmp_path: Path) -> None:
    rules = load_rules(str(tmp_path / "nope.yaml"))
    assert "—" in rules.forbidden_patterns
    assert rules.max_words == 120


def test_repo_style_rules_yaml_is_loadable() -> None:
    rules = load_rules("style_rules.yaml")
    assert "j'espère que vous allez bien" in rules.forbidden_patterns
    assert rules.max_questions == 1


# ── end to end: flag persisted on the message ───────────────────────────────


def test_review_required_persisted_on_message(tmp_path: Path) -> None:
    import pytest
    from sqlalchemy import select

    from azul.db.models import Message
    from azul.db.session import session_scope
    from azul.orchestrator import campaign as camp
    from azul.orchestrator.graph import build_pipeline

    class SloppyWriter(Writer):
        name: ClassVar[str] = "sloppy"

        def write(self, request: DraftRequest) -> Draft:
            return Draft(body="Toujours — la même — slop.", subject="s")

    monkeypatch = pytest.MonkeyPatch()
    pipeline = build_pipeline(writer=SloppyWriter())
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)
    try:
        p = tmp_path / "p.csv"
        p.write_text("email,full_name,company\nann@acme.com,Ann Lee,Acme\n", encoding="utf-8")
        with session_scope() as s:
            camp.run_campaign(
                s, tenant_slug="t1", name="Q1", rows=camp.load_prospects_csv(str(p))
            )
        with session_scope() as s:
            m = s.scalars(select(Message)).one()
            assert m.review_required is True
    finally:
        monkeypatch.undo()
