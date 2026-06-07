"""Sending + reply sync, behind the swappable `Channel` interface.

Sending is always an API call from the user's real mailbox — never computer-use.
"""

from azul.connectors.base import Channel, InboundReply, OutboundMessage, SendResult
from azul.connectors.factory import get_channel

__all__ = ["Channel", "InboundReply", "OutboundMessage", "SendResult", "get_channel"]
