"""Tests for sim/broker.py."""
from __future__ import annotations

from sim.broker import MESSAGE_RETENTION_S, MessageBroker


def test_broadcast_then_collect_returns_message():
    b = MessageBroker()
    b.broadcast("ch", "A1", {"x": 1}, t_now=10.0)
    msgs = b.collect("ch", since=5.0, t_now=20.0)
    assert len(msgs) == 1
    assert msgs[0].sender_id == "A1"
    assert msgs[0].payload == {"x": 1}


def test_collect_excludes_messages_at_or_before_since():
    b = MessageBroker()
    b.broadcast("ch", "A1", {}, t_now=10.0)
    # since=10 strict → exclude t=10
    assert b.collect("ch", since=10.0, t_now=11.0) == []


def test_channels_are_isolated():
    b = MessageBroker()
    b.broadcast("ch1", "A1", {}, t_now=10.0)
    b.broadcast("ch2", "A2", {}, t_now=10.0)
    assert len(b.collect("ch1", since=0.0, t_now=11.0)) == 1
    assert len(b.collect("ch2", since=0.0, t_now=11.0)) == 1
    assert b.collect("ch3", since=0.0, t_now=11.0) == []


def test_retention_trims_messages_older_than_60_seconds():
    b = MessageBroker()
    b.broadcast("ch", "A1", {}, t_now=10.0)
    b.broadcast("ch", "A2", {}, t_now=20.0)
    # Force a trim by broadcasting beyond the retention window.
    b.broadcast("ch", "A3", {}, t_now=10.0 + MESSAGE_RETENTION_S + 1.0)
    # t=10 should be dropped; t=20 retained; t=71 retained.
    timestamps = sorted(m.timestamp for m in b.channels["ch"])
    assert timestamps == [20.0, 71.0]


def test_collect_respects_t_now_upper_bound():
    b = MessageBroker()
    b.broadcast("ch", "A1", {}, t_now=10.0)
    b.broadcast("ch", "A2", {}, t_now=20.0)
    msgs = b.collect("ch", since=0.0, t_now=15.0)
    assert len(msgs) == 1
    assert msgs[0].timestamp == 10.0
