"""Comprehensive unit tests for DrainGuard synchronization primitive.

DrainGuard coordinates multi-threaded access to drain_events() ensuring:
- Mutual exclusion (only one drain at a time)
- Deadlock prevention (thread cannot wait for itself)
- Proper notification of waiting threads
- Thread ownership validation

Test Categories:
1. Single-Threaded Basic Behavior (6 tests)
2. Multi-Threaded Race Conditions (3 tests)
3. Edge Cases & Error Conditions (4 tests)
4. Integration Patterns (1 test)

Total: 14 test scenarios covering 100% of DrainGuard functionality.
"""

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest

from kombu_pyamqp_threadsafe import DrainGuard
from testing import PropagatingThread

# ====================
# Test Constants
# ====================

# Timing tolerances (seconds)
IMMEDIATE_RETURN_THRESHOLD = 0.1  # Max time for immediate/non-blocking operations
POLL_RETURN_THRESHOLD = 0.05  # Max time for polling (timeout=0) operations
NOTIFICATION_TIMEOUT = 0.3  # Max time for threads to wake after notification

# Test configuration
SEQUENTIAL_HANDOFF_THREADS = 3  # Number of threads for sequential handoff test

# ====================
# Helper Functions (Reusable Utilities)
# ====================


def collect_thread_results(
    threads: list[PropagatingThread], timeout: float = 1.0
) -> list:
    """Join threads and collect return values.

    Args:
        threads: List of PropagatingThread instances
        timeout: Timeout per thread join (seconds)

    Returns:
        List of return values from threads (in order)

    Raises:
        pytest.fail if any thread doesn't complete within timeout
    """
    results = []
    for idx, thread in enumerate(threads):
        thread.join(timeout=timeout)
        if thread.is_alive():
            pytest.fail(
                f"Test design error: thread {idx} did not complete in {timeout}s"
            )
        results.append(thread.ret)
    return results


def measure_elapsed_time(func: Callable, *args, **kwargs) -> tuple[float, Any]:
    """Measure function execution time.

    Args:
        func: Callable to measure
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Tuple of (elapsed_seconds, return_value)
    """
    start = time.monotonic()
    result = func(*args, **kwargs)
    elapsed = time.monotonic() - start
    return elapsed, result


def assert_elapsed_time_within(
    elapsed: float,
    expected: float,
    tolerance: float = 0.1,
    context: str = "",
) -> None:
    """Assert elapsed time within tolerance range.

    Args:
        elapsed: Actual elapsed time (seconds)
        expected: Expected time (seconds)
        tolerance: Acceptable deviation (seconds)
        context: Description for assertion message

    Raises:
        AssertionError if outside tolerance range
    """
    lower = expected - tolerance
    upper = expected + tolerance
    ctx = f" ({context})" if context else ""
    assert lower <= elapsed <= upper, (
        f"Elapsed time {elapsed:.3f}s outside expected range "
        f"[{lower:.3f}s, {upper:.3f}s]{ctx}"
    )


# ====================
# Fixtures
# ====================


@pytest.fixture
def guard() -> DrainGuard:
    """Provide fresh DrainGuard instance for each test."""
    return DrainGuard()


@pytest.fixture(scope="session")
def thread_timeout() -> float:
    """Default timeout for thread operations (seconds)."""
    return 2.0


# ====================
# Category 1: Single-Threaded Basic Behavior (6 tests)
# ====================


class TestSingleThreadedBehavior:
    """Tests for basic DrainGuard operations in single-threaded context."""

    def test_initial_state_is_inactive(self, guard: DrainGuard) -> None:
        """Verify clean initial state after construction.

        A newly created DrainGuard should be in inactive state:
        - is_drain_active() returns False
        - Internal state _drain_is_active_by is None
        """
        assert guard.is_drain_active() is False
        assert guard._drain_is_active_by is None

    def test_start_drain_first_time_succeeds(self, guard: DrainGuard) -> None:
        """Verify first drain acquisition succeeds.

        When start_drain() is called for the first time:
        - Should return True (acquisition successful)
        - is_drain_active() should return True
        - Internal state should track current thread ID
        """
        result = guard.start_drain()

        assert result is True
        assert guard.is_drain_active() is True
        assert guard._drain_is_active_by == threading.get_ident()

        # Cleanup
        guard.finish_drain()

    def test_finish_drain_normal_flow_cleans_state(self, guard: DrainGuard) -> None:
        """Verify proper drain cleanup.

        After successfully finishing a drain:
        - is_drain_active() should return False
        - Internal state _drain_is_active_by should be None
        - Lock should be released
        """
        guard.start_drain()
        guard.finish_drain()

        assert guard.is_drain_active() is False
        assert guard._drain_is_active_by is None

        # Verify lock is released by trying to acquire again
        result = guard.start_drain()
        assert result is True
        guard.finish_drain()

    def test_finish_drain_without_start_raises_assertion(
        self, guard: DrainGuard
    ) -> None:
        """Verify assertion fires when finishing non-existent drain.

        Calling finish_drain() without prior start_drain() should raise
        AssertionError with message "Drain must be started".
        """
        with pytest.raises(AssertionError, match="Drain must be started"):
            guard.finish_drain()

    def test_wait_when_not_active_returns_immediately(self, guard: DrainGuard) -> None:
        """Verify wait returns immediately when no drain active.

        When no drain is active, wait_drain_finished() should:
        - Return immediately without blocking
        - Complete in < IMMEDIATE_RETURN_THRESHOLD seconds
        """
        elapsed, _ = measure_elapsed_time(guard.wait_drain_finished, timeout=1.0)

        assert (
            elapsed < IMMEDIATE_RETURN_THRESHOLD
        ), f"Expected immediate return, took {elapsed:.3f}s"

    def test_wait_self_deadlock_detection_raises_assertion(
        self, guard: DrainGuard
    ) -> None:
        """Verify assertion prevents thread from waiting for itself.

        When a thread that started drain tries to wait for itself:
        - Should raise AssertionError
        - Error message should indicate deadlock detection
        """
        guard.start_drain()

        with pytest.raises(
            AssertionError, match="You can not wait your own; deadlock detected"
        ):
            guard.wait_drain_finished()

        # Cleanup
        guard.finish_drain()


# ====================
# Category 2: Multi-Threaded Race Conditions (3 tests)
# ====================


class TestMultiThreadedRaceConditions:
    """Tests for concurrent access patterns and race condition handling."""

    def test_concurrent_start_drain_stress_test_multiple_threads(
        self, thread_timeout: float
    ) -> None:
        """Verify mutual exclusion under high contention.

        Run 100 iterations with 10 threads competing for drain:
        - In every iteration, exactly one thread should win
        - All other threads should fail
        - No state corruption should occur
        """
        n_threads = 10
        n_iterations = 100

        for iteration in range(n_iterations):
            guard = DrainGuard()
            start_barrier = threading.Barrier(n_threads)
            finish_barrier = threading.Barrier(n_threads)
            results: list[tuple[int, bool]] = []

            def worker(
                _guard=guard,
                _start_barrier=start_barrier,
                _finish_barrier=finish_barrier,
                _results=results,
                _iteration=iteration,
            ):
                try:
                    # Synchronize start - all threads enter start_drain() simultaneously
                    _start_barrier.wait(timeout=thread_timeout)
                except threading.BrokenBarrierError:
                    pytest.fail(f"Iteration {_iteration}: start barrier broken")

                result = _guard.start_drain()
                _results.append((threading.get_ident(), result))

                try:
                    # Wait for all threads to complete start_drain() attempt
                    # This ensures all losers tried before winner releases
                    _finish_barrier.wait(timeout=thread_timeout)
                except threading.BrokenBarrierError:
                    pytest.fail(f"Iteration {_iteration}: finish barrier broken")

                if result:
                    # Winner releases after all attempted acquisition
                    _guard.finish_drain()
                return result

            threads = [PropagatingThread(target=worker) for _ in range(n_threads)]
            for t in threads:
                t.start()

            collect_thread_results(threads, timeout=thread_timeout)

            # Verify exactly one True in this iteration
            true_count = sum(1 for _, r in results if r)
            false_count = sum(1 for _, r in results if not r)

            assert (
                true_count == 1
            ), f"Iteration {iteration}: expected exactly 1 winner, got {true_count}"
            assert (
                false_count == n_threads - 1
            ), f"Iteration {iteration}: expected {n_threads - 1} losers, got {false_count}"

            # Drain should be inactive after iteration
            assert guard.is_drain_active() is False

    def test_wait_until_finished_blocks_until_drain_completes(
        self, guard: DrainGuard, thread_timeout: float
    ) -> None:
        """Verify waiting thread unblocks when drain finishes.

        Setup:
        - Thread A: starts drain, holds for 0.2s, finishes
        - Thread B: waits for drain to finish

        Expected:
        - Thread B blocks until A finishes (~0.2s)
        - Thread B verifies drain is inactive after wait
        """
        drain_started = threading.Event()
        drain_finished = threading.Event()
        wait_completed = threading.Event()
        elapsed_time = []

        def drainer():
            guard.start_drain()
            drain_started.set()

            # Hold drain for 0.2s
            if not drain_finished.wait(timeout=thread_timeout):
                pytest.fail("Test design error: drain_finished event not set")

            guard.finish_drain()

        def waiter():
            # Wait for drain to actually start
            if not drain_started.wait(timeout=thread_timeout):
                pytest.fail("Test design error: drain did not start")

            start_time = time.monotonic()
            guard.wait_drain_finished(timeout=thread_timeout)
            elapsed = time.monotonic() - start_time
            elapsed_time.append(elapsed)

            # Verify drain is now inactive
            assert guard.is_drain_active() is False
            wait_completed.set()

        t1 = PropagatingThread(target=drainer)
        t2 = PropagatingThread(target=waiter)

        t1.start()
        t2.start()

        # Signal drainer to finish after 0.2s
        time.sleep(0.2)
        drain_finished.set()

        t1.join(timeout=thread_timeout)
        t2.join(timeout=thread_timeout)

        if not wait_completed.is_set():
            pytest.fail("Test design error: waiter did not complete")

        # Verify waiter blocked for ~0.2s
        assert_elapsed_time_within(
            elapsed_time[0],
            expected=0.2,
            tolerance=0.1,
            context="waiter should block until drainer finishes",
        )

    def test_wait_timeout_behavior_returns_after_timeout(
        self, guard: DrainGuard, thread_timeout: float
    ) -> None:
        """Verify timeout works correctly when drain doesn't finish.

        Setup:
        - Thread A: starts drain and holds it for 5s
        - Thread B: waits with timeout=0.5s

        Expected:
        - Thread B returns after ~0.5s without raising exception
        - Drain is still active (A still holding)

        Important: wait_drain_finished(timeout=...) does NOT raise exception on timeout.
        This differs from drain_events(timeout=...) which expects socket.timeout.
        Reason: socket.timeout means "socket is alive, but no data" - concrete socket state.
        But wait_drain_finished() doesn't know socket state (only waits for another thread),
        so raising TimeoutError would mislead upper layers about actual socket condition.
        """
        ready = threading.Event()
        elapsed_time = []
        cleanup_done = threading.Event()

        def drainer():
            guard.start_drain()
            ready.set()

            # Wait for cleanup signal or timeout
            cleanup_done.wait(timeout=5.0)
            guard.finish_drain()

        def waiter():
            if not ready.wait(timeout=thread_timeout):
                pytest.fail("Test design error: drain not started")

            start_time = time.monotonic()
            guard.wait_drain_finished(timeout=0.5)
            elapsed = time.monotonic() - start_time
            elapsed_time.append(elapsed)

            # Drain should still be active (A still holding)
            assert guard.is_drain_active() is True

        t1 = PropagatingThread(target=drainer)
        t2 = PropagatingThread(target=waiter)

        t1.start()
        t2.start()

        t2.join(timeout=thread_timeout)
        if t2.is_alive():
            pytest.fail("Test design error: waiter did not complete")

        # Signal cleanup
        cleanup_done.set()
        t1.join(timeout=thread_timeout)

        # Verify waiter returned after ~0.5s timeout
        assert_elapsed_time_within(
            elapsed_time[0],
            expected=0.5,
            tolerance=0.1,
            context="waiter should return after timeout",
        )


# ====================
# Category 3: Edge Cases & Error Conditions (4 tests)
# ====================


class TestEdgeCasesAndErrors:
    """Tests for boundary conditions and error scenarios."""

    def test_finish_drain_from_wrong_thread_raises_assertion(
        self, guard: DrainGuard, thread_timeout: float
    ) -> None:
        """Verify assertion prevents cross-thread finish.

        Setup:
        - Thread A: starts drain
        - Thread B: tries to finish it

        Expected: AssertionError with message about wrong thread.
        """
        drain_started = threading.Event()
        error_caught = threading.Event()
        error_message = []

        def thread_a():
            guard.start_drain()
            drain_started.set()

            # Wait for thread B to try (and fail) to finish
            time.sleep(0.2)
            guard.finish_drain()

        def thread_b():
            if not drain_started.wait(timeout=thread_timeout):
                pytest.fail("Test design error: drain not started")

            try:
                guard.finish_drain()
                pytest.fail("Expected AssertionError but none was raised")
            except AssertionError as e:
                error_message.append(str(e))
                error_caught.set()

        t1 = PropagatingThread(target=thread_a)
        t2 = PropagatingThread(target=thread_b)

        t1.start()
        t2.start()

        if not error_caught.wait(timeout=thread_timeout):
            pytest.fail("Test design error: thread B did not catch error")

        t1.join(timeout=thread_timeout)
        t2.join(timeout=thread_timeout)

        # Verify correct error message
        assert len(error_message) == 1
        assert "You can not finish drain started by other thread" in error_message[0]

    def test_multiple_finish_calls_raises_assertion(self, guard: DrainGuard) -> None:
        """Verify assertion fires on second finish.

        Calling finish_drain() twice without intervening start_drain()
        should raise AssertionError "Drain must be started".
        """
        guard.start_drain()
        guard.finish_drain()

        # Second finish should fail
        with pytest.raises(AssertionError, match="Drain must be started"):
            guard.finish_drain()

    def test_wait_with_zero_timeout_polls_immediately(
        self, guard: DrainGuard, thread_timeout: float
    ) -> None:
        """Verify zero timeout behaves correctly (poll behavior).

        When drain is active and wait_drain_finished(timeout=0) is called:
        - Should return immediately (< 0.05s)
        - Drain should still be active
        """
        ready = threading.Event()
        elapsed_time = []
        cleanup_done = threading.Event()

        def drainer():
            guard.start_drain()
            ready.set()
            cleanup_done.wait(timeout=thread_timeout)
            guard.finish_drain()

        def waiter():
            if not ready.wait(timeout=thread_timeout):
                pytest.fail("Test design error: drain not started")

            start_time = time.monotonic()
            guard.wait_drain_finished(timeout=0)
            elapsed = time.monotonic() - start_time
            elapsed_time.append(elapsed)

            # Drain should still be active
            assert guard.is_drain_active() is True

        t1 = PropagatingThread(target=drainer)
        t2 = PropagatingThread(target=waiter)

        t1.start()
        t2.start()

        t2.join(timeout=thread_timeout)
        if t2.is_alive():
            pytest.fail("Test design error: waiter did not complete")

        # Cleanup
        cleanup_done.set()
        t1.join(timeout=thread_timeout)

        # Verify immediate return (polling behavior)
        assert (
            elapsed_time[0] < POLL_RETURN_THRESHOLD
        ), f"Expected immediate return, took {elapsed_time[0]:.3f}s"

    def test_reentrancy_check_rlock_behavior(self, guard: DrainGuard) -> None:
        """Verify RLock allows reentrancy but assertion prevents double-drain.

        DrainGuard uses RLock which DOES allow reentrancy. However, the
        assertion on line 211 prevents the same thread from starting drain
        twice, even though the lock acquisition succeeds.

        This test verifies the fail-fast assertion catches reentrancy attempts.

        Implementation Detail:
        - acquire(blocking=False) from owning thread succeeds (RLock reentrancy)
        - Then assertion fires: "assert self._drain_is_active_by is None"
        - Result: AssertionError with clear fail-fast message
        """
        # First acquisition succeeds
        first_result = guard.start_drain()
        assert first_result is True
        assert guard.is_drain_active() is True
        assert guard._drain_is_active_by == threading.get_ident()

        # Second acquisition: RLock allows it, but assertion catches it
        with pytest.raises(AssertionError):
            guard.start_drain()

        # State should be consistent (still active by same thread)
        assert guard.is_drain_active() is True
        assert guard._drain_is_active_by == threading.get_ident()

        # Cleanup: single finish_drain() releases (not double release!)
        guard.finish_drain()
        assert guard.is_drain_active() is False

        # After finish, can acquire again (fresh start)
        third_result = guard.start_drain()
        assert third_result is True
        guard.finish_drain()


# ====================
# Category 4: Integration Patterns (1 test)
# ====================


class TestIntegrationPatterns:
    """Tests for real-world usage patterns."""

    def test_typical_usage_pattern_from_drain_events(
        self, guard: DrainGuard, thread_timeout: float
    ) -> None:
        """Verify the pattern used in ThreadSafeConnection.drain_events().

        Pattern:
        ```python
        started = guard.start_drain()
        if not started:
            guard.wait_drain_finished()
        else:
            try:
                # do drain work
                pass
            finally:
                guard.finish_drain()
        ```

        Simulate this pattern with multiple threads concurrently.
        Expected: No exceptions, no hangs, all threads complete.
        """
        n_threads = 5
        barrier = threading.Barrier(n_threads)
        completed = []
        work_done = []

        def simulate_drain_events(thread_id: int):
            """Simulate drain_events pattern."""
            try:
                barrier.wait(timeout=thread_timeout)
            except threading.BrokenBarrierError:
                pytest.fail(f"Test design error: barrier broken (thread {thread_id})")

            # Standard pattern from ThreadSafeConnection
            started = guard.start_drain()
            if not started:
                # Another thread is draining, wait for it
                guard.wait_drain_finished(timeout=thread_timeout)
                completed.append((thread_id, "waited"))
            else:
                try:
                    # Simulate drain work
                    time.sleep(0.05)
                    work_done.append(thread_id)
                    completed.append((thread_id, "drained"))
                finally:
                    guard.finish_drain()

        threads = [
            PropagatingThread(target=simulate_drain_events, args=(i,))
            for i in range(n_threads)
        ]

        for t in threads:
            t.start()

        collect_thread_results(threads, timeout=thread_timeout)

        # Verify all threads completed
        assert len(completed) == n_threads

        # Verify exactly one thread did drain work
        assert len(work_done) == 1, f"Expected 1 drainer, got {len(work_done)}"

        # Verify the rest waited
        drained_count = sum(1 for _, action in completed if action == "drained")
        waited_count = sum(1 for _, action in completed if action == "waited")

        assert drained_count == 1, f"Expected 1 drainer, got {drained_count}"
        assert (
            waited_count == n_threads - 1
        ), f"Expected {n_threads - 1} waiters, got {waited_count}"

        # Final state should be inactive
        assert guard.is_drain_active() is False
