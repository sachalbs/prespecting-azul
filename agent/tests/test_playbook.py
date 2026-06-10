"""The cold-outreach playbook ships at the repo root and loads as the system prompt."""

from __future__ import annotations

from pathlib import Path

from azul.writing import prompts


def test_playbook_file_exists_at_agent_root() -> None:
    assert Path("AZUL_COLD_OUTREACH_PLAYBOOK.md").exists()


def test_system_prompt_loads_the_playbook_not_the_fallback() -> None:
    prompts._load_playbook.cache_clear()  # pyright: ignore[reportPrivateUsage]
    text = prompts.system_prompt()
    # Distinctive phrases only the real playbook carries.
    assert "PLAYBOOK COLD OUTREACH" in text
    assert "La seule métrique : la réponse." in text
    assert prompts.FALLBACK_PLAYBOOK not in text
    # The JSON output contract is still appended so parsing stays stable.
    assert "hook_type" in text


def test_default_playbook_path_points_at_the_file() -> None:
    from azul.config import get_settings

    assert get_settings().writer_playbook_path == "AZUL_COLD_OUTREACH_PLAYBOOK.md"
