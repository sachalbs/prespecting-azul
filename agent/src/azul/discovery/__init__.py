"""Prospect discovery: an ICP brief -> a list of leads (name + company + domain).

The least reliable link without a data provider (Apollo/Lusha) — web search +
extraction. Behind a `Discoverer` interface so it's swappable; the human approves
the discovered list before we spend anything finding emails or writing.
"""

from azul.discovery.base import Discoverer, Lead
from azul.discovery.factory import get_discoverer

__all__ = ["Discoverer", "Lead", "get_discoverer"]
