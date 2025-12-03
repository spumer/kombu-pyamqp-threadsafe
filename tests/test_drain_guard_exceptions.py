"""Tests for DrainGuard exception propagation.

Verifies:
- Exceptions from drain thread propagate to waiting threads
- Threads arriving after drain finished don't get old exceptions
"""

import threading

import pytest

from kombu_pyamqp_threadsafe import DrainGuard
from testing import PropagatingThread


@pytest.fixture
def guard() -> DrainGuard:
    """Provide fresh DrainGuard instance for each test."""
    return DrainGuard()


class TestExceptionPropagation:
    """Tests for exception propagation from drain to waiters."""

    def test_waiter_receives_exception(self, guard: DrainGuard) -> None:
        """Waiter thread gets exception from drain thread."""
        drain_started = threading.Event()
        waiter_ready = threading.Event()
        exc_received = []

        def drainer():
            guard.start_drain()
            drain_started.set()
            waiter_ready.wait(timeout=2.0)
            guard.finish_drain(exc=ValueError("test error"))

        def waiter():
            drain_started.wait(timeout=2.0)
            waiter_ready.set()
            try:
                guard.wait_drain_finished(timeout=2.0)
                pytest.fail("Expected ValueError but none was raised")
            except ValueError as e:
                exc_received.append(str(e))

        t1 = PropagatingThread(target=drainer)
        t2 = PropagatingThread(target=waiter)
        t1.start()
        t2.start()
        t1.join(2.0)
        t2.join(2.0)

        assert exc_received == ["test error"]

    def test_late_waiter_gets_no_exception(self, guard: DrainGuard) -> None:
        """Thread arriving after drain finished doesn't get old exception."""
        guard.start_drain()
        guard.finish_drain(exc=ValueError("old exception"))

        # Call wait_drain_finished when drain already inactive
        guard.wait_drain_finished(timeout=2.0)

        # No exception raised - test passed
