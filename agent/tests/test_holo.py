"""Holo3 agent-loop parsing + coordinate remap (pure units, no browser/network)."""

from __future__ import annotations

import pytest

from azul.research.holo3 import (
    Holo3ResearchEngine,
    HoloAction,
    parse_holo_message,
    remap_point,
)


def test_parse_json_envelope() -> None:
    msg = {
        "content": (
            '{"note":"n","thought":"t",'
            '"tool_call":{"name":"click","arguments":{"x":500,"y":250}}}'
        )
    }
    action = parse_holo_message(msg)
    assert action.name == "click"
    assert action.args == {"x": 500, "y": 250}
    assert action.note == "n"


def test_parse_native_tool_calls() -> None:
    msg = {
        "content": None,
        "tool_calls": [{"function": {"name": "type", "arguments": '{"text":"hi"}'}}],
    }
    action = parse_holo_message(msg)
    assert action.name == "type"
    assert action.args["text"] == "hi"


def test_remap_normalised_to_pixels() -> None:
    assert remap_point({"x": 500, "y": 250}, 1280, 800) == (640.0, 200.0)
    assert remap_point({"point": [1000, 1000]}, 1000, 500) == (1000.0, 500.0)


def test_task_complete_hooks() -> None:
    action = HoloAction(
        name="task_complete",
        args={"hooks": [{"text": "Posted about RevOps pain", "source_url": "u"}]},
    )
    hooks = Holo3ResearchEngine.hooks_from_complete(action)
    assert len(hooks) == 1
    assert hooks[0].text == "Posted about RevOps pain"


def test_task_complete_falls_back_to_note() -> None:
    action = HoloAction(name="task_complete", args={}, note="Spoke at a logistics conf")
    hooks = Holo3ResearchEngine.hooks_from_complete(action)
    assert len(hooks) == 1
    assert "logistics" in hooks[0].text


def test_parse_normalises_action_aliases() -> None:
    msg = {
        "content": '{"tool_call":{"name":"left_click","arguments":{"x":10,"y":20}}}'
    }
    action = parse_holo_message(msg)
    assert action.name == "click"

    msg = {"content": '{"tool_call":{"name":"scroll_down","arguments":{}}}'}
    action = parse_holo_message(msg)
    assert action.name == "scroll"
    assert action.args["direction"] == "down"

    msg = {
        "content": None,
        "tool_calls": [{"function": {"name": "FINISH", "arguments": "{}"}}],
    }
    assert parse_holo_message(msg).name == "task_complete"

    msg = {"content": '{"tool_call":{"name":"navigate","arguments":{"url":"https://x.y"}}}'}
    assert parse_holo_message(msg).name == "goto"


class _FakeMouse:
    def click(self, x: float, y: float) -> None: ...
    def wheel(self, dx: int, dy: int) -> None: ...
    def move(self, x: float, y: float) -> None: ...
    def down(self) -> None: ...
    def up(self) -> None: ...


class _FakeKeyboard:
    def type(self, text: str) -> None: ...
    def press(self, key: str) -> None: ...


class _FakePage:
    url = "https://fake.example"
    viewport_size = {"width": 1000, "height": 1000}
    mouse = _FakeMouse()
    keyboard = _FakeKeyboard()

    def goto(self, url: str, wait_until: str | None = None) -> None:
        self.url = url

    def screenshot(self) -> bytes:
        return b"\x89PNG-fake"


class _FakeContext:
    def add_init_script(self, script: str) -> None: ...
    def new_page(self) -> _FakePage:
        return _FakePage()


class _FakeBrowser:
    def new_context(self, **kwargs: object) -> _FakeContext:
        return _FakeContext()

    def close(self) -> None: ...


class _FakeChromium:
    def launch(self, **kwargs: object) -> _FakeBrowser:
        return _FakeBrowser()


class _FakePw:
    chromium = _FakeChromium()


class _FakeSyncPlaywright:
    def __enter__(self) -> _FakePw:
        return _FakePw()

    def __exit__(self, *args: object) -> None: ...


def test_garbage_replies_get_two_corrections_then_fallback_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3 invalid replies in a row -> 2 corrective turns, then hooks=[] (no raise)."""
    import httpx
    import playwright.sync_api as pw_api
    import respx

    from azul.config import get_settings
    from azul.domain import ProspectBrief

    monkeypatch.setattr(pw_api, "sync_playwright", lambda: _FakeSyncPlaywright())
    monkeypatch.setenv("HAI_API_KEY", "k")
    get_settings.cache_clear()

    bodies = []
    garbage = {"choices": [{"message": {"content": "no json here, sorry"}}]}
    with respx.mock(base_url="https://api.hcompany.ai/v1") as router:
        def _record(request: httpx.Request) -> httpx.Response:
            bodies.append(request.read().decode())
            return httpx.Response(200, json=garbage)

        router.post("/chat/completions").mock(side_effect=_record)
        try:
            engine = Holo3ResearchEngine()
            result = engine.research(ProspectBrief(email="a@b.com", full_name="Ann Lee"))
        finally:
            get_settings.cache_clear()

    assert result.hooks == []  # fallback, not an exception
    assert len(bodies) == 3  # initial + 2 corrective rounds, then gave up
    assert "Your last reply was invalid" in bodies[-1]


def test_unknown_action_gets_correction_then_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx
    import playwright.sync_api as pw_api
    import respx

    from azul.config import get_settings
    from azul.domain import ProspectBrief

    monkeypatch.setattr(pw_api, "sync_playwright", lambda: _FakeSyncPlaywright())
    monkeypatch.setenv("HAI_API_KEY", "k")
    get_settings.cache_clear()

    replies = [
        {"choices": [{"message": {"content": '{"tool_call":{"name":"levitate","arguments":{}}}'}}]},
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"tool_call":{"name":"task_complete",'
                            '"arguments":{"hooks":[{"text":"found it","source_url":"u"}]}}}'
                        )
                    }
                }
            ]
        },
    ]
    with respx.mock(base_url="https://api.hcompany.ai/v1") as router:
        router.post("/chat/completions").mock(
            side_effect=[httpx.Response(200, json=r) for r in replies]
        )
        try:
            result = Holo3ResearchEngine().research(
                ProspectBrief(email="a@b.com", full_name="Ann Lee")
            )
        finally:
            get_settings.cache_clear()

    assert [h.text for h in result.hooks] == ["found it"]
