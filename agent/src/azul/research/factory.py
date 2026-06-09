"""Pick the research backend from settings."""

from __future__ import annotations

from azul.config import get_settings
from azul.research.base import ResearchEngine
from azul.research.stub import StubResearchEngine


def get_research_engine() -> ResearchEngine:
    name = get_settings().research_engine
    if name == "holo3":
        from azul.research.holo3 import Holo3ResearchEngine

        return Holo3ResearchEngine()
    if name == "dossier":
        from azul.research.dossier import DossierResearchEngine

        return DossierResearchEngine()
    return StubResearchEngine()
