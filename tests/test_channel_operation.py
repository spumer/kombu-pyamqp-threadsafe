"""Unit tests for channel_operation() context manager.

channel_operation() wraps any critical section over channel.connection. It:
- raises RecoverableConnectionError, before running the body, when the
  connection or channel is under teardown;
- snapshots channel.connection so the object stays alive for the whole body;
- counts active operations, so channel.collect() can wait for our exit.
"""

import threading

import pytest
from amqp import RecoverableConnectionError

from kombu_pyamqp_threadsafe import (
    ChannelCoordinator,
    channel_operation,
)


class FakeConnection:
    """Minimal stand-in for ThreadSafeConnection in unit tests."""

    def __init__(self) -> None:
        self._teardown_event = threading.Event()
        # lets a test confirm it still holds this object after connection reset
        self.marker = "alive"

    @property
    def marked_for_teardown(self) -> bool:
        return self._teardown_event.is_set()

    def mark_for_teardown(self) -> None:
        self._teardown_event.set()


class FakeChannel:
    """Minimal stand-in for ThreadSafeChannel in unit tests."""

    def __init__(self, connection: FakeConnection | None) -> None:
        self.connection = connection
        self._coordinator = ChannelCoordinator(teardown_wait_s=0.2)


@pytest.fixture
def conn() -> FakeConnection:
    return FakeConnection()


@pytest.fixture
def channel(conn: FakeConnection) -> FakeChannel:
    return FakeChannel(conn)


def test_yields_the_channel_connection(channel: FakeChannel, conn: FakeConnection) -> None:
    """The context manager yields the channel's own connection."""
    with channel_operation(channel) as snapshot:
        assert snapshot is conn


def test_active_operations_is_one_inside_body_and_zero_outside(channel: FakeChannel) -> None:
    """The operation is counted on the coordinator only for the body's duration."""
    assert channel._coordinator.active_operations == 0

    with channel_operation(channel):
        assert channel._coordinator.active_operations == 1

    assert channel._coordinator.active_operations == 0


def test_raises_when_connection_marked_for_teardown(
    channel: FakeChannel, conn: FakeConnection
) -> None:
    """A connection marked for teardown is rejected before the body runs."""
    conn.mark_for_teardown()

    with pytest.raises(RecoverableConnectionError), channel_operation(channel):
        pytest.fail("must not enter operation when connection is marked for teardown")

    assert channel._coordinator.active_operations == 0


def test_raises_when_coordinator_marked_for_teardown(channel: FakeChannel) -> None:
    """A channel whose coordinator is marked for teardown is rejected before the body runs."""
    channel._coordinator.begin_teardown()

    with pytest.raises(RecoverableConnectionError), channel_operation(channel):
        pytest.fail("body must not run when coordinator is marked for teardown")


def test_raises_when_connection_is_none(channel: FakeChannel) -> None:
    """A channel with no connection is rejected before the body runs."""
    # channel_operation reads channel.connection once. When it is already
    # None, the CM must raise RecoverableConnectionError before touching
    # conn.marked_for_teardown (which would raise AttributeError on None)
    # and before running the body.
    channel.connection = None
    with pytest.raises(RecoverableConnectionError), channel_operation(channel):
        pytest.fail("must not enter body when connection is None")


def test_snapshot_survives_channel_connection_reset(
    channel: FakeChannel, conn: FakeConnection
) -> None:
    """After entering the CM, channel.connection can be nulled from outside; the
    yielded snapshot must still refer to the original.
    """
    with channel_operation(channel) as snapshot:
        channel.connection = None
        # snapshot is a local reference - keeps the original alive
        assert snapshot is conn
        assert snapshot.marker == "alive"


def test_exit_decrements_active_operations_when_body_raises(channel: FakeChannel) -> None:
    """An exception in the body still decrements the active-operations count."""
    with pytest.raises(RuntimeError), channel_operation(channel):
        assert channel._coordinator.active_operations == 1
        raise RuntimeError("boom")

    assert channel._coordinator.active_operations == 0
