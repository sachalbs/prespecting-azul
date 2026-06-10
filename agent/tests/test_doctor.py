"""Doctor live checks: every external call mocked, OK/FAIL + remedy verified."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
import respx

import azul.cli.doctor as doctor_mod
from azul.cli.doctor import (
    Check,
    check_db,
    check_dns_auth,
    check_graph,
    check_tavily,
    check_writer,
    run_live_checks,
)
from azul.config import Settings


def _settings(**kv: Any) -> Settings:
    return Settings(**kv)


# ── DB ───────────────────────────────────────────────────────────────────────


def test_db_check_ok_with_schema() -> None:
    # conftest created the schema on the test database.
    check = check_db(_settings())
    assert check.ok


# ── Tavily ───────────────────────────────────────────────────────────────────


def test_tavily_missing_key_fails_with_remedy() -> None:
    check = check_tavily(_settings(tavily_api_key=None))
    assert not check.ok and "TAVILY_API_KEY" in check.detail


def test_tavily_real_search_ok() -> None:
    with respx.mock(base_url="https://api.tavily.com") as router:
        router.post("/search").mock(return_value=httpx.Response(200, json={"results": []}))
        check = check_tavily(_settings(tavily_api_key="k"))
    assert check.ok


def test_tavily_401_fails() -> None:
    with respx.mock(base_url="https://api.tavily.com") as router:
        router.post("/search").mock(return_value=httpx.Response(401))
        check = check_tavily(_settings(tavily_api_key="bad"))
    assert not check.ok and "401" in check.detail


# ── Writer ───────────────────────────────────────────────────────────────────


def test_writer_one_token_completion_ok() -> None:
    s = _settings(
        writer_base_url="https://api.deepseek.com/v1",
        writer_api_key="k",
        writer_model="deepseek-chat",
    )
    with respx.mock(base_url="https://api.deepseek.com/v1") as router:
        route = router.post("/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": "."}}]})
        )
        check = check_writer(s)
    assert check.ok
    assert json.loads(route.calls[0].request.content)["max_tokens"] == 1


def test_writer_unknown_model_fails_with_remedy() -> None:
    s = _settings(
        writer_base_url="https://api.deepseek.com/v1",
        writer_api_key="k",
        writer_model="nope-1",
    )
    with respx.mock(base_url="https://api.deepseek.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(404))
        check = check_writer(s)
    assert not check.ok and "nope-1" in check.detail


# ── Graph ────────────────────────────────────────────────────────────────────


def _jwt(scp: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"scp": scp}).encode()).decode().rstrip("=")
    return f"h.{payload}.sig"


def test_graph_ok_with_mail_send_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    def token_full() -> str:
        return _jwt("Mail.Send Mail.Read")

    monkeypatch.setattr(doctor_mod, "_acquire_token", token_full)
    with respx.mock(base_url="https://graph.microsoft.com/v1.0") as router:
        router.get("/me").mock(
            return_value=httpx.Response(200, json={"mail": "me@contoso.com"})
        )
        checks, domain = check_graph(_settings())
    assert all(c.ok for c in checks)
    assert domain == "contoso.com"


def test_graph_missing_mail_send_scope_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def token_partial() -> str:
        return _jwt("Mail.Read")

    monkeypatch.setattr(doctor_mod, "_acquire_token", token_partial)
    with respx.mock(base_url="https://graph.microsoft.com/v1.0") as router:
        router.get("/me").mock(return_value=httpx.Response(200, json={"mail": "me@contoso.com"}))
        checks, _ = check_graph(_settings())
    scope_check = next(c for c in checks if c.name == "Mail.Send scope")
    assert not scope_check.ok and "auth-email" in scope_check.detail


def test_graph_no_cached_token_fails_with_remedy(monkeypatch: pytest.MonkeyPatch) -> None:
    from azul.errors import ChannelError

    def boom() -> str:
        raise ChannelError("No cached Graph token")

    monkeypatch.setattr(doctor_mod, "_acquire_token", boom)
    checks, domain = check_graph(_settings())
    assert len(checks) == 1 and not checks[0].ok
    assert "auth-email" in checks[0].detail
    assert domain is None


# ── SPF / DKIM / DMARC ──────────────────────────────────────────────────────


def test_dns_auth_human_language(monkeypatch: pytest.MonkeyPatch) -> None:
    txt = {
        "contoso.com": ["v=spf1 include:spf.protection.outlook.com -all"],
        "_dmarc.contoso.com": ["v=DMARC1; p=none"],
    }
    def fake_txt(name: str) -> list[str]:
        return txt.get(name, [])

    def fake_exists(name: str) -> bool:
        return name == "selector1._domainkey.contoso.com"

    monkeypatch.setattr(doctor_mod, "_txt_records", fake_txt)
    monkeypatch.setattr(doctor_mod, "_name_exists", fake_exists)
    checks = check_dns_auth("contoso.com")
    by_name = {c.name: c for c in checks}
    assert by_name["SPF"].ok and "who may send" in by_name["SPF"].detail
    assert by_name["DKIM"].ok and "selector1" in by_name["DKIM"].detail
    assert by_name["DMARC"].ok


def test_dns_auth_missing_records_explain_the_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_txt(name: str) -> list[str]:
        return []

    def no_name(name: str) -> bool:
        return False

    monkeypatch.setattr(doctor_mod, "_txt_records", no_txt)
    monkeypatch.setattr(doctor_mod, "_name_exists", no_name)
    checks = check_dns_auth("ghost.io")
    assert all(not c.ok for c in checks)
    assert any("v=spf1" in c.detail for c in checks)
    assert any("v=DMARC1" in c.detail for c in checks)


# ── Orchestration ────────────────────────────────────────────────────────────


def test_run_live_checks_selects_by_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(research_engine="tiered", writer_provider="openai_compat", channel="stub")

    def fake(name: str) -> Any:
        def _check(settings: Settings) -> Check:
            return Check(name, True)

        return _check

    monkeypatch.setattr(doctor_mod, "check_db", fake("DB"))
    monkeypatch.setattr(doctor_mod, "check_tavily", fake("Tavily"))
    monkeypatch.setattr(doctor_mod, "check_writer", fake("Writer"))
    monkeypatch.setattr(doctor_mod, "check_holo", fake("Holo"))
    names = [c.name for c in run_live_checks(s)]
    assert names == ["DB", "Tavily", "Writer", "Holo"]  # no Graph/DNS on stub channel


def test_run_live_checks_explicit_domain_runs_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings()

    def fake_db(settings: Settings) -> Check:
        return Check("DB", True)

    def fake_dns(domain: str) -> list[Check]:
        return [Check("SPF", True, domain)]

    monkeypatch.setattr(doctor_mod, "check_db", fake_db)
    monkeypatch.setattr(doctor_mod, "check_dns_auth", fake_dns)
    checks = run_live_checks(s, domain="contoso.com")
    assert any(c.name == "SPF" and c.detail == "contoso.com" for c in checks)


# ── deliverability-check ─────────────────────────────────────────────────────


class _RecordingChannel:
    name = "graph"

    def __init__(self) -> None:
        self.sent: list[Any] = []

    def send(self, message: Any) -> Any:
        from azul.connectors.base import SendResult

        self.sent.append(message)
        return SendResult(external_id=f"ext-{len(self.sent)}")


def test_deliverability_check_sends_to_tester_and_three_seeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from azul.cli.doctor import run_deliverability_check

    ch = _RecordingChannel()

    def fake_channel() -> Any:
        return ch

    import azul.connectors as connectors_mod

    monkeypatch.setattr(connectors_mod, "get_channel", fake_channel)
    s = _settings(
        channel="graph",
        seed_inboxes="a@gmail.test, b@yahoo.test, c@proton.test, d@too-many.test",
    )
    sent = run_deliverability_check(s, "web-x@mail-tester.com")
    assert sent[0] == "web-x@mail-tester.com"
    assert len(sent) == 4  # tester + 3 seeds max, the 4th seed dropped
    assert "d@too-many.test" not in sent
    assert all(m.dedup_key.startswith("deliverability:") for m in ch.sent)


def test_deliverability_check_refuses_off_graph_channel() -> None:
    from azul.cli.doctor import run_deliverability_check
    from azul.errors import ConfigError

    with pytest.raises(ConfigError):
        run_deliverability_check(_settings(channel="stub"), "web-x@mail-tester.com")
