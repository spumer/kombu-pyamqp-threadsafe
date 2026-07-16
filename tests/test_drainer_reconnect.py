"""Integration tests: reconnect scenarios with the dedicated drainer enabled.

Reconnect coverage of the dedicated-drainer feature: the drainer
is pinned 1:1 to a ThreadSafeConnection (drainer.py module docstring). kombu's
reconnect builds a brand-new ThreadSafeConnection, so the old drainer must die
with the old connection and a fresh one must come up with the new one — with
no leaked thread and no reconnect storm when several application threads hit
the break concurrently.

Connection breaks here are a direct local close of the transport socket
(`close_transport`, same technique as tests/test_integration_reconnect.py),
not a toxiproxy-injected remote fault. This file was written alongside
several other agents each owning their own toxiproxy proxy on the shared
container (see docker-compose.test.yml), which only publishes 5672, 8474 and
25672 to the host; claiming a fourth port would mean editing and restarting
that already-running, shared compose file mid-session, tearing down the other
proxies with it. A local socket close exercises the same drainer code path —
the select() loop in drainer.py observes a dead local fd (OSError, or
transport.connected flipping False on the next tick) exactly as it would for
a remote break — without touching anyone else's proxy, port, or container.

Fixtures and helpers are duplicated locally on purpose (not imported from
tests/conftest.py or tests/test_drainer_integration.py) per this iteration's
brief: other agents are editing those files concurrently.
"""

import os
import threading
import time

import pytest

import kombu_pyamqp_threadsafe
from testing import PropagatingThread

RECONNECT_TIMEOUT = 8.0
THREAD_TIMEOUT = 8.0


def _drainer_thread_names() -> list[str]:
    return [t.name for t in threading.enumerate() if t.name.startswith("kombu-pyamqp-drainer-")]


def _count_open_fds() -> int:
    """Best-effort open-fd count for this process (duplicated locally on
    purpose — see module docstring — rather than imported).
    """
    for path in ("/proc/self/fd", "/dev/fd"):
        if os.path.isdir(path):
            return len(os.listdir(path))
    pytest.skip("no fd directory available on this platform")
    return 0  # unreachable


def close_transport(connection: kombu_pyamqp_threadsafe.KombuConnection) -> None:
    """Close the underlying transport socket to simulate a network failure.

    Same technique and same name as the helper in
    tests/test_integration_reconnect.py; duplicated here rather than
    imported (see module docstring).
    """
    if connection._connection and connection._connection._transport:
        connection._connection._transport.close()


def _wait_until(predicate, timeout: float = RECONNECT_TIMEOUT, interval: float = 0.05) -> bool:
    """Poll predicate() until it is truthy or timeout elapses.

    No sleep-and-hope: the drainer's detection latency is bounded by its poll
    tick (default 1s) plus scheduling, not instant, so callers that need to
    observe "break detected" wait on the actual condition instead of a fixed
    sleep.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


# kombu's own Connection._connection_factory() (called by _ensure_connection /
# ensure_connection) simply reassigns `self._connection = self._establish_
# connection()` and never calls collect()/close() on the connection it is
# replacing (kombu/connection.py:938-943). KombuConnection._connection_factory
# overrides it to snapshot the outgoing connection and explicitly stop its
# drainer (intentional=False) before building the replacement, so the old
# drainer's self-pipe fds are released right away instead of leaking, and the
# old/new coexistence window collapses to (effectively) zero. The drainer's own
# self-detection (transport.connected flips False, or select() errors on the
# closed fd, bounded by _DEFAULT_POLL_TICK_S = 1.0s) remains as a fallback for
# any path that bypasses the factory. Convergence to exactly one live drainer
# is still asserted below with a bounded wait.
DRAINER_CONVERGENCE_TIMEOUT = 2.5


def _wait_for_exactly_one_drainer_thread(timeout: float = DRAINER_CONVERGENCE_TIMEOUT) -> list[str]:
    names = _drainer_thread_names()
    if len(names) == 1:
        return names
    _wait_until(lambda: len(_drainer_thread_names()) == 1, timeout=timeout)
    return _drainer_thread_names()


def collect_thread_results(
    threads: list[PropagatingThread], timeout: float = THREAD_TIMEOUT
) -> list:
    """Join threads and collect return values (raises the first exception
    a PropagatingThread recorded, via its own join()).
    """
    results = []
    for idx, thread in enumerate(threads):
        thread.join(timeout=timeout)
        if thread.is_alive():
            pytest.fail(f"Test design error: thread {idx} did not complete in {timeout}s")
        results.append(thread.ret)
    return results


@pytest.fixture
def drainer_connection(rabbitmq_dsn):
    connection = kombu_pyamqp_threadsafe.KombuConnection(
        rabbitmq_dsn,
        transport_options={"dedicated_drainer": True},
        default_channel_pool_size=100,
    )
    yield connection
    connection.close()


class TestReconnectWithDrainer:
    """Test 1: ensure() + a broken connection recovers with the drainer on,
    and messages flow again through the new connection afterwards.
    """

    def test_ensure_connection_recovers_after_break_and_messages_flow(
        self, drainer_connection, queue_name
    ):
        connection = drainer_connection
        connection.connect()
        assert connection.connected
        assert len(_drainer_thread_names()) == 1

        close_transport(connection)

        assert _wait_until(lambda: not connection.connected), (
            "connection must be detected as broken after the local socket close"
        )

        connection.ensure_connection(max_retries=10, interval_start=0, interval_step=0.05)

        assert connection.connected
        names = _wait_for_exactly_one_drainer_thread()
        assert len(names) == 1, (
            f"exactly one drainer thread must be running for the new connection "
            f"after reconnect, got {names}"
        )

        # Fresh SimpleQueue built AFTER reconnect: it binds to
        # connection.default_channel at construction time, so it must be
        # created post-recovery to ride the new channel rather than one tied
        # to the transport that just died.
        queue = connection.SimpleQueue(queue_name)
        try:
            queue.clear()
            queue.put("hello-after-reconnect")
            message = queue.get(block=True, timeout=5)
            assert message.payload == "hello-after-reconnect"
            message.ack()
        finally:
            queue.clear()
            queue.close()


class TestNoThreadLeakAcrossReconnectCycles:
    """Test 2: M break/reconnect cycles leave exactly one live drainer
    thread and no dead ones lingering.
    """

    @pytest.mark.parametrize("cycles", [6])
    def test_exactly_one_drainer_thread_survives_m_reconnect_cycles(
        self, drainer_connection, queue_name, cycles: int
    ):
        connection = drainer_connection
        connection.connect()
        assert connection.connected
        assert len(_drainer_thread_names()) == 1

        for cycle in range(cycles):
            close_transport(connection)

            assert _wait_until(lambda: not connection.connected), (
                f"cycle {cycle}: break not detected within {RECONNECT_TIMEOUT}s"
            )

            connection.ensure_connection(max_retries=10, interval_start=0, interval_step=0.05)

            assert connection.connected, f"cycle {cycle}: did not reconnect"
            names = _wait_for_exactly_one_drainer_thread()
            assert len(names) == 1, (
                f"cycle {cycle}: expected exactly 1 drainer thread after reconnect "
                f"(within the {DRAINER_CONVERGENCE_TIMEOUT}s self-detection bound), "
                f"got {len(names)}: {names}"
            )

        # threading.enumerate() only ever returns *live* threads -- CPython
        # reaps finished ones automatically -- so this final count also
        # catches a drainer whose self-detection silently failed to actually
        # exit somewhere in the middle of the loop above and left an extra
        # live thread running alongside the current one.
        final = _wait_for_exactly_one_drainer_thread()
        assert len(final) == 1, f"drainer thread leak after {cycles} cycles: {final}"

        # The connection must still be fully usable after the last cycle.
        queue = connection.SimpleQueue(queue_name)
        try:
            queue.clear()
            queue.put("still-alive-after-cycles")
            message = queue.get(block=True, timeout=5)
            assert message.payload == "still-alive-after-cycles"
            message.ack()
        finally:
            queue.clear()
            queue.close()


class TestConcurrentPublishDuringBreakWithDrainer:
    """Test 3: adaptation of test_integration_reconnect.py's
    TestParallelEnsureRecovery (the "2e2cf64" anti-ping-pong regression) with
    the dedicated drainer enabled. Several application threads racing
    ensure() against one broken connection must converge on exactly one
    reconnect -- no storm, no deadlock -- and end with exactly one drainer
    thread.
    """

    @pytest.mark.parametrize("n_threads", [8])
    def test_one_socket_close_causes_one_reconnect(
        self, drainer_connection, queue_name, n_threads: int, mocker
    ):
        connection = drainer_connection

        kombu_pyamqp_threadsafe.kombu.Queue(queue_name, channel=connection).declare()
        assert connection.connected
        assert len(_drainer_thread_names()) == 1

        factory_spy = mocker.patch.object(
            connection, "_connection_factory", wraps=connection._connection_factory
        )

        close_transport(connection)

        def worker():
            def declare_queue():
                # Fresh pool channel per attempt, released immediately after:
                # the test targets the ensure() race itself, not channel
                # lifetime.
                ch = connection.default_channel_pool.acquire(block=True, timeout=5)
                try:
                    kombu_pyamqp_threadsafe.kombu.Queue(queue_name, channel=ch).declare()
                finally:
                    ch.release()

            ensured = connection.ensure(
                connection,
                declare_queue,
                max_retries=10,
                interval_start=0,
                interval_step=0,
                interval_max=0.05,
            )
            for _ in range(3):
                ensured()

        threads = [PropagatingThread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        collect_thread_results(threads)

        assert connection.connected
        names = _wait_for_exactly_one_drainer_thread()
        assert len(names) == 1, (
            f"exactly one drainer thread must survive the concurrent-publish reconnect, got {names}"
        )
        assert factory_spy.call_count == 1, (
            f"one socket close must cause exactly one reconnect, "
            f"got {factory_spy.call_count} "
            "(reconnect ping-pong: stale errors tore down live replacements)"
        )


class TestNoFdLeakAcrossReconnectCycles:
    """The orphaned old drainer's self-pipe (2 fds) must be released on every
    reconnect. Before the fix, ensure_connection() reconnect paths (no collect)
    leaked 2 fds per cycle because the old drainer self-terminated but nothing
    called stop() to close its pipe.
    """

    @pytest.mark.parametrize("cycles", [8])
    def test_ensure_connection_reconnects_do_not_leak_fds(
        self, drainer_connection, queue_name, cycles: int
    ):
        connection = drainer_connection
        connection.connect()
        assert connection.connected
        assert len(_drainer_thread_names()) == 1

        # Baseline after the first connect: the steady state is one drainer and
        # one transport socket, so a leak-free run returns here.
        fds_before = _count_open_fds()

        for cycle in range(cycles):
            close_transport(connection)
            assert _wait_until(lambda: not connection.connected), (
                f"cycle {cycle}: break not detected within {RECONNECT_TIMEOUT}s"
            )
            connection.ensure_connection(max_retries=10, interval_start=0, interval_step=0.05)
            assert connection.connected, f"cycle {cycle}: did not reconnect"
            _wait_for_exactly_one_drainer_thread()

        fds_after = _count_open_fds()
        delta = fds_after - fds_before

        # A 2-fd/cycle self-pipe leak would be delta ~= 2*cycles; the socket is
        # swapped 1-for-1 so it nets to zero. Threshold well under 2*cycles,
        # with slack for incidental churn.
        assert delta < cycles, (
            f"fd leak across {cycles} ensure_connection reconnects: "
            f"{fds_before} -> {fds_after} (delta {delta}, expected ~0)"
        )

    def test_factory_stops_the_old_connections_drainer(self, drainer_connection):
        """The replaced connection's drainer is explicitly stopped (pipe closed,
        fresh drainer on the new connection) — not left to orphan.
        """
        connection = drainer_connection
        connection.connect()
        old_conn = connection._connection
        old_drainer = old_conn._drainer

        close_transport(connection)
        assert _wait_until(lambda: not connection.connected)
        connection.ensure_connection(max_retries=10, interval_start=0, interval_step=0.05)

        new_conn = connection._connection
        assert new_conn is not old_conn, "reconnect must build a new ThreadSafeConnection"
        assert new_conn._drainer is not old_drainer, "new connection needs its own drainer"
        assert old_drainer._closed is True, (
            "the old drainer's self-pipe must be closed by the factory stop() "
            "(otherwise it leaks 2 fds)"
        )


class TestOrphanedWaiterStaysRecoverable:
    """A consumer parked on the connection being replaced must get a RECOVERABLE
    error (so ensure()/Consumer reconnects), never ConnectionClosedIntentionally
    — stopping the old drainer from the reconnect factory is a failure-driven
    replacement, not an application close (interaction with the intentional-close
    signal).
    """

    def test_reconnect_wakes_orphaned_waiter_recoverable(self, drainer_connection):
        connection = drainer_connection
        connection.connect()
        old_conn = connection._connection

        errors: list[Exception] = []
        parked = threading.Event()

        def waiter():
            parked.set()
            try:
                old_conn.drain_events(timeout=None)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=waiter)
        thread.start()
        assert parked.wait(timeout=2.0)
        time.sleep(0.3)  # park in wait_activity of the old connection

        close_transport(connection)
        connection.ensure_connection(max_retries=10, interval_start=0, interval_step=0.05)

        thread.join(timeout=THREAD_TIMEOUT)
        if thread.is_alive():
            pytest.fail("orphaned waiter hung across the reconnect")

        assert len(errors) == 1, f"expected exactly one error, got {errors}"
        assert isinstance(errors[0], connection.recoverable_connection_errors), (
            f"orphaned waiter on a replaced connection must be recoverable, got {errors[0]!r}"
        )
        assert not isinstance(errors[0], kombu_pyamqp_threadsafe.ConnectionClosedIntentionally), (
            "a reconnect replacement must NOT surface an intentional-close signal"
        )
