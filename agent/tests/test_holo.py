"""Holo3 agent-loop parsing + coordinate remap (pure units, no browser/network)."""

from __future__ import annotations

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
