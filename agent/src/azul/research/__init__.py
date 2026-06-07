"""Deep research, behind the swappable `ResearchEngine` interface."""

from azul.research.base import Hook, ResearchEngine, ResearchResult
from azul.research.factory import get_research_engine

__all__ = ["Hook", "ResearchEngine", "ResearchResult", "get_research_engine"]
