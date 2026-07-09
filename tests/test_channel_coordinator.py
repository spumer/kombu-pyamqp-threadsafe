"""Unit tests for ChannelCoordinator synchronization primitive.

ChannelCoordinator counts active operations on a channel — operations between
enter_operation and exit_operation — and lets teardown wait until
active_operations == 0 before nulling channel.connection. New operations started
after begin_teardown() are rejected with a recoverable error.
"""

import threading
import time

import pytest
from amqp import RecoverableConnectionError

from kombu_pyamqp_threadsafe import ChannelCoordinator
from testing import PropagatingThread


@pytest.fixture
def coord() -> ChannelCoordinator:
    """A coordinator with a short teardown wait to keep timing tests fast."""
    return ChannelCoordinator(teardown_wait_s=0.2)


def test_new_coordinator_has_no_active_operations_and_is_not_marked(
    coord: ChannelCoordinator,
) -> None:
    """A fresh coordinator starts with no active operations and unmarked."""
    assert coord.active_operations == 0
    assert coord.marked_for_teardown is False


def test_enter_operation_increments_active_operations(coord: ChannelCoordinator) -> None:
    """Each enter_operation raises active_operations by one."""
    coord.enter_operation()
    assert coord.active_operations == 1

    coord.enter_operation()
    assert coord.active_operations == 2

    coord.exit_operation()
    coord.exit_operation()


def test_exit_operation_decrements_active_operations(coord: ChannelCoordinator) -> None:
    """Each exit_operation lowers active_operations by one."""
    coord.enter_operation()
    coord.enter_operation()
    coord.exit_operation()
    assert coord.active_operations == 1

    coord.exit_operation()
    assert coord.active_operations == 0


def test_enter_operation_after_teardown_marked_raises_recoverable(
    coord: ChannelCoordinator,
) -> None:
    """Once teardown is marked, a new enter_operation is rejected."""
    coord.begin_teardown()  # marks; active_operations already 0 -> returns True

    with pytest.raises(RecoverableConnectionError):
        coord.enter_operation()


def test_begin_teardown_with_no_active_operations_returns_true_immediately(
    coord: ChannelCoordinator,
) -> None:
    """With nothing in flight, begin_teardown marks and returns True at once."""
    started = time.monotonic()
    result = coord.begin_teardown()
    elapsed = time.monotonic() - started

    assert result is True
    # returned immediately (no wait)
    assert elapsed < 0.05
    assert coord.marked_for_teardown is True


def test_begin_teardown_blocks_until_active_operation_exits(coord: ChannelCoordinator) -> None:
    """begin_teardown blocks until the one active operation exits, then True."""
    coord.enter_operation()

    worker_done = threading.Event()

    def worker() -> None:
        time.sleep(0.05)
        coord.exit_operation()
        worker_done.set()

    t = PropagatingThread(target=worker)
    t.start()

    started = time.monotonic()
    result = coord.begin_teardown()
    elapsed = time.monotonic() - started

    assert result is True
    assert elapsed >= 0.04  # waited for the worker
    assert worker_done.is_set()

    t.join(timeout=1.0)


def test_begin_teardown_while_another_teardown_is_draining_returns_true_without_waiting(
    coord: ChannelCoordinator,
) -> None:
    """A second begin_teardown returns True at once, without waiting on the drain the first caller owns."""
    coord.enter_operation()  # keep an operation active so a real wait would block

    first_caller_result: list[bool] = []

    def first_caller_teardown() -> None:
        first_caller_result.append(coord.begin_teardown())  # this one waits (and times out)

    t = PropagatingThread(target=first_caller_teardown)
    t.start()

    # Give the first caller time to mark teardown and enter its wait.
    time.sleep(0.05)
    assert coord.marked_for_teardown is True

    started = time.monotonic()
    result = coord.begin_teardown()
    elapsed = time.monotonic() - started

    assert result is True
    assert elapsed < 0.05  # returned without waiting on the drain

    # the first caller still owns the drain; release the operation so it
    # completes and observes active_operations == 0
    coord.exit_operation()
    t.join(timeout=1.0)
    assert first_caller_result == [True]


def test_begin_teardown_returns_false_when_active_operation_never_exits(
    coord: ChannelCoordinator,
) -> None:
    """begin_teardown returns False when active_operations never reaches 0."""
    coord.enter_operation()

    started = time.monotonic()
    result = coord.begin_teardown()
    elapsed = time.monotonic() - started

    assert result is False
    # slept ~teardown_wait_s (0.2)
    assert 0.15 <= elapsed <= 0.5
    # marked stays set even after timeout — new operations are rejected
    assert coord.marked_for_teardown is True

    # cleanup
    coord.exit_operation()


def test_begin_teardown_waits_until_all_active_operations_across_threads_exit(
    coord: ChannelCoordinator,
) -> None:
    """begin_teardown waits for the last of several concurrent operations to exit, without a false timeout."""
    n_workers = 8
    all_entered = threading.Barrier(n_workers + 1)
    release = threading.Event()

    def worker() -> None:
        coord.enter_operation()
        all_entered.wait(timeout=2.0)
        release.wait(timeout=2.0)
        coord.exit_operation()

    threads = [PropagatingThread(target=worker) for _ in range(n_workers)]
    for t in threads:
        t.start()

    # Wait until every worker holds an active operation.
    all_entered.wait(timeout=2.0)
    assert coord.active_operations == n_workers

    # Let workers exit shortly after we start waiting, to prove teardown
    # actually blocks until active_operations reaches zero.
    def releaser() -> None:
        time.sleep(0.05)
        release.set()

    r = threading.Thread(target=releaser)
    r.start()

    started = time.monotonic()
    result = coord.begin_teardown()
    elapsed = time.monotonic() - started

    assert result is True
    assert elapsed >= 0.04  # waited for all operations to drain
    assert coord.active_operations == 0

    for t in threads:
        t.join(timeout=2.0)
    r.join(timeout=1.0)


def test_concurrent_enter_exit_leaves_active_operations_at_zero(coord: ChannelCoordinator) -> None:
    """Balanced enter/exit from many threads leaves no lost updates: active_operations returns to 0."""
    n_workers = 16
    iterations = 200
    barrier = threading.Barrier(n_workers)

    def worker() -> None:
        barrier.wait(timeout=2.0)
        for _ in range(iterations):
            coord.enter_operation()
            coord.exit_operation()

    threads = [PropagatingThread(target=worker) for _ in range(n_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert coord.active_operations == 0
