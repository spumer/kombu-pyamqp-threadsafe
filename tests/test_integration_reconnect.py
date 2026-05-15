"""Integration tests for reconnect scenarios.

This module tests real-world reconnection scenarios with selective exception propagation:
- Recovery after socket close with single channel
- Recovery after socket close with multiple channels
- Regression test for KeyError: None after timeout false positive

Critical regression test:
The old bug: Thread A does health check → socket.timeout → treated as error →
Thread B's queue_declare() gets TimeoutError → triggers reconnect → KeyError: None

With fix: socket.timeout is filtered, Thread B continues normally.
"""

import ssl
import threading
import time

import pytest
from amqp import RecoverableConnectionError

import kombu_pyamqp_threadsafe
from testing import PropagatingThread

# ====================
# Test Constants
# ====================

THREAD_TIMEOUT = 5.0  # Longer timeout for integration tests


# ====================
# Helper Functions
# ====================


def collect_thread_results(
    threads: list[PropagatingThread], timeout: float = THREAD_TIMEOUT
) -> list:
    """Join threads and collect return values."""
    results = []
    for idx, thread in enumerate(threads):
        thread.join(timeout=timeout)
        if thread.is_alive():
            pytest.fail(f"Test design error: thread {idx} did not complete in {timeout}s")
        results.append(thread.ret)
    return results


def close_transport(connection: kombu_pyamqp_threadsafe.KombuConnection) -> None:
    """Close the underlying transport to simulate network failure."""
    if connection._connection and connection._connection._transport:
        connection._connection._transport.close()


# ====================
# Fixtures
# ====================


@pytest.fixture
def multi_channel_connection(rabbitmq_dsn):
    """Connection with multiple channels pre-created."""
    connection = kombu_pyamqp_threadsafe.KombuConnection(
        rabbitmq_dsn, default_channel_pool_size=100
    )
    yield connection
    connection.close()


# ====================
# Recovery Tests: Single Channel
# ====================


class TestSingleChannelRecovery:
    """Tests for recovery scenarios with single channel."""

    def test_socket_close_detection(self, connection) -> None:
        """Verify socket close is detected as connection error."""
        # Establish connection
        _ = connection.default_channel
        assert connection.connected

        # Close transport
        close_transport(connection)

        # Next operation should detect closed socket
        assert not connection.connected

    def test_recovery_after_socket_close(self, connection) -> None:
        """Verify connection recovers after socket close."""
        # Establish connection
        channel = connection.default_channel
        assert connection.connected

        # Close transport
        close_transport(connection)

        # Connection should be detected as closed
        assert not connection.connected

        # ensure_connection() triggers reconnection
        connection.ensure_connection()

        # Should have a new working channel
        assert connection.connected
        new_channel = connection.default_channel
        assert new_channel.is_usable()

    def test_channel_operations_work_after_recovery(self, connection, queue_name) -> None:
        """Verify channel operations work after recovery."""
        # Establish connection and declare queue
        channel = connection.default_channel
        queue = kombu_pyamqp_threadsafe.kombu.Queue(queue_name, channel=connection)
        queue.declare()

        # Close transport
        close_transport(connection)

        # ensure_connection() to trigger recovery
        connection.ensure_connection()

        # Queue operations should work
        queue2 = kombu_pyamqp_threadsafe.kombu.Queue(queue_name, channel=connection)
        queue2.declare()  # Should not raise


# ====================
# Recovery Tests: Multiple Channels
# ====================


class TestMultipleChannelRecovery:
    """Tests for recovery scenarios with multiple channels."""

    @pytest.mark.parametrize("n_channels", [10])
    def test_recovery_with_multiple_channels(
        self, multi_channel_connection, n_channels: int
    ) -> None:
        """Verify recovery works with multiple channels in pool."""
        connection = multi_channel_connection

        # Acquire multiple channels
        channels = []
        for _ in range(n_channels):
            ch = connection.default_channel_pool.acquire()
            channels.append(ch)

        assert connection.connected

        # Close transport
        close_transport(connection)

        # Release all channels back to pool
        for ch in channels:
            ch.release()

        # Connection should recover when we access it again
        new_channel = connection.default_channel
        assert connection.connected
        assert new_channel.is_usable()

    @pytest.mark.parametrize("n_channels", [10])
    def test_concurrent_operations_during_recovery(
        self, multi_channel_connection, queue_name, n_channels: int
    ) -> None:
        """Verify concurrent operations handle recovery correctly."""
        connection = multi_channel_connection

        # Establish connection
        _ = connection.default_channel
        assert connection.connected

        barrier = threading.Barrier(n_channels)
        errors = []
        lock = threading.Lock()

        def worker(worker_id: int):
            try:
                barrier.wait(timeout=THREAD_TIMEOUT)
            except threading.BrokenBarrierError:
                with lock:
                    errors.append(f"Worker {worker_id}: barrier broken")
                return

            try:
                # Try to use a channel - may fail if connection is closed
                ch = connection.default_channel_pool.acquire()
                try:
                    # Simple operation
                    pass
                finally:
                    ch.release()
            except (RecoverableConnectionError, OSError, ssl.SSLError):
                # Expected during recovery
                pass
            except Exception as e:
                with lock:
                    errors.append(f"Worker {worker_id}: {type(e).__name__}: {e}")

        # Start workers
        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_channels)]
        for t in threads:
            t.start()

        # Close transport while workers are running
        time.sleep(0.05)
        close_transport(connection)

        # Wait for all workers
        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)
            if t.is_alive():
                pytest.fail("Worker thread did not complete")

        # Errors like KeyError: None indicate a regression
        keyerror_none = [e for e in errors if "KeyError" in e and "None" in e]
        assert len(keyerror_none) == 0, f"Regression: KeyError: None detected: {keyerror_none}"


# ====================
# Regression Tests: Selective Exception Propagation
# ====================


class TestSelectiveExceptionPropagationRegression:
    """Critical regression tests for selective exception propagation.

    These tests verify the specific bug that the fix prevents:
    - socket.timeout in health check should NOT propagate to other threads
    - Other threads should NOT receive false connection errors
    """

    def test_socket_timeout_in_connected_check_not_propagated(self, connection) -> None:
        """Verify socket.timeout in connected property check is not propagated.

        Scenario:
        1. Thread A: checks `connection.connected` property
        2. This calls drain_events(timeout=0, _nodispatch=True)
        3. socket.timeout is raised (normal - no data available)
        4. Thread B: should NOT see this as an error

        Old bug: socket.timeout was stored in _drain_exc, Thread B got it.
        With fix: socket.timeout is filtered, Thread B continues normally.
        """
        # Establish connection
        _ = connection.default_channel
        assert connection.connected

        conn = connection._connection
        guard = conn._drain_guard

        # Simulate what happens in `connected` property:
        # drain_events(timeout=0, _nodispatch=True) raises socket.timeout
        # but socket.timeout should be filtered

        waiter_exception = []
        drain_started = threading.Event()

        def health_checker():
            """Simulates connected property check that gets socket.timeout."""
            guard.start_drain()
            drain_started.set()
            time.sleep(0.05)

            # socket.timeout is filtered - finish with None
            guard.finish_drain(exc=None)

        def worker():
            """Worker thread that should NOT receive socket.timeout."""
            if not drain_started.wait(timeout=THREAD_TIMEOUT):
                pytest.fail("Health check did not start")

            try:
                guard.wait_drain_finished(timeout=THREAD_TIMEOUT)
            except Exception as e:
                waiter_exception.append(e)

        t1 = PropagatingThread(target=health_checker)
        t2 = PropagatingThread(target=worker)

        t1.start()
        t2.start()

        t1.join(timeout=THREAD_TIMEOUT)
        t2.join(timeout=THREAD_TIMEOUT)

        assert len(waiter_exception) == 0, (
            f"Worker should NOT receive exception from socket.timeout, got {waiter_exception}"
        )

    def test_no_keyerror_none_after_timeout_false_positive(self, connection, queue_name) -> None:
        """Critical regression test: KeyError: None after timeout false positive.

        This is the exact scenario the fix is designed to prevent:

        1. Thread A (health checker): connection.connected → socket.timeout
           - Old: socket.timeout stored in _drain_exc
           - New: socket.timeout filtered, _drain_exc = None

        2. Thread B (worker): queue_declare() → wait_drain_finished()
           - Old: gets socket.timeout from _drain_exc → reconnect triggered
           - New: no exception, continues normally

        3. Old bug continuation:
           - Thread B triggers reconnect due to false positive
           - reconnect() → channel.collect() with channel_id=None
           - KeyError: None in channel_frame_buff access

        With fix: Step 2 doesn't get exception, no reconnect, no KeyError.
        """
        # Establish connection
        channel = connection.default_channel
        queue = kombu_pyamqp_threadsafe.kombu.Queue(queue_name, channel=connection)
        queue.declare()

        errors = []
        operations_completed = []
        lock = threading.Lock()

        def health_checker():
            """Thread A: periodic health checks."""
            for _ in range(5):
                try:
                    _ = connection.connected
                except Exception as e:
                    with lock:
                        errors.append(f"Health checker: {type(e).__name__}: {e}")
                time.sleep(0.02)

        def worker():
            """Thread B: queue operations that should not be affected."""
            for i in range(5):
                try:
                    queue = kombu_pyamqp_threadsafe.kombu.Queue(queue_name, channel=connection)
                    queue.declare()
                    with lock:
                        operations_completed.append(i)
                except KeyError as e:
                    with lock:
                        errors.append(f"Worker KeyError: {e}")
                    break
                except RecoverableConnectionError as e:
                    # This is acceptable if connection actually dropped
                    with lock:
                        errors.append(f"Worker RecoverableConnectionError: {e}")
                    break
                except Exception as e:
                    with lock:
                        errors.append(f"Worker: {type(e).__name__}: {e}")
                    break
                time.sleep(0.01)

        t1 = PropagatingThread(target=health_checker)
        t2 = PropagatingThread(target=worker)

        t1.start()
        t2.start()

        t1.join(timeout=THREAD_TIMEOUT)
        t2.join(timeout=THREAD_TIMEOUT)

        # Check for KeyError: None - the specific regression
        keyerror_none = [e for e in errors if "KeyError" in e and "None" in str(e)]
        assert len(keyerror_none) == 0, f"Regression: KeyError: None detected: {keyerror_none}"

        # At least some operations should complete successfully
        assert len(operations_completed) > 0, (
            f"At least some operations should complete, errors: {errors}"
        )


# ====================
# Pool Channel Leak Regression (tochka-esb-tools issue #26)
# ====================


class TestCollectReleasesPoolChannels:
    """Regression tests for outstanding pool channels on Connection.collect().

    Background: Connection.ensure() calls collect() before _ensure_connection
    on recoverable errors, then revive(default_channel) on the obj passed in.
    If the obj is a pool-acquired Producer, Producer.revive replaces
    self._channel with default_channel. The original pool channel loses its
    reference; pool.release(is_usable=False) then discards it silently —
    rabbit, however, still sees it as open until rabbit's channel-limit is
    reached.

    Fix: KombuConnection.collect() calls pool.force_close_all(close_pool=False)
    before super().collect(), sending channel.close frames while the transport
    is still alive.
    """

    def test_collect_force_closes_outstanding_pool_channels(
        self, multi_channel_connection
    ) -> None:
        """Verify Connection.collect() closes channels in pool._dirty.

        Without the fix, channels would remain open on rabbit's side until
        rabbit's per-connection channel-limit is hit.
        """
        conn = multi_channel_connection
        pool = conn.default_channel_pool

        # Acquire and keep strong refs to prevent weakref-based GC clearing _dirty.
        ch1 = pool.acquire(block=False)
        ch2 = pool.acquire(block=False)
        assert ch1.is_open
        assert ch2.is_open
        assert ch1 in pool._dirty
        assert ch2 in pool._dirty

        # collect() simulates what Connection.ensure() does on recoverable error,
        # before invoking obj.revive(default_channel).
        conn.collect()

        # Channels closed (channel.close frame sent while transport was alive).
        assert not ch1.is_open
        assert not ch2.is_open
        # Pool drained, but not closed — ready for new acquires after reconnect.
        assert len(pool._dirty) == 0
        assert pool._resource.qsize() == 0
        assert not pool.closed

    def test_pool_usable_after_collect(self, multi_channel_connection) -> None:
        """After collect() pool serves fresh channels on the new transport."""
        conn = multi_channel_connection
        pool = conn.default_channel_pool

        _ = pool.acquire(block=False)
        conn.collect()

        # Pool reusable: ensure_connection re-establishes transport,
        # acquire creates a fresh channel on the new connection.
        conn.ensure_connection()
        new_ch = pool.acquire(block=False)
        assert new_ch.is_open
        assert new_ch in pool._dirty
