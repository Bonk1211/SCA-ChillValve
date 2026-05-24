"""In-process message broker. PRD §7.2 (sync adaptation for Phase 3).

Phase 5 will wrap this in asyncio when FastAPI lands.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List

MESSAGE_RETENTION_S = 60.0


@dataclass
class Message:
    channel: str
    sender_id: str
    payload: Dict[str, Any]
    timestamp: float   # simulated seconds


@dataclass
class MessageBroker:
    channels: Dict[str, List[Message]] = field(default_factory=lambda: defaultdict(list))

    def broadcast(
        self,
        channel: str,
        sender_id: str,
        payload: Dict[str, Any],
        t_now: float,
    ) -> None:
        self.channels[channel].append(Message(channel, sender_id, payload, t_now))
        cutoff = t_now - MESSAGE_RETENTION_S
        self.channels[channel] = [m for m in self.channels[channel] if m.timestamp >= cutoff]

    def collect(self, channel: str, since: float, t_now: float) -> List[Message]:
        return [
            m for m in self.channels.get(channel, [])
            if m.timestamp > since and m.timestamp <= t_now
        ]
