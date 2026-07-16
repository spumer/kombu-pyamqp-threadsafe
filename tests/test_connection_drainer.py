"""Unit tests for ConnectionDrainer lifecycle and dedicated_drainer option plumbing.

No RabbitMQ needed here — a fake connection/transport stands in for the
real socket. Real-broker thread-count assertions live in
tests/test_drainer_integration.py.
"""

import contextlib
import gc
import os
import selectors
import socket
import struct
import threading
import time

import pytest
from amqp import ConnectionForced, RecoverableConnectionError

import kombu_pyamqp_threadsafe
from kombu_pyamqp_threadsafe.drainer import (
    DEDICATED_DRAINER_OPTION,
    ConnectionClosedIntentionally,
    ConnectionDrainer,
)
from testing import PropagatingThread


def _count_open_fds() -> int:
    """Best-effort count of open file descriptors for this process."""
    for path in ("/proc/self/fd", "/dev/fd"):
        if os.path.isdir(path):
            return len(os.listdir(path))
    pytest.skip("no fd directory available on this platform")
    return 0  # unreachable; keeps type checkers happy


class FakeTransport:
    """A transport backed by a real socketpair so selectors can poll it.

    `sock` is the drainer's read end; it stays quiet (never readable) unless a
    test writes to `_peer`, so the loop just ticks. `close()` tears both ends
    down and reports `connected = False`, mirroring a dead transport.
    """

    def __init__(self, connected: bool = True):
        self.connected = connected
        self.sock, self._peer = socket.socketpair()
        self.sock.setblocking(False)
        # amqp transports expose a raw read buffer the drainer inspects to tell
        # a buffered frame from a truly-dry socket; empty by default here.
        self._read_buffer = b""

    def close(self) -> None:
        self.connected = False
        with contextlib.suppress(OSError):
            self.sock.close()
        with contextlib.suppress(OSError):
            self._peer.close()

    @contextlib.contextmanager
    def having_timeout(self, timeout):
        """Mirror amqp transport's scoped-timeout mechanism on the real
        socketpair sock, so _tick_heartbeat's heartbeat-write bound can be
        exercised against the fake exactly as against a live transport.
        """
        if timeout is None:
            yield self.sock
            return
        prev = self.sock.gettimeout()
        if prev != timeout:
            self.sock.settimeout(timeout)
        try:
            yield self.sock
        finally:
            if timeout != prev:
                self.sock.settimeout(prev)


class FakeConnection:
    """Stands in for ThreadSafeConnection: the drainer reads `_transport`,
    calls `mark_for_teardown()` on fatal errors, and classifies socket errors
    through `connection_errors`.

    `heartbeat = 0` (negotiated-off) by default: every existing test in this
    module exercises the loop with heartbeat ticking disabled, matching
    "option off -> byte-for-byte identical behavior". Tests that care about
    the ticker opt in explicitly via HeartbeatFakeConnection below.
    """

    def __init__(self, transport: "FakeTransport | None" = None):
        self._transport = transport if transport is not None else FakeTransport()
        self.marked_for_teardown = False
        self.connection_errors = (OSError,)
        self.heartbeat = 0
        self._transport_lock = threading.RLock()

    def mark_for_teardown(self) -> None:
        self.marked_for_teardown = True


@pytest.fixture
def fake_conn() -> FakeConnection:
    """A connected fake connection, ready for a drainer to watch."""
    return FakeConnection()


@pytest.fixture
def drainer(fake_conn) -> ConnectionDrainer:
    """A drainer with a short tick, so timing-sensitive tests stay fast."""
    d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
    yield d
    # Best-effort cleanup: a leftover running thread from a failed
    # assertion would otherwise leak into later tests.
    with contextlib.suppress(RuntimeError):
        d.stop(join_timeout=1.0)


# ====================
# Option plumbing
# ====================


class TestOptionPlumbing:
    def test_constant_value(self):
        assert DEDICATED_DRAINER_OPTION == "dedicated_drainer"

    def test_default_disables_drainer(self):
        conn = kombu_pyamqp_threadsafe.ThreadSafeConnection()
        assert conn._dedicated_drainer_enabled is False
        assert conn._drainer is None

    def test_option_true_enables_drainer(self):
        conn = kombu_pyamqp_threadsafe.ThreadSafeConnection(dedicated_drainer=True)
        assert conn._dedicated_drainer_enabled is True
        assert isinstance(conn._drainer, ConnectionDrainer)

    def test_option_survives_from_kombu_connection(self):
        original = kombu_pyamqp_threadsafe.KombuConnection(
            "amqp://guest:guest@127.0.0.1:5672/",
            transport_options={"dedicated_drainer": True},
        )
        cloned = kombu_pyamqp_threadsafe.KombuConnection.from_kombu_connection(original)
        assert cloned.transport_options.get("dedicated_drainer") is True


# ====================
# start()
# ====================


class TestStart:
    def test_start_spawns_a_named_daemon_thread(self, drainer):
        drainer.start()

        assert drainer.is_running is True
        thread = drainer._thread
        assert thread is not None
        assert thread.daemon is True
        assert thread.name.startswith("kombu-pyamqp-drainer-")

    def test_start_is_idempotent(self, drainer):
        drainer.start()
        first_thread = drainer._thread

        drainer.start()

        assert drainer._thread is first_thread

    def test_concurrent_start_spawns_exactly_one_worker(self, fake_conn):
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        run_calls: list[int] = []
        original_run = d._run

        def counting_run():
            run_calls.append(1)
            original_run()

        d._run = counting_run  # spy: instance attribute shadows the bound method

        try:
            n_threads = 8
            barrier = threading.Barrier(n_threads)

            def worker():
                barrier.wait(timeout=2.0)
                d.start()

            threads = [PropagatingThread(target=worker) for _ in range(n_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=2.0)
                if t.is_alive():
                    pytest.fail("Test design error: worker thread did not complete")

            # Give the one spawned thread a moment to enter _run.
            deadline = time.monotonic() + 1.0
            while not run_calls and time.monotonic() < deadline:
                time.sleep(0.01)

            assert len(run_calls) == 1, (
                f"expected exactly one drainer thread to start, got {len(run_calls)}"
            )
        finally:
            d.stop(join_timeout=1.0)

    def test_start_after_real_stop_raises_runtime_error(self, drainer):
        """One ConnectionDrainer per ThreadSafeConnection, never reused across a reconnect.

        start() after a real stop() fails fast rather than silently
        resurrecting closed self-pipe fds.
        """
        drainer.start()
        drainer.stop(join_timeout=1.0)

        with pytest.raises(RuntimeError):
            drainer.start()


# ====================
# stop()
# ====================


class TestStop:
    def test_stop_without_start_is_a_noop(self, drainer):
        drainer.stop(join_timeout=1.0)

        assert drainer.is_running is False

    def test_stop_joins_running_thread(self, drainer):
        drainer.start()
        assert drainer.is_running is True

        drainer.stop(join_timeout=1.0)

        assert drainer.is_running is False
        assert drainer._thread is None

    def test_double_stop_is_safe(self, drainer):
        drainer.start()

        drainer.stop(join_timeout=1.0)
        drainer.stop(join_timeout=1.0)  # must not raise, must not hang

        assert drainer.is_running is False

    def test_stop_wakes_the_loop_instantly_regardless_of_tick(self, fake_conn):
        # Tick is deliberately long: an instant stop proves the self-pipe
        # wakes select(), not the tick timeout expiring on its own.
        d = ConnectionDrainer(fake_conn, poll_tick_s=5.0)
        d.start()

        started = time.monotonic()
        d.stop(join_timeout=2.0)
        elapsed = time.monotonic() - started

        assert elapsed < 1.0, f"stop() took {elapsed:.2f}s — self-pipe wakeup not working"

    def test_stop_from_own_thread_raises_runtime_error(self, fake_conn):
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        errors: list[Exception] = []

        def self_stopper():
            try:
                d.stop(join_timeout=1.0)
            except RuntimeError as exc:
                errors.append(exc)

        thread = threading.Thread(target=self_stopper)
        d._thread = thread  # pretend this thread IS the drainer's own thread
        thread.start()
        thread.join(timeout=2.0)
        if thread.is_alive():
            pytest.fail("Test design error: self_stopper did not complete")

        assert len(errors) == 1
        assert "own drainer thread" in str(errors[0])

        # The manual wiring above never went through real start(), so
        # fixture teardown must not try to join it via the guard it just
        # proved works.
        d._thread = None


# ====================
# pid guard (fork safety)
# ====================


class TestPidGuard:
    def test_is_running_false_when_pid_does_not_match(self, drainer):
        drainer.start()
        assert drainer.is_running is True

        real_pid = drainer._pid
        # Simulate the child side of a fork(): the Thread object still looks
        # alive, but no real OS thread exists for it in this "process".
        drainer._pid = real_pid + 1

        assert drainer.is_running is False

        drainer._pid = real_pid  # restore so the fixture's stop() can join it


# ====================
# Phase-1 loop body: wakeup poll + transport-liveness self-termination
# ====================


class TestSelfTerminationOnDeadTransport:
    def test_run_exits_when_transport_is_none(self, fake_conn):
        fake_conn._transport = None
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)

        d.start()
        d._thread.join(timeout=1.0)

        assert d.is_running is False
        d.stop(join_timeout=1.0)  # must be a safe no-op; thread already exited

    def test_run_exits_when_transport_reports_not_connected(self, fake_conn):
        fake_conn._transport.connected = False
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)

        d.start()
        d._thread.join(timeout=1.0)

        assert d.is_running is False
        d.stop(join_timeout=1.0)

    def test_run_keeps_going_while_transport_stays_connected(self, drainer):
        drainer.start()

        time.sleep(0.2)  # several ticks worth

        assert drainer.is_running is True


# ====================
# Activity signalling (wait_activity / _notify_activity / generations)
# ====================


class TestWaitActivity:
    """The generation-counter Condition that app threads block on while the
    drainer pumps frames. No thread is started here — the primitives are
    driven directly, so timing is deterministic.
    """

    def test_generation_starts_at_zero(self, drainer):
        assert drainer.generation == 0

    def test_notify_activity_bumps_generation(self, drainer):
        drainer._notify_activity()
        assert drainer.generation == 1
        drainer._notify_activity()
        assert drainer.generation == 2

    def test_wait_returns_when_generation_already_advanced(self, drainer):
        # Frame pumped before the waiter captured its generation: waiting from
        # an older generation must return at once, never block (lost wakeup).
        since = drainer.generation
        drainer._notify_activity()

        started = time.monotonic()
        drainer.wait_activity(timeout=5.0, since_generation=since)
        assert time.monotonic() - started < 0.5

    def test_wait_wakes_on_concurrent_notify(self, drainer):
        since = drainer.generation

        def pump():
            time.sleep(0.05)
            drainer._notify_activity()

        t = threading.Thread(target=pump)
        t.start()
        started = time.monotonic()
        drainer.wait_activity(timeout=5.0, since_generation=since)
        elapsed = time.monotonic() - started
        t.join(timeout=1.0)

        assert 0.03 < elapsed < 1.0

    def test_wait_timeout_raises_socket_timeout(self, drainer):
        since = drainer.generation
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            drainer.wait_activity(timeout=0.3, since_generation=since)
        elapsed = time.monotonic() - started
        assert 0.25 < elapsed < 1.0

    def test_wait_zero_timeout_is_immediate(self, drainer):
        since = drainer.generation
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            drainer.wait_activity(timeout=0, since_generation=since)
        assert time.monotonic() - started < 0.1

    def test_wait_raises_stored_exc_when_no_new_activity(self, drainer):
        boom = OSError("broker dropped")
        drainer._fail(boom)

        since = drainer.generation
        with pytest.raises(OSError) as exc_info:
            drainer.wait_activity(timeout=5.0, since_generation=since)
        assert exc_info.value is boom

    def test_wait_reraises_same_exc_on_repeat(self, drainer):
        # README Rule 2: the fatal error surfaces on every drain, not once.
        boom = OSError("broker dropped")
        drainer._fail(boom)

        for _ in range(3):
            with pytest.raises(OSError) as exc_info:
                drainer.wait_activity(timeout=1.0, since_generation=drainer.generation)
            assert exc_info.value is boom

    def test_wait_prefers_buffered_activity_over_stored_exc(self, drainer):
        # A graceful broker Close arrives as a channel-0 frame (generation
        # bumped) AND the follow-up EOF fails the drainer (_exc set). The
        # waiter must return so the app thread dispatches the buffered Close
        # (RecoverableConnectionError) instead of the raw EOF OSError.
        since = drainer.generation
        drainer._notify_activity()  # frame buffered
        drainer._fail(OSError("eof after close"))  # then fatal

        # Returns (does not raise): buffered activity wins.
        drainer.wait_activity(timeout=5.0, since_generation=since)


class TestDrainUntilDry:
    """The drain loop's frame-pumping logic, driven by a scripted
    _drain_into_buffers so no real socket/broker is involved.
    """

    class ScriptedConnection(FakeConnection):
        """_drain_into_buffers replays a script of outcomes.

        Each entry is either True (a method was read), False (contended), or an
        Exception instance (raise it). Dryness is driven separately through
        _has_input (see _make_drainer): the loop only calls _drain_into_buffers
        while there is input, so the script never needs a "dry" sentinel.
        """

        def __init__(self, script):
            super().__init__()
            self._script = list(script)
            self.read_timeouts: list[float] = []

        def _drain_into_buffers(self, timeout):
            self.read_timeouts.append(timeout)
            item = self._script.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

    def _make_drainer(self, conn):
        """Drainer whose _has_input reports input while the script is non-empty,
        then reports dry — so _drain_until_dry consumes exactly the script.
        """
        d = ConnectionDrainer(conn, poll_tick_s=0.05)
        d._has_input = lambda sel, transport: bool(conn._script)  # type: ignore[method-assign]
        return d

    def test_pumps_every_method_then_stops_at_dry(self):
        conn = self.ScriptedConnection([True, True, True])
        d = self._make_drainer(conn)

        keep_running = d._drain_until_dry(sel=None)

        assert keep_running is True
        assert d.generation == 3  # one notify per read method
        assert d._exc is None

    def test_reads_use_a_nonzero_timeout_not_busy_spin(self):
        # The core of the busy-spin fix: the drainer must never read at
        # timeout=0 (which spins amqp _read on a fragmented body). Every read
        # goes through the small blocking timeout.
        conn = self.ScriptedConnection([True, True])
        d = self._make_drainer(conn)

        d._drain_until_dry(sel=None)

        assert conn.read_timeouts, "expected at least one read"
        assert all(t > 0 for t in conn.read_timeouts), (
            f"reads must use a non-zero timeout, got {conn.read_timeouts}"
        )

    def test_contended_step_yields_without_failing(self):
        # start_drain lost the race: _drain_into_buffers returns False. The
        # drainer keeps running and retries on the next select().
        conn = self.ScriptedConnection([False])
        d = self._make_drainer(conn)

        keep_running = d._drain_until_dry(sel=None)

        assert keep_running is True
        assert d.generation == 0

    def test_mid_frame_stall_yields_without_failing(self):
        # A read that times out mid-frame (peer stalled past read_timeout_s) is
        # NOT a failure: the partial is preserved by the transport, so the
        # drainer yields the lock and keeps running.
        conn = self.ScriptedConnection([True, TimeoutError()])
        d = self._make_drainer(conn)

        keep_running = d._drain_until_dry(sel=None)

        assert keep_running is True
        assert d._exc is None
        assert d.generation == 1  # the one good read before the stall

    def test_connection_error_triggers_fail_and_stops(self):
        boom = OSError("broker dropped")
        conn = self.ScriptedConnection([True, boom])
        d = self._make_drainer(conn)

        keep_running = d._drain_until_dry(sel=None)

        assert keep_running is False
        assert d._exc is boom
        assert conn.marked_for_teardown is True
        assert d.generation == 1  # the one good read before the failure


class TestShouldOwnReads:
    """Routing gate: while True, app-thread drain_events defers to the drainer."""

    def test_false_before_start(self, drainer):
        assert drainer.should_own_reads is False

    def test_true_while_running(self, drainer):
        drainer.start()
        assert drainer.should_own_reads is True

    def test_true_after_fail_even_though_thread_dead(self, drainer):
        # After a fatal _fail the thread exits, but reads must keep routing to
        # the drainer so the stored error surfaces (Rule 2), not to the legacy
        # socket-reading path.
        drainer._fail(OSError("boom"))
        assert drainer.is_running is False
        assert drainer.should_own_reads is True

    def test_true_after_clean_self_termination(self, fake_conn):
        # Transport dead at loop entry: the drainer self-terminates with no
        # _exc. It must STAY the read owner (not hand back to the legacy path):
        # a thread already parked in wait_activity has to be released with a
        # recoverable error, and new callers must route to the drainer branch
        # to get that same terminal error rather than reading a torn-down
        # socket. The terminal flag keeps should_own_reads True.
        fake_conn._transport = None
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        d.start()
        d._thread.join(timeout=1.0)

        assert d.is_running is False
        assert d.should_own_reads is True
        d.stop(join_timeout=1.0)


class TestFail:
    """_fail records the error, marks the connection, and wakes every waiter."""

    def test_fail_stores_exc_and_marks_teardown(self, fake_conn):
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        boom = OSError("broker dropped")

        d._fail(boom)

        assert d._exc is boom
        assert fake_conn.marked_for_teardown is True

    def test_fail_keeps_first_exc_on_repeat(self, fake_conn):
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        first = OSError("first")
        second = OSError("second")

        d._fail(first)
        d._fail(second)

        assert d._exc is first

    def test_fail_wakes_a_blocked_waiter(self, drainer):
        since = drainer.generation
        boom = OSError("broker dropped")
        got: list[Exception] = []

        def waiter():
            try:
                drainer.wait_activity(timeout=5.0, since_generation=since)
            except Exception as exc:
                got.append(exc)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)  # let it block
        drainer._fail(boom)
        t.join(timeout=1.0)

        assert got == [boom]


# ====================
# Terminal wakeup — every _run exit releases waiters
# ====================


class _FdlessConnection:
    """Minimal conn stand-in with no socketpair, for fd-accounting tests."""

    _transport = None


class TestTerminalWakeup:
    """A thread parked in wait_activity(timeout=None) must wake on EVERY drainer
    exit path, not only on _fail — otherwise it hangs forever (README Rule 2).
    """

    def _park_waiter(self, drainer, since):
        outcome: dict = {}

        def waiter():
            try:
                drainer.wait_activity(timeout=None, since_generation=since)
                outcome["result"] = "returned"
            except BaseException as exc:
                outcome["error"] = exc

        # daemon: if the fix regresses, the parked thread must not wedge exit.
        t = threading.Thread(target=waiter, daemon=True)
        t.start()
        time.sleep(0.1)  # let it park in wait_activity
        return t, outcome

    def test_stop_wakes_blocked_waiter_with_intentional_close_error(self, drainer):
        # stop() means the application closed the connection intentionally, so
        # the waiter gets a NON-recoverable ConnectionClosedIntentionally — not
        # a recoverable error that would make ensure() reconnect and resurrect
        # a connection the app deliberately tore down (owner decision).
        drainer.start()
        t, outcome = self._park_waiter(drainer, drainer.generation)

        drainer.stop(join_timeout=1.0)
        t.join(timeout=2.0)

        assert not t.is_alive(), "waiter hung after stop()"
        assert isinstance(outcome.get("error"), ConnectionClosedIntentionally)
        assert not isinstance(outcome.get("error"), RecoverableConnectionError)

    def test_clean_self_termination_wakes_blocked_waiter_recoverable(self, fake_conn):
        # A dead transport (NOT an intentional stop()) is a failure, so the
        # waiter still gets a recoverable error and may reconnect.
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        d.start()
        t, outcome = self._park_waiter(d, d.generation)

        fake_conn._transport.connected = False  # drainer self-terminates next tick
        t.join(timeout=2.0)

        assert not t.is_alive(), "waiter hung after clean self-termination"
        assert isinstance(outcome.get("error"), RecoverableConnectionError)
        assert not isinstance(outcome.get("error"), ConnectionClosedIntentionally)
        d.stop(join_timeout=1.0)

    def test_wait_raises_intentional_after_stop_on_repeat(self, drainer):
        # Once stopped intentionally, every wait_activity keeps raising the same
        # non-recoverable signal (never hangs, never flips to recoverable).
        drainer.start()
        drainer.stop(join_timeout=1.0)

        for _ in range(3):
            with pytest.raises(ConnectionClosedIntentionally):
                drainer.wait_activity(timeout=None, since_generation=drainer.generation)

    def test_buffered_frame_wins_over_terminal_signal(self, drainer):
        # A frame pumped before termination must still be delivered: generation
        # advance beats the terminal flag, mirroring how it beats _exc.
        drainer.start()
        since = drainer.generation
        drainer._notify_activity()  # frame buffered
        drainer.stop(join_timeout=1.0)  # then terminated

        # Returns (does not raise): buffered activity wins.
        drainer.wait_activity(timeout=5.0, since_generation=since)

    def test_fail_error_survives_a_later_intentional_stop(self, fake_conn):
        # Priority: a real _fail error outranks the terminal/intentional signal.
        # A failure recorded first must stay recoverable even if stop() (from a
        # follow-up teardown) marks the drainer intentional afterwards.
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        boom = OSError("broker dropped")
        d._fail(boom)
        with d._activity_cond:
            d._intentional_stop = True  # a later teardown stop()

        with pytest.raises(OSError) as exc_info:
            d.wait_activity(timeout=1.0, since_generation=d.generation)
        assert exc_info.value is boom


class TestIntentionalCloseExceptionType:
    """The signal type is chosen so ensure() does not resurrect an intentionally
    closed connection, while ordinary `except ConnectionError` still catches it.
    """

    def test_not_recoverable_but_is_connection_error(self):
        conn = kombu_pyamqp_threadsafe.KombuConnection("amqp://guest:guest@127.0.0.1:5672/")
        # Non-recoverable: ensure()/Consumer must NOT retry/reconnect on it.
        assert not issubclass(ConnectionClosedIntentionally, conn.recoverable_connection_errors)
        # Still a connection error: existing except-blocks catch it, and
        # `connected` classifies it as "not connected".
        assert issubclass(ConnectionClosedIntentionally, conn.connection_errors)

    def test_exposed_at_package_top_level(self):
        assert (
            kombu_pyamqp_threadsafe.ConnectionClosedIntentionally is ConnectionClosedIntentionally
        )


# ====================
# Unexpected error in _run routes to _fail
# ====================


class TestRunErrorRouting:
    """An exception escaping the loop body (outside _drain_into_buffers) must
    reach _fail — recorded and broadcast — not die silently on the thread.
    """

    def test_sel_register_failure_routed_to_fail(self, fake_conn):
        # Socket closed before registration → sel.register(conn_sock) raises
        # ValueError (fd == -1) from inside _run, outside _drain_into_buffers.
        fake_conn._transport.sock.close()
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)

        d.start()
        d._thread.join(timeout=1.0)

        assert d.is_running is False
        assert d._exc is not None, "unexpected _run error must be routed to _fail"
        assert fake_conn.marked_for_teardown is True
        d.stop(join_timeout=1.0)

    def test_run_error_wakes_blocked_waiter(self, fake_conn):
        fake_conn._transport.sock.close()
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)

        outcome: dict = {}

        def waiter():
            try:
                d.wait_activity(timeout=None, since_generation=0)
            except BaseException as exc:
                outcome["error"] = exc

        t = threading.Thread(target=waiter, daemon=True)
        # Park BEFORE start so the waiter is already waiting when _run crashes.
        t.start()
        time.sleep(0.05)
        d.start()
        t.join(timeout=2.0)

        assert not t.is_alive(), "waiter hung after _run crashed"
        assert outcome.get("error") is not None
        d.stop(join_timeout=1.0)


# ====================
# Heartbeat ticker — _loop calls conn.heartbeat_tick() at negotiated cadence
# ====================


class HeartbeatFakeConnection(FakeConnection):
    """Fake conn for heartbeat-tick tests: records every heartbeat_tick call
    (timestamp, rate) and can be scripted to raise on a given call number.

    raise_exc defaults to ConnectionForced ("too many heartbeats missed", the
    receive-side failure). Pass an OSError to model a heartbeat SEND that fails
    (RST/EPIPE) — the write-side failure.
    """

    def __init__(
        self,
        heartbeat: float,
        raise_on_call: int | None = None,
        raise_exc: Exception | None = None,
    ):
        super().__init__()
        self.heartbeat = heartbeat
        self.heartbeat_tick_calls: list[tuple[float, int]] = []
        self._raise_on_call = raise_on_call
        self._raise_exc = raise_exc or ConnectionForced("Too many heartbeats missed")

    def heartbeat_tick(self, rate=2):
        self.heartbeat_tick_calls.append((time.monotonic(), rate))
        if (
            self._raise_on_call is not None
            and len(self.heartbeat_tick_calls) == self._raise_on_call
        ):
            raise self._raise_exc


class TestHeartbeatTick:
    def test_ticks_at_negotiated_cadence(self):
        # poll_tick_s is deliberately coarse (1.0s): the select timeout must
        # be driven down to heartbeat/4 by the ticker, not by poll_tick_s.
        conn = HeartbeatFakeConnection(heartbeat=0.2)
        d = ConnectionDrainer(conn, poll_tick_s=1.0)

        d.start()
        try:
            time.sleep(0.5)
        finally:
            d.stop(join_timeout=1.0)

        calls = [rate for _, rate in conn.heartbeat_tick_calls]
        assert len(calls) >= 3, (
            f"expected several ticks in 0.5s at a 0.05s cadence, got {conn.heartbeat_tick_calls}"
        )
        assert all(rate == 2 for rate in calls)

    def test_heartbeat_zero_disables_ticker(self):
        conn = HeartbeatFakeConnection(heartbeat=0)
        d = ConnectionDrainer(conn, poll_tick_s=0.05)

        d.start()
        try:
            time.sleep(0.3)
        finally:
            d.stop(join_timeout=1.0)

        assert conn.heartbeat_tick_calls == []

    def test_connection_forced_routes_to_fail(self):
        conn = HeartbeatFakeConnection(heartbeat=0.1, raise_on_call=1)
        d = ConnectionDrainer(conn, poll_tick_s=0.05)
        since = d.generation

        d.start()
        try:
            with pytest.raises(ConnectionForced):
                d.wait_activity(timeout=2.0, since_generation=since)

            assert conn.marked_for_teardown is True
            assert d._exc is not None
        finally:
            d.stop(join_timeout=1.0)  # thread already dead; must be a safe no-op


class TestHeartbeatWriteFailure:
    """A heartbeat SEND that fails on the drainer thread (RST/EPIPE that does
    not flip transport.connected) must route to _fail as a recoverable
    connection error — never through collect() (which self-stops the drainer)
    and never surfacing a RuntimeError to waiters. The receive-side
    (ConnectionForced) already worked; this is the write side.
    """

    def test_tick_heartbeat_routes_write_oserror_to_fail(self):
        conn = HeartbeatFakeConnection(
            heartbeat=0.2, raise_on_call=1, raise_exc=OSError("Broken pipe")
        )
        d = ConnectionDrainer(conn, poll_tick_s=1.0)

        keep_running = d._tick_heartbeat()

        assert keep_running is False
        assert isinstance(d._exc, OSError)
        assert not isinstance(d._exc, RuntimeError)
        assert conn.marked_for_teardown is True

    def test_heartbeat_write_failure_wakes_waiter_recoverable(self):
        conn = HeartbeatFakeConnection(
            heartbeat=0.2, raise_on_call=1, raise_exc=OSError("Broken pipe")
        )
        d = ConnectionDrainer(conn, poll_tick_s=1.0)
        since = d.generation

        d._tick_heartbeat()

        # OSError is a recoverable connection error (ensure() reconnects),
        # unlike the RuntimeError the pre-fix collect()/self-stop produced.
        with pytest.raises(OSError):
            d.wait_activity(timeout=1.0, since_generation=since)


class TestResolveWriteTimeout:
    """The bound for the heartbeat write: explicit override wins; otherwise it is
    derived from the negotiated heartbeat (half the liveness window) and clamped
    to [floor, ceiling]; None when heartbeat is off (the ticker never runs).
    """

    def test_explicit_override_wins(self, fake_conn):
        d = ConnectionDrainer(fake_conn, write_timeout_s=2.5)
        assert d._resolve_write_timeout(heartbeat_interval=60) == 2.5
        # Override applies even with heartbeat off (harmless: ticker won't run).
        assert d._resolve_write_timeout(heartbeat_interval=0) == 2.5

    def test_none_when_heartbeat_off_and_no_override(self, fake_conn):
        d = ConnectionDrainer(fake_conn)
        assert d._resolve_write_timeout(heartbeat_interval=0) is None

    def test_derived_and_clamped_from_heartbeat(self, fake_conn):
        d = ConnectionDrainer(fake_conn)
        assert d._resolve_write_timeout(60) == 5.0  # heartbeat/2=30, capped at ceiling
        assert d._resolve_write_timeout(8) == 4.0  # heartbeat/2, within bounds
        assert d._resolve_write_timeout(1) == 1.0  # heartbeat/2=0.5, raised to floor


class TestHeartbeatWriteTimeout:
    """A heartbeat SEND must be bounded by a write timeout. If the peer's TCP
    receive window is shut (peer not reading, kernel send buffer full), an
    unbounded sock.sendall() blocks for many minutes while _transport_lock is
    held — wedging publishers and close(), with the self-pipe powerless (the
    thread is stuck in a write syscall, not in select). The drainer bounds the
    write via the transport's having_timeout() so it fails fast and routes to
    _fail, exactly like any other write failure.
    """

    class _WriteConnection(FakeConnection):
        """Its heartbeat_tick performs a real blocking write on the transport,
        mirroring send_heartbeat -> frame_writer -> transport.write. Backed by a
        real transport+socket so the write actually blocks/times out.
        """

        def __init__(self, transport):
            super().__init__(transport=transport)
            self.heartbeat = 60
            self.tick_calls = 0

        def heartbeat_tick(self, rate=2):
            self.tick_calls += 1
            # An 8-byte heartbeat frame; blocks if the send buffer is full,
            # unless the caller bounded the write with a socket timeout.
            self._transport.write(b"\x08\x00\x00\x00\x00\x00\x00\xce")

    @staticmethod
    def _real_transport(sock):
        import amqp.transport

        transport = amqp.transport.TCPTransport.__new__(amqp.transport.TCPTransport)
        transport.sock = sock
        transport.connected = True
        transport._write = sock.sendall
        transport._read_buffer = b""
        return transport

    @staticmethod
    def _wedged_pair():
        """A socketpair whose sender's send buffer is already full, so the next
        blocking sendall() hangs until it either drains (never — the peer never
        reads) or a write timeout fires.
        """
        writer, reader = socket.socketpair()
        writer.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        reader.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        writer.setblocking(False)
        with contextlib.suppress(BlockingIOError):
            while True:
                writer.send(b"\x00" * 4096)
        writer.setblocking(True)  # back to blocking: sendall() will now hang
        return writer, reader

    def test_wedged_heartbeat_write_is_bounded_not_hung(self):
        writer, reader = self._wedged_pair()
        conn = self._WriteConnection(self._real_transport(writer))
        d = ConnectionDrainer(conn, poll_tick_s=1.0)
        result: dict = {}

        def run_tick():
            started = time.monotonic()
            keep = d._tick_heartbeat(write_timeout=0.3)
            result["elapsed"] = time.monotonic() - started
            result["keep"] = keep

        # daemon: if the fix is absent the write hangs; the process must not wedge.
        t = threading.Thread(target=run_tick, daemon=True)
        try:
            t.start()
            t.join(timeout=2.0)

            assert not t.is_alive(), (
                "heartbeat write hung: an unbounded sendall on a full send "
                "buffer did not return within 2s (write timeout not applied)"
            )
            assert result["elapsed"] < 1.5, (
                f"write timeout (0.3s) not honored: tick took {result['elapsed']:.2f}s"
            )
            assert result["keep"] is False
            assert isinstance(d._exc, OSError)  # socket.timeout is an OSError
            assert conn.marked_for_teardown is True
        finally:
            # Unblocks a still-hung sendall (RED path) so the daemon can exit.
            reader.close()
            writer.close()

    def test_wedged_write_wakes_waiter_recoverable(self):
        writer, reader = self._wedged_pair()
        conn = self._WriteConnection(self._real_transport(writer))
        d = ConnectionDrainer(conn, poll_tick_s=1.0)
        since = d.generation
        try:
            d._tick_heartbeat(write_timeout=0.3)
            # socket.timeout is an OSError -> recoverable; ensure() reconnects.
            with pytest.raises(OSError):
                d.wait_activity(timeout=1.0, since_generation=since)
        finally:
            reader.close()
            writer.close()

    def test_healthy_write_succeeds_and_restores_socket_timeout(self):
        writer, reader = socket.socketpair()
        writer.settimeout(None)  # ambient blocking mode, as after _init_socket
        conn = self._WriteConnection(self._real_transport(writer))
        d = ConnectionDrainer(conn, poll_tick_s=1.0)
        try:
            keep = d._tick_heartbeat(write_timeout=0.3)

            assert keep is True
            assert d._exc is None
            assert conn.tick_calls == 1
            # The scoped write timeout was restored: the socket is back to its
            # ambient blocking mode, so publisher writes (having_timeout(None),
            # which never touches the timeout) stay byte-for-byte unaffected.
            assert writer.gettimeout() is None
        finally:
            reader.close()
            writer.close()


class TestFrameWriterDrainerThreadDoesNotCollect:
    """frame_writer must not call collect() for a write done on the drainer's
    own thread (its only write is the heartbeat): collect() -> drainer.stop()
    from that thread is a self-stop RuntimeError with an aborted teardown. The
    write error is surfaced instead, for _tick_heartbeat to route to _fail.
    Application threads still collect() on a write failure (unchanged).
    """

    class _ConnectedTransport:
        connected = True

    def _make_conn(self):
        conn = kombu_pyamqp_threadsafe.ThreadSafeConnection(dedicated_drainer=True)
        conn._transport = self._ConnectedTransport()
        return conn

    def test_drainer_thread_write_failure_reraises_without_collect(self):
        conn = self._make_conn()
        # Spoof: the current (test) thread IS the drainer thread, so
        # collect()->stop() would hit the self-stop guard if reached.
        conn._drainer._thread = threading.current_thread()

        def raising_writer(*args, **kwargs):
            raise OSError("Broken pipe")

        conn.frame_writer = raising_writer  # wrapped into conn._frame_writer

        # The OSError itself must surface (for _tick_heartbeat -> _fail), NOT a
        # RuntimeError from a self-stop inside collect().
        with pytest.raises(OSError):
            conn._frame_writer(8, 0, None, None, None)

    def test_application_thread_write_failure_still_collects(self, mocker):
        conn = self._make_conn()
        conn._drainer._thread = None  # current thread is NOT the drainer

        collect_spy = mocker.patch.object(conn, "collect")

        def raising_writer(*args, **kwargs):
            raise OSError("Broken pipe")

        conn.frame_writer = raising_writer

        with pytest.raises(OSError):
            conn._frame_writer(8, 0, None, None, None)
        collect_spy.assert_called_once()


# ====================
# Self-pipe fd lifecycle — allocated on start, not in __init__
# ====================


class TestWakeupPipeLifecycle:
    def test_no_pipe_allocated_until_start(self, fake_conn):
        d = ConnectionDrainer(fake_conn)
        assert d._wakeup_r is None
        assert d._wakeup_w is None

    def test_pipe_created_on_start_and_closed_on_stop(self, fake_conn):
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        d.start()
        assert d._wakeup_r is not None
        assert d._wakeup_w is not None

        d.stop(join_timeout=1.0)
        assert d._closed is True

    def test_constructing_without_start_leaks_no_fds(self):
        before = _count_open_fds()

        drainers = [ConnectionDrainer(_FdlessConnection()) for _ in range(20)]

        after = _count_open_fds()
        del drainers
        gc.collect()

        assert after - before < 20, (
            f"fd leak: constructing 20 unstarted drainers added {after - before} fds"
        )


# ====================
# _has_input — non-blocking readiness across buffer / SSL pending / socket
# ====================


class _PendingSock:
    """Stands in for an SSL socket that buffers decrypted records below the fd."""

    def __init__(self, pending_bytes: int):
        self._pending = pending_bytes

    def pending(self) -> int:
        return self._pending


class TestHasInput:
    """The dry check is non-blocking: it must see buffered input (transport
    read buffer, SSL pending) AND fresh socket bytes, and report a stop, so the
    drainer never does a blocking read just to discover the socket is empty.
    """

    def _wire(self, fake_conn):
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        wakeup_r, wakeup_w = os.pipe()
        d._wakeup_r = wakeup_r
        sel = selectors.DefaultSelector()
        sel.register(wakeup_r, selectors.EVENT_READ)
        sel.register(fake_conn._transport.sock, selectors.EVENT_READ)

        def cleanup():
            sel.close()
            os.close(wakeup_r)
            os.close(wakeup_w)

        return d, sel, wakeup_w, cleanup

    def test_read_buffer_nonempty_is_input(self, fake_conn):
        d, sel, _w, cleanup = self._wire(fake_conn)
        try:
            fake_conn._transport._read_buffer = b"leftover"
            assert d._has_input(sel, fake_conn._transport) is True
        finally:
            cleanup()

    def test_socket_bytes_are_input(self, fake_conn):
        d, sel, _w, cleanup = self._wire(fake_conn)
        try:
            fake_conn._transport._peer.sendall(b"x")
            assert d._has_input(sel, fake_conn._transport) is True
        finally:
            cleanup()

    def test_dry_when_nothing_buffered_or_readable(self, fake_conn):
        d, sel, _w, cleanup = self._wire(fake_conn)
        try:
            assert d._has_input(sel, fake_conn._transport) is False
        finally:
            cleanup()

    def test_wakeup_reports_stop(self, fake_conn):
        d, sel, wakeup_w, cleanup = self._wire(fake_conn)
        try:
            os.write(wakeup_w, b"\x00")
            assert d._has_input(sel, fake_conn._transport) == "stop"
        finally:
            cleanup()

    def test_ssl_pending_is_input_even_when_socket_quiet(self, fake_conn):
        # SSL buffers decrypted data below the fd; select() would not report it
        # readable, so pending() must be consulted or a whole frame is stranded.
        d = ConnectionDrainer(fake_conn, poll_tick_s=0.05)
        d._wakeup_r = -1  # unused: pending() short-circuits before select()
        fake_conn._transport.sock = _PendingSock(pending_bytes=42)
        fake_conn._transport._read_buffer = b""

        assert d._has_input(sel=None, transport=fake_conn._transport) is True


# ====================
# Requirement: a socket.timeout mid-frame must not lose the half-frame
# ====================


class TestPartialFramePreservedAcrossTimeout:
    """Pins the amqp transport contract the busy-spin fix relies on: a
    read_frame that times out mid-body prepends the partial bytes back onto the
    transport read buffer, so the next read resumes it with no loss. If amqp
    ever broke this, the drainer's read-timeout would drop fragmented frames.
    """

    def test_frame_split_across_a_read_timeout_is_reassembled(self):
        import amqp.transport

        client, server = socket.socketpair()
        try:
            transport = amqp.transport.TCPTransport.__new__(amqp.transport.TCPTransport)
            transport.sock = client
            transport.connected = True
            transport._quick_recv = client.recv
            transport._read_buffer = b""
            transport.raise_on_initial_eintr = True

            # One AMQP frame: type=8 (heartbeat-ish arbitrary), channel=0,
            # 4-byte payload, frame-end 0xCE. Header is >BHI (type, channel, size).
            payload = b"BODY"
            frame = struct.pack(">BHI", 8, 0, len(payload)) + payload + b"\xce"
            head, tail = frame[:9], frame[9:]  # split mid-body

            client.settimeout(0.1)
            server.sendall(head)
            # First read: body incomplete -> socket.timeout, partial preserved.
            with pytest.raises((TimeoutError, OSError)):
                transport.read_frame()
            assert transport._read_buffer, "partial frame bytes must be retained"

            # The rest arrives; the frame reassembles intact.
            server.sendall(tail)
            frame_type, channel, got = transport.read_frame()
            assert frame_type == 8
            assert channel == 0
            assert got == payload
        finally:
            client.close()
            server.close()


# ====================
# drain_events(_nodispatch=True) still dispatches channel-0 control frames
# ====================


class _StubDrainer:
    """Minimal drainer stand-in for testing the drain_events routing: owns
    reads, no activity, wait_activity is a no-op.
    """

    should_own_reads = True
    generation = 0

    def wait_activity(self, timeout, since_generation):
        return


class TestNodispatchDispatchesConnectionEvents:
    """`connected` and other health checks drain with _nodispatch=True. In
    drainer mode that path must still dispatch channel-0 control frames
    (Connection.Close/Blocked/CloseOk), so a broker Close the drainer buffered
    surfaces instead of being silently held (connected must go False).
    """

    def _instrument(self, conn):
        calls: list[str] = []
        conn._dispatch_connection_events = lambda: calls.append("channel0") or 0
        conn._dispatch_pending_events = lambda: calls.append("pending") or 0
        return calls

    def test_nodispatch_dispatches_channel_zero_only(self):
        conn = kombu_pyamqp_threadsafe.ThreadSafeConnection()
        conn._drainer = _StubDrainer()
        calls = self._instrument(conn)

        conn.drain_events(timeout=0, _nodispatch=True)

        # Channel-0 control frames dispatched; application channels suppressed.
        assert "channel0" in calls
        assert "pending" not in calls

    def test_full_dispatch_path_unchanged(self):
        conn = kombu_pyamqp_threadsafe.ThreadSafeConnection()
        conn._drainer = _StubDrainer()
        calls = self._instrument(conn)

        conn.drain_events(timeout=0, _nodispatch=False)

        # Full path routes everything through _dispatch_pending_events (which
        # itself covers channel 0); the _nodispatch-only shortcut is not taken.
        assert "pending" in calls
        assert "channel0" not in calls
