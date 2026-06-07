"""Memory: episodic (what happened) vs procedural (winning patterns / skills).

Jalon 0 records episodic outcomes only. The procedural store + curator + eval
harness are stubs — they come online once we have real outcome data.
"""

from azul.memory.episodic import EpisodicMemory
from azul.memory.procedural import ProceduralMemory

__all__ = ["EpisodicMemory", "ProceduralMemory"]
