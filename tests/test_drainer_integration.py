"""Integration tests: dedicated-drainer thread against a real RabbitMQ broker.

127.0.0.1:5672 by default — see tests/conftest.py for the rabbitmq_*
fixtures. Scope: thread-count lifecycle around connect/close/collect, plus
frame delivery, drain_events timeout semantics, and Rule 2 error propagation
now that the drain loop reads and buffers frames.
"""

import base64
import contextlib
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import amqp.exceptions
import pytest

import kombu_pyamqp_threadsafe
from testing import PropagatingThread
from toxiproxy_client import toxic_timeout

_MGMT_URL = "http://127.0.0.1:15672"
_MGMT_AUTH = "Basic " + base64.b64encode(b"guest:guest").decode()


def _mgmt(method: str, path: str):
    req = urllib.request.Request(_MGMT_URL + path, method=method)
    req.add_header("Authorization", _MGMT_AUTH)
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read()
    return json.loads(body) if body else None


def _find_broker_connection(tag: str, deadline_s: float = 8.0) -> "str | None":
    """Return the broker-side name of the connection tagged via
    client_properties.connection_name. RabbitMQ management stats register a new
    connection a couple of seconds late, so this polls until it appears.
    """
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        for conn in _mgmt("GET", "/api/connections"):
            if (conn.get("client_properties") or {}).get("connection_name") == tag:
                return conn["name"]
        time.sleep(0.3)
    return None


CLOSE_JOIN_SLACK_S = 2.5  # stop() bounds the join at 2s; this adds test-scheduling slack

# Fast enough to keep the "quiet for several intervals" tests well under
# pytest's default patience, slow enough that the 0.05s selector floor
# (poll_tick_s) never dominates the heartbeat/4 cadence in practice.
HEARTBEAT_S = 1


def _drainer_thread_names() -> list[str]:
    return [t.name for t in threading.enumerate() if t.name.startswith("kombu-pyamqp-drainer-")]


class TestDrainerLifecycleWithOptionOn:
    def test_exactly_one_drainer_thread_after_connect(self, rabbitmq_dsn):
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}
        )
        try:
            connection.connect()
            assert _drainer_thread_names() != []
            assert len(_drainer_thread_names()) == 1
        finally:
            connection.close()

    def test_zero_drainer_threads_after_close(self, rabbitmq_dsn):
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}
        )
        connection.connect()
        assert len(_drainer_thread_names()) == 1

        started = time.monotonic()
        connection.close()
        elapsed = time.monotonic() - started

        assert _drainer_thread_names() == []
        assert elapsed < CLOSE_JOIN_SLACK_S, (
            f"close() took {elapsed:.2f}s — join did not bound the wait"
        )

    def test_zero_drainer_threads_after_collect(self, rabbitmq_dsn):
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}
        )
        try:
            connection.connect()
            assert len(_drainer_thread_names()) == 1

            connection.collect()

            assert _drainer_thread_names() == []
        finally:
            connection.close()

    def test_reconnect_after_collect_starts_a_fresh_single_drainer(self, rabbitmq_dsn):
        """A new ThreadSafeConnection after collect() gets its own drainer.

        The old one does not linger alongside it.
        """
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}
        )
        try:
            connection.connect()
            assert len(_drainer_thread_names()) == 1

            connection.collect()
            assert _drainer_thread_names() == []

            connection.connect()
            assert len(_drainer_thread_names()) == 1
        finally:
            connection.close()


class TestDrainerLifecycleWithOptionOff:
    def test_no_drainer_thread_created_without_option(self, rabbitmq_dsn):
        connection = kombu_pyamqp_threadsafe.KombuConnection(rabbitmq_dsn)
        try:
            connection.connect()
            assert _drainer_thread_names() == []
        finally:
            connection.close()


class TestFrameDeliveryViaDrainer:
    """Iteration 4: the drainer pumps frames; consumers receive them through
    drain_events, and no application thread is ever elected as the reader.
    """

    def test_simplequeue_roundtrip(self, rabbitmq_dsn):
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}
        )
        queue = connection.SimpleQueue("drainer-roundtrip")
        try:
            queue.clear()
            queue.put("hello-drainer")

            message = queue.get(block=True, timeout=5)
            assert message.payload == "hello-drainer"
            message.ack()
        finally:
            queue.clear()
            queue.close()
            connection.close()

    def test_only_the_drainer_thread_reads_the_socket(self, rabbitmq_dsn):
        """The spy on start_drain proves the "exactly one reader" ownership:
        every socket read goes through the drainer thread, never an app thread.
        """
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}
        )
        connection.connect()

        guard = connection._connection._drain_guard
        original_start_drain = guard.start_drain
        caller_threads: list[str] = []
        lock = threading.Lock()

        def spy():
            with lock:
                caller_threads.append(threading.current_thread().name)
            return original_start_drain()

        guard.start_drain = spy  # type: ignore[method-assign]

        queue = connection.SimpleQueue("drainer-owner-check")
        try:
            queue.clear()
            queue.put("owned")
            message = queue.get(block=True, timeout=5)
            assert message.payload == "owned"
            message.ack()

            with lock:
                observed = list(caller_threads)
            assert observed, "the drainer must have read at least once"
            assert all(name.startswith("kombu-pyamqp-drainer-") for name in observed), (
                f"an application thread was elected as reader: {observed}"
            )
        finally:
            queue.clear()
            queue.close()
            connection.close()


class TestDrainEventsTimeoutSemantics:
    """Iteration 5: drain_events timeout behavior in drainer mode."""

    def test_connected_stays_true_on_a_quiet_connection(self, rabbitmq_dsn):
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}, heartbeat=0
        )
        try:
            connection.connect()
            _ = connection.default_channel  # establish
            # No traffic: connected must not hang or flip false. It routes
            # through wait_activity(0) -> socket.timeout -> "alive".
            for _ in range(3):
                assert connection.connected is True
                time.sleep(0.1)
        finally:
            connection.close()

    def test_get_on_empty_queue_times_out(self, rabbitmq_dsn):
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}, heartbeat=0
        )
        queue = connection.SimpleQueue("drainer-empty")
        try:
            queue.clear()
            started = time.monotonic()
            with pytest.raises(queue.Empty):
                queue.get(block=True, timeout=0.3)
            elapsed = time.monotonic() - started
            assert 0.25 < elapsed < 2.0, f"timeout not honored: {elapsed:.2f}s"
        finally:
            queue.clear()
            queue.close()
            connection.close()


class TestRule2ErrorPropagation:
    """Iteration 6: a broken connection surfaces a recoverable error to a
    thread blocked in drain_events, and keeps surfacing it (README Rule 2).

    Uses the bench proxy on 25672 (network_failure operates there) so the
    break is a real remote RST the drainer's read observes — not a local fd
    close that select() would just see vanish.
    """

    def test_blocked_waiter_gets_recoverable_error_on_break(
        self, rabbitmq_proxy, network_failure, rabbitmq_username, rabbitmq_password
    ):
        dsn = f"amqp://{rabbitmq_username}:{rabbitmq_password}@127.0.0.1:25672/"
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            dsn, transport_options={"dedicated_drainer": True}, heartbeat=0
        )
        connection.connect()
        conn = connection._connection

        errors: list[Exception] = []
        waiting = threading.Event()

        def waiter():
            waiting.set()
            try:
                # Quiet connection + heartbeat off: this blocks in wait_activity
                # until the drainer's read fails on the reset.
                conn.drain_events(timeout=8)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=waiter)
        thread.start()
        assert waiting.wait(timeout=2.0)
        time.sleep(0.2)  # ensure the waiter is parked in wait_activity

        with network_failure.reset_peer():
            thread.join(timeout=8.0)

        if thread.is_alive():
            pytest.fail("waiter did not wake after the connection was reset")

        assert len(errors) == 1, f"expected exactly one error, got {errors}"
        exc = errors[0]
        assert isinstance(exc, connection.recoverable_connection_errors), (
            f"waiter must get a recoverable connection error, got {exc!r}"
        )

        # Rule 2: the error is not one-shot — a repeat drain re-raises it.
        with pytest.raises(connection.recoverable_connection_errors):
            conn.drain_events(timeout=1)

        with contextlib.suppress(Exception):  # already-broken transport
            connection.close()

    def test_blocked_waiter_wakes_when_collect_stops_the_drainer(self, rabbitmq_dsn):
        """A consumer parked in drain_events(timeout=None) must wake, not hang,
        when the connection is torn down. collect() on a live connection here is
        a teardown driven from the application (not a socket failure the drainer
        detects itself), so — by the owner's decision — the waiter is closed
        intentionally: it receives a NON-recoverable error, so a surrounding
        ensure()/Consumer does not reconnect and resurrect it. (A genuine socket
        failure still wakes it recoverable — see
        test_blocked_waiter_gets_recoverable_error_on_break.)
        """
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}, heartbeat=0
        )
        connection.connect()
        conn = connection._connection

        errors: list[Exception] = []
        waiting = threading.Event()

        def waiter():
            waiting.set()
            try:
                conn.drain_events(timeout=None)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=waiter)
        thread.start()
        assert waiting.wait(timeout=2.0)
        time.sleep(0.2)  # ensure the waiter is parked in wait_activity

        connection.collect()  # application-driven teardown -> intentional stop

        thread.join(timeout=3.0)
        if thread.is_alive():
            pytest.fail("waiter hung after collect() stopped the drainer")

        assert len(errors) == 1, f"expected exactly one error, got {errors}"
        assert isinstance(errors[0], kombu_pyamqp_threadsafe.ConnectionClosedIntentionally), (
            f"an application-driven collect() must close the waiter intentionally, got {errors[0]!r}"
        )
        assert not isinstance(errors[0], connection.recoverable_connection_errors), (
            "an intentional close must NOT be recoverable, or ensure() would resurrect it"
        )

        with contextlib.suppress(Exception):
            connection.close()

    def test_intentional_close_is_not_resurrected_by_ensure(self, rabbitmq_dsn, mocker):
        """Owner scenario: a consumer draining under ensure() while the
        application calls connection.close() must receive a non-recoverable
        error and ensure() must NOT reconnect (no _connection_factory call) —
        the intentionally closed connection is not resurrected.
        """
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}, heartbeat=0
        )
        connection.connect()
        conn = connection._connection

        factory_spy = mocker.patch.object(
            connection, "_connection_factory", wraps=connection._connection_factory
        )

        errors: list[Exception] = []
        ready = threading.Event()

        def consumer():
            def drain():
                conn.drain_events(timeout=1)

            ensured = connection.ensure(
                connection,
                drain,
                max_retries=5,
                interval_start=0,
                interval_step=0,
                interval_max=0.05,
            )
            ready.set()
            try:
                for _ in range(50):
                    ensured()  # returns on a quiet tick; raises once closed
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=consumer)
        thread.start()
        assert ready.wait(timeout=2.0)
        time.sleep(0.3)  # let it park in a drain

        connection.close()  # the application intentionally closes

        thread.join(timeout=5.0)
        if thread.is_alive():
            pytest.fail("consumer hung after intentional close()")

        assert len(errors) == 1, f"expected exactly one error, got {errors}"
        assert not isinstance(errors[0], connection.recoverable_connection_errors), (
            f"ensure() got a recoverable error and would reconnect: {errors[0]!r}"
        )
        assert factory_spy.call_count == 0, (
            f"ensure() must not resurrect an intentionally closed connection, "
            f"but reconnected {factory_spy.call_count} time(s)"
        )


@pytest.fixture
def rabbitmq_default_proxy(toxiproxy_client):
    """The 'rabbitmq' Toxiproxy proxy backing rabbitmq_dsn (port 5672).

    Distinct from rabbitmq_bench (port 25672, benchmark-only, defined in
    tests/benchmarks/fixtures/toxiproxy.py): this is the proxy every plain
    integration test in this file already connects through by default (see
    docker-compose.test.yml — 5672 is Toxiproxy, not RabbitMQ directly).
    """
    proxy = toxiproxy_client.get_or_create_proxy(
        name="rabbitmq", listen="0.0.0.0:5672", upstream="rabbitmq:5672"
    )
    yield proxy
    proxy.remove_all_toxics()  # never leave a stray toxic for the next test


class TestHeartbeatKeepsConnectionAlive:
    """Iteration 7: with the drainer's ticker on, a connection that nobody
    drains or publishes on for several heartbeat intervals stays up — the
    ticker, not app-thread activity, is what's keeping it alive.
    """

    def test_survives_and_still_publishes_after_a_quiet_period(self, rabbitmq_dsn):
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}, heartbeat=HEARTBEAT_S
        )
        queue = connection.SimpleQueue("drainer-heartbeat-alive")
        try:
            conn = connection._connection
            assert conn.heartbeat == HEARTBEAT_S, (
                "broker must actually negotiate the requested heartbeat, or this "
                "test proves nothing about the ticker"
            )
            queue.clear()

            # Several heartbeat intervals with nobody draining or publishing.
            # Only the drainer thread's ticker is exercising the connection.
            time.sleep(4.5)

            assert connection.connected is True

            # Not just a stale flag: a real round trip through the same
            # connection proves the transport is genuinely alive.
            queue.put("still-alive")
            message = queue.get(block=True, timeout=5)
            assert message.payload == "still-alive"
            message.ack()
        finally:
            queue.clear()
            queue.close()
            connection.close()


class TestHeartbeatControlWithoutDrainer:
    """RED control for the heartbeat feature (no code under test here): with
    a heartbeat negotiated but the dedicated drainer OFF, nothing in this
    layer ever calls heartbeat_tick() unless something happens to be
    draining (see drainer.py module docstring / plan). Left quiet for the
    same span as the test above, the broker's own heartbeat monitor kills the
    connection. This demonstrates the problem the ticker (test above) solves;
    it is not asserting desired behavior of the legacy path.

    Timing-sensitive by nature (depends on the broker's own heartbeat
    enforcement, not just our client): if this becomes flaky in CI, it is the
    demonstration that is unreliable, not the feature above it verifies.

    Checked through the low-level connection.drain_events(), not through
    connection.SimpleQueue()/Producer(): those go through KombuConnection's
    own ensure()/auto-reconnect, which transparently opens a fresh connection
    and would silently heal the dead one -- masking exactly the failure this
    control is meant to demonstrate (confirmed empirically: SimpleQueue().put()
    on the dead connection here raises nothing at all).
    """

    def test_broker_kills_idle_connection_without_the_drainer(self, rabbitmq_dsn):
        connection = kombu_pyamqp_threadsafe.KombuConnection(rabbitmq_dsn, heartbeat=HEARTBEAT_S)
        connection.connect()
        conn = connection._connection
        assert conn.heartbeat == HEARTBEAT_S

        time.sleep(4.5)  # same quiet span as the drainer-on test above

        with pytest.raises(connection.recoverable_connection_errors):
            conn.drain_events(timeout=2)

        with contextlib.suppress(Exception):  # connection is already dead by design here
            connection.close()


class TestHeartbeatMissViaToxiproxy:
    """Iteration 7: a heartbeat-miss (broker-side silence, simulated with a
    Toxiproxy timeout toxic that blocks all data without closing the TCP
    connection) is detected by the drainer's own ticker — not by a socket
    error — and routed through the existing _fail path.
    """

    def test_missed_heartbeat_wakes_a_blocked_waiter_with_a_recoverable_error(
        self, rabbitmq_dsn, rabbitmq_default_proxy
    ):
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn, transport_options={"dedicated_drainer": True}, heartbeat=HEARTBEAT_S
        )
        connection.connect()
        conn = connection._connection
        assert conn.heartbeat == HEARTBEAT_S

        errors: list[Exception] = []
        waiting = threading.Event()

        def waiter():
            waiting.set()
            try:
                conn.drain_events(timeout=10)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=waiter)
        thread.start()
        assert waiting.wait(timeout=2.0)
        time.sleep(0.2)  # ensure the waiter is parked in wait_activity

        # timeout_ms=0: blocks all data indefinitely without forcing a TCP
        # close, so this is purely the drainer's local "two heartbeats
        # missed" clock firing -- not a socket error racing it.
        toxic = toxic_timeout(rabbitmq_default_proxy, timeout_ms=0)
        try:
            thread.join(timeout=8.0)
        finally:
            toxic.remove()

        if thread.is_alive():
            pytest.fail("waiter did not wake after the heartbeat was missed")

        assert len(errors) == 1, f"expected exactly one error, got {errors}"
        assert isinstance(errors[0], connection.recoverable_connection_errors), (
            f"waiter must get a recoverable connection error, got {errors[0]!r}"
        )

        with contextlib.suppress(Exception):
            connection.close()


@pytest.fixture
def requires_rabbitmq_mgmt():
    """Skip if the RabbitMQ management API is not reachable on 127.0.0.1:15672."""
    try:
        _mgmt("GET", "/api/overview")
    except (urllib.error.URLError, OSError):
        pytest.skip("RabbitMQ management API not reachable on 127.0.0.1:15672")


class TestGracefulBrokerCloseDetection:
    """A graceful broker Connection.Close (reply-code 320) must surface through
    `connected` in drainer mode, at legacy parity (~0.1s). The drainer only
    buffers the channel-0 Close; `connected`'s health-check drain
    (drain_events(0, _nodispatch=True)) has to dispatch channel 0 so the Close
    raises and connected flips to False — otherwise a dead connection reads as
    alive (the phase4-reconnect regression).
    """

    def test_connected_detects_management_kill(self, rabbitmq_dsn, requires_rabbitmq_mgmt):
        tag = "drainer-close-" + uuid.uuid4().hex[:8]
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn,
            transport_options={
                "dedicated_drainer": True,
                "client_properties": {"connection_name": tag},
            },
        )
        try:
            connection.connect()
            _ = connection.default_channel
            assert connection.connected is True

            name = _find_broker_connection(tag)
            assert name is not None, "connection did not register in the broker"

            # Polite AMQP Connection.Close (reply-code 320), like the repro.
            _mgmt("DELETE", "/api/connections/" + urllib.parse.quote(name, safe=""))

            deadline = time.monotonic() + 5.0
            detected = None
            while time.monotonic() < deadline:
                if not connection.connected:
                    detected = time.monotonic()
                    break
                time.sleep(0.05)

            assert detected is not None, (
                "drainer mode did not detect the graceful broker Close within 5s"
            )
        finally:
            with contextlib.suppress(Exception):
                connection.close()


class TestLegacyCloseUnderConcurrentDrain:
    """Legacy (dedicated_drainer off) close() must return even when another
    thread is actively parked in drain_events() at the moment it is called.

    ThreadSafeConnection.close() sends Connection.Close and then blocks in
    drain_events() waiting for CloseOk. If a concurrent thread has already
    won DrainGuard's start_drain() and is mid-read at that moment, wrapping
    the wait in the outer _transport_lock inverts lock order against that
    reader: the reader needs _transport_lock to deliver CloseOk, while
    close() would be holding it and waiting on the reader instead. Neither
    side has a timeout -- a permanent circular wait. See the production
    comment on ThreadSafeConnection.close for the invariant this protects.

    Reproducing the race needs precise timing: the background thread must
    have won start_drain() and be parked in a blocking read exactly when
    close() reaches its own CloseOk wait. A single attempt is probabilistic,
    so this retries independent attempts (fresh connection each time) and
    fails on the first attempt that does not finish inside the watchdog.
    """

    # How long close() gets before we call it deadlocked. Generous versus the
    # observed post-fix close time (~2s: one CONSUMER_DRAIN_TIMEOUT_S turn
    # behind the consumer's blocking read plus channel teardown).
    CLOSE_WATCHDOG_S = 5.0
    N_ATTEMPTS = 5
    # Each blocking read the consumer makes. Long enough that close() almost
    # certainly lands mid-read (the deadlock window), short enough that a
    # failed attempt retires quickly.
    CONSUMER_DRAIN_TIMEOUT_S = 1.0
    # Delay between starting the consumer and calling close(): lets the
    # consumer win DrainGuard's start_drain() and park in its blocking read.
    # Well below CONSUMER_DRAIN_TIMEOUT_S, so close() hits the middle of the
    # consumer's first read rather than racing its start or its timeout edge.
    CONSUMER_START_DELAY_S = 0.15

    def test_close_returns_while_a_thread_is_actively_draining(self, rabbitmq_dsn):
        for attempt in range(self.N_ATTEMPTS):
            connection = kombu_pyamqp_threadsafe.KombuConnection(
                rabbitmq_dsn,
                heartbeat=0,
                # Pin the legacy path explicitly: this test must keep
                # exercising it even if the library's default ever flips.
                transport_options={"dedicated_drainer": False},
            )
            connection.connect()
            conn = connection._connection
            assert conn._drainer is None, "test requires the legacy (no-drainer) path"

            stop_event = threading.Event()
            close_started = threading.Event()

            def consumer_loop(conn=conn, stop_event=stop_event, close_started=close_started):
                while not stop_event.is_set():
                    try:
                        conn.drain_events(timeout=self.CONSUMER_DRAIN_TIMEOUT_S)
                    except TimeoutError:
                        continue
                    except (OSError, amqp.exceptions.ConnectionError):
                        if close_started.is_set():
                            # Connection closing/closed underneath this read
                            # once close() is in flight -- expected, not a
                            # test failure.
                            return
                        # Before close() starts only timeouts are expected; a
                        # connection error here means the scenario never got
                        # exercised -- surface it via PropagatingThread.join.
                        raise

            consumer_thread = PropagatingThread(
                target=consumer_loop,
                daemon=True,
                name=f"legacy-close-consumer-{attempt}",
            )
            consumer_thread.start()
            time.sleep(self.CONSUMER_START_DELAY_S)

            close_started.set()
            closer = PropagatingThread(target=connection.close, daemon=True)
            closer.start()
            closer.join(timeout=self.CLOSE_WATCHDOG_S)

            if closer.is_alive():
                pytest.fail(
                    f"close() hung on attempt {attempt} while a consumer thread was "
                    f"draining -- did not return within {self.CLOSE_WATCHDOG_S}s "
                    "(legacy lock-inversion deadlock)"
                )

            stop_event.set()
            consumer_thread.join(timeout=5.0)
            assert not consumer_thread.is_alive(), (
                f"consumer thread on attempt {attempt} did not stop after a "
                "successfully completed close()"
            )
