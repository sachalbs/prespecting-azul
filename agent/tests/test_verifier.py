"""In-house verifier: syntax + MX always; SMTP RCPT + catch-all probe when enabled."""

from __future__ import annotations

import pytest

import azul.sourcing.verifier as verifier_mod
from azul.enums import EmailStatus, VerifyStatus
from azul.sourcing.verifier import SmtpVerifier


def _mock_dns(monkeypatch: pytest.MonkeyPatch, table: dict[str, list[str] | None]) -> None:
    def fake_resolve_mx(domain: str) -> list[str] | None:
        return table.get(domain)

    monkeypatch.setattr(verifier_mod, "resolve_mx", fake_resolve_mx)


def _mock_smtp(monkeypatch: pytest.MonkeyPatch, codes: dict[str, int | None]) -> list[str]:
    """RCPT codes per address; '*' is the catch-all probe fallback. Returns the call log."""
    calls: list[str] = []

    def fake_rcpt(host: str, email: str, timeout: float) -> int | None:
        calls.append(email)
        if email in codes:
            return codes[email]
        return codes.get("*", 550)

    monkeypatch.setattr(verifier_mod, "smtp_rcpt_code", fake_rcpt)
    return calls


def test_bad_syntax_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    result = SmtpVerifier(smtp_enabled=False).verify("not-an-email")
    assert result.verdict == VerifyStatus.INVALID
    assert result.status == EmailStatus.INVALID
    assert result.score == 1.0


def test_no_mx_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_dns(monkeypatch, {"ghost.io": None})
    result = SmtpVerifier(smtp_enabled=False).verify("bob@ghost.io")
    assert result.verdict == VerifyStatus.INVALID


def test_dns_error_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_dns(monkeypatch, {"slow.io": []})
    result = SmtpVerifier(smtp_enabled=False).verify("bob@slow.io")
    assert result.verdict == VerifyStatus.UNKNOWN


def test_smtp_disabled_caps_at_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_dns(monkeypatch, {"acme.com": ["mx1.acme.com"]})
    result = SmtpVerifier(smtp_enabled=False).verify("ann@acme.com")
    assert result.verdict == VerifyStatus.UNKNOWN
    assert result.status == EmailStatus.UNKNOWN
    assert result.raw["reason"] == "smtp_disabled"


def test_rcpt_accepted_not_catch_all_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_dns(monkeypatch, {"acme.com": ["mx1.acme.com"]})
    calls = _mock_smtp(monkeypatch, {"ann@acme.com": 250, "*": 550})
    result = SmtpVerifier(smtp_enabled=True).verify("ann@acme.com")
    assert result.verdict == VerifyStatus.VALID
    assert result.status == EmailStatus.VERIFIED
    assert result.score == 0.9
    assert len(calls) == 2  # the address + the random catch-all probe


def test_rcpt_rejected_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_dns(monkeypatch, {"acme.com": ["mx1.acme.com"]})
    _mock_smtp(monkeypatch, {"gone@acme.com": 550})
    result = SmtpVerifier(smtp_enabled=True).verify("gone@acme.com")
    assert result.verdict == VerifyStatus.INVALID


def test_catch_all_domain_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_dns(monkeypatch, {"ghost.io": ["mx.ghost.io"]})
    _mock_smtp(monkeypatch, {"*": 250})  # accepts everything, incl. the random probe
    result = SmtpVerifier(smtp_enabled=True).verify("bob@ghost.io")
    assert result.verdict == VerifyStatus.CATCH_ALL
    assert result.status == EmailStatus.RISKY
    assert result.raw["catch_all"] is True
    assert result.sendable  # policy: catch-all may send, flagged


def test_greylisting_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_dns(monkeypatch, {"acme.com": ["mx1.acme.com"]})
    _mock_smtp(monkeypatch, {"ann@acme.com": 451})
    result = SmtpVerifier(smtp_enabled=True).verify("ann@acme.com")
    assert result.verdict == VerifyStatus.UNKNOWN
    assert result.sendable  # allowed, flagged


def test_invalid_never_sendable(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_dns(monkeypatch, {"ghost.io": None})
    assert not SmtpVerifier(smtp_enabled=False).verify("bob@ghost.io").sendable


def test_catch_all_probe_cached_per_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_dns(monkeypatch, {"acme.com": ["mx1.acme.com"]})
    calls = _mock_smtp(monkeypatch, {"ann@acme.com": 250, "bob@acme.com": 250, "*": 550})
    v = SmtpVerifier(smtp_enabled=True)
    v.verify("ann@acme.com")
    v.verify("bob@acme.com")
    probes = [c for c in calls if c.startswith("azul-")]
    assert len(probes) == 1  # second verify reuses the cached catch-all verdict


def test_catch_all_prospect_is_drafted_and_verdict_persisted(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path
    from typing import ClassVar

    from sqlalchemy import select

    from azul.db.models import Prospect
    from azul.db.session import session_scope
    from azul.orchestrator import campaign as camp
    from azul.orchestrator.graph import build_pipeline
    from azul.sourcing.base import EmailVerification, EmailVerifier

    class CatchAllVerifier(EmailVerifier):
        name: ClassVar[str] = "catchall"

        def verify(
            self, email: str, *, full_name: str | None = None, company_domain: str | None = None
        ) -> EmailVerification:
            return EmailVerification(
                email=email, status=EmailStatus.RISKY, provider=self.name,
                score=0.5, verdict=VerifyStatus.CATCH_ALL,
            )

    pipeline = build_pipeline(verifier=CatchAllVerifier())
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)

    assert isinstance(tmp_path, Path)
    p = tmp_path / "p.csv"
    p.write_text("email,full_name,company\nbob@ghost.io,Bob Stone,Ghost\n", encoding="utf-8")
    with session_scope() as s:
        cid = camp.run_campaign(
            s, tenant_slug="t1", name="Q1", rows=camp.load_prospects_csv(str(p))
        ).id
    with session_scope() as s:
        assert len(camp.list_drafts(s, cid)) == 1  # flagged, not skipped
        prospect = s.scalars(select(Prospect)).one()
        assert prospect.verify_status == VerifyStatus.CATCH_ALL
        assert prospect.verify_confidence == 0.5
        assert prospect.email_status == EmailStatus.RISKY
