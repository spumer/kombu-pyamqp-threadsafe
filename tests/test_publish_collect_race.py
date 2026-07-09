"""Integration tests for coordination between critical channel sections and
KombuConnection.collect().

A publisher used to hit `AttributeError: 'NoneType' object has no attribute
'transport'` when a concurrent collect() nulled channel.connection between
the truthy-check and the deref — and kombu does not retry AttributeError.
The coordination layers (the connection teardown mark, ChannelCoordinator,
channel_operation) guarantee publishers only ever see recoverable errors.
"""

import threading
import time

import kombu
import pytest
from amqp import RecoverableChannelError, RecoverableConnectionError

import kombu_pyamqp_threadsafe
from testing import PropagatingThread


@pytest.fixture
def connection(rabbitmq_dsn):
    conn = kombu_pyamqp_threadsafe.KombuConnection(rabbitmq_dsn, default_channel_pool_size=8)
    yield conn
    conn.close()


@pytest.fixture
def declared_queue(connection):
    queue_name = "test_publish_collect_race"
    q = kombu.Queue(queue_name, channel=connection)
    q.declare()
    yield queue_name
    # Best-effort cleanup: tests intentionally tear the connection down,
    # so re-declare a fresh channel path via ensure_connection first.
    try:
        connection.ensure_connection(max_retries=1)
        kombu.Queue(queue_name, channel=connection).delete()
    except Exception:
        pass


def test_publish_raises_recoverable_when_connection_marked_for_teardown(
    connection, declared_queue
) -> None:
    """A connection marked for teardown before publish makes the publisher raise RecoverableConnectionError instead of publishing."""
    pool = connection.default_channel_pool
    channel = pool.acquire(block=False)

    # Directly simulate a concurrent teardown by marking the connection.
    connection._connection.mark_for_teardown()
    try:
        producer = kombu.Producer(channel)
        with pytest.raises(RecoverableConnectionError):
            producer.publish({"payload": 1}, routing_key=declared_queue)
    finally:
        channel.release()


def test_collect_waits_for_active_publisher(connection, declared_queue, monkeypatch) -> None:
    """channel.collect() blocks until active operations exit, so a publisher under normal latency never sees a nulled self.connection."""
    pool = connection.default_channel_pool
    channel = pool.acquire(block=False)

    publisher_entered = threading.Event()
    release_publisher = threading.Event()

    # Slow down send_method - it is invoked from inside our _basic_publish
    # while channel_operation is already open (active_operations == 1). This forces
    # channel.collect() to actually wait for us.
    original_send = channel.send_method

    def slow_send_method(*args, **kwargs):
        publisher_entered.set()
        release_publisher.wait(timeout=2.0)
        return original_send(*args, **kwargs)

    monkeypatch.setattr(channel, "send_method", slow_send_method)

    def publisher() -> None:
        producer = kombu.Producer(channel)
        producer.publish({"x": 1}, routing_key=declared_queue)

    t = PropagatingThread(target=publisher)
    t.start()

    assert publisher_entered.wait(timeout=2.0), "publisher must enter body"

    # Collect must wait; measure how long teardown actually takes.
    # We release publisher AFTER a small delay to prove collect waited.
    def release_after_delay():
        time.sleep(0.2)
        release_publisher.set()

    releaser = threading.Thread(target=release_after_delay)
    releaser.start()

    started = time.monotonic()
    channel.collect()
    elapsed = time.monotonic() - started

    # collect() started while the publisher's operation was active; must
    # have waited at least ~0.2s until the releaser let publisher finish.
    assert elapsed >= 0.15, f"collect() must wait for the active publisher; elapsed={elapsed}"

    t.join(timeout=2.0)
    releaser.join(timeout=1.0)


def test_teardown_timeout_still_recoverable(connection, declared_queue, monkeypatch) -> None:
    """When an active publisher blocks past CHANNEL_TEARDOWN_WAIT_S, collect() proceeds anyway and the publisher still sees only a recoverable error, never AttributeError."""
    # Shrink the wait so the test is fast and deterministic.
    monkeypatch.setattr(kombu_pyamqp_threadsafe, "CHANNEL_TEARDOWN_WAIT_S", 0.05)
    pool = connection.default_channel_pool
    channel = pool.acquire(block=False)
    # Coordinator was constructed with default 0.5s; recreate with the
    # shrunken value so this specific channel honors the fast timeout.
    channel._coordinator = kombu_pyamqp_threadsafe.ChannelCoordinator(teardown_wait_s=0.05)
    publisher_entered = threading.Event()
    release_publisher = threading.Event()
    # Slow send_method invoked from inside _basic_publish under
    # channel_operation: keeps active_operations == 1 so begin_teardown() has to
    # wait, and with the shrunken window it will hit the timeout.
    original_send = channel.send_method

    def slow_send_method(*args, **kwargs):
        publisher_entered.set()
        release_publisher.wait(timeout=2.0)
        return original_send(*args, **kwargs)

    monkeypatch.setattr(channel, "send_method", slow_send_method)
    exceptions: list[BaseException] = []

    def publisher() -> None:
        producer = kombu.Producer(channel)
        try:
            producer.publish({"x": 1}, routing_key=declared_queue)
        except BaseException as exc:
            exceptions.append(exc)

    t = PropagatingThread(target=publisher)
    t.start()
    assert publisher_entered.wait(timeout=2.0)
    # collect() waits ~0.05s, times out, proceeds.
    connection.collect()
    release_publisher.set()
    t.join(timeout=3.0)
    raised = list(exceptions)
    if t.exc is not None:
        raised.append(t.exc)
    assert raised, "publisher must observe an error after mid-publish teardown"
    for exc in raised:
        assert not isinstance(exc, AttributeError), (
            f"publisher must never see AttributeError; got: {exc!r}"
        )
        assert isinstance(exc, connection.recoverable_connection_errors), (
            f"expected recoverable, got {type(exc).__name__}: {exc!r}"
        )


def test_transport_none_raises_recoverable_connection_error(
    connection, declared_queue, monkeypatch
) -> None:
    """A transport that is gone mid-block raises RecoverableConnectionError, not AttributeError."""
    pool = connection.default_channel_pool
    channel = pool.acquire(block=False)
    # Raw attribute, not the `transport` property: the property
    # force-connects when _transport is None instead of reporting the
    # torn-down state.
    monkeypatch.setattr(channel.connection, "_transport", None)
    producer = kombu.Producer(channel)
    with pytest.raises(RecoverableConnectionError, match="transport closed"):
        producer.publish({"x": 1}, routing_key=declared_queue)


def test_send_timeout_raises_recoverable_channel_error(
    connection, declared_queue, monkeypatch
) -> None:
    """A send timeout maps to RecoverableChannelError, not a bare TimeoutError."""
    pool = connection.default_channel_pool
    channel = pool.acquire(block=False)

    def timing_out_send_method(*args, **kwargs):
        raise TimeoutError("forced timeout")

    monkeypatch.setattr(channel, "send_method", timing_out_send_method)
    producer = kombu.Producer(channel)
    with pytest.raises(RecoverableChannelError, match="timed out"):
        producer.publish({"x": 1}, routing_key=declared_queue)


@pytest.mark.parametrize("duration_s,n_publishers", [(1.5, 4)])
def test_no_attribute_error_under_concurrent_collect(
    connection,
    declared_queue,
    duration_s: float,
    n_publishers: int,
) -> None:
    """Under many publishers running while a background thread calls conn.collect(), no publisher ever sees AttributeError across the run."""
    stop = threading.Event()
    attr_errors: list[BaseException] = []
    recoverable: list[BaseException] = []
    published_ok = 0
    published_ok_lock = threading.Lock()

    def publisher() -> None:
        nonlocal published_ok
        while not stop.is_set():
            try:
                with connection.default_channel_pool.acquire(block=True, timeout=1.0) as ch:
                    producer = kombu.Producer(ch)
                    producer.publish({"x": 1}, routing_key=declared_queue)
                with published_ok_lock:
                    published_ok += 1
            except AttributeError as exc:
                attr_errors.append(exc)
                return
            except connection.recoverable_connection_errors as exc:
                recoverable.append(exc)
                try:
                    connection.ensure_connection()
                except Exception:
                    pass
            except Exception:
                raise

    def collector() -> None:
        while not stop.is_set():
            time.sleep(0.02)
            try:
                connection.collect()
            except Exception:
                pass

    connection.ensure_connection()
    pubs = [PropagatingThread(target=publisher) for _ in range(n_publishers)]
    coll = PropagatingThread(target=collector)
    for t in pubs:
        t.start()
    coll.start()
    time.sleep(duration_s)
    stop.set()
    for t in pubs:
        t.join(timeout=5.0)
    coll.join(timeout=5.0)
    assert not attr_errors, f"AttributeError leaked to publisher: {attr_errors[:3]!r}"
    assert published_ok > 0 or recoverable, "test did not exercise publish path"


def test_wait_raises_recoverable_when_teardown_active(connection, declared_queue) -> None:
    """channel.wait() (used by consumers and publisher-confirm mode) raises a recoverable error, never AttributeError, when teardown is active."""
    pool = connection.default_channel_pool
    channel = pool.acquire(block=False)
    connection._connection.mark_for_teardown()
    try:
        with pytest.raises(RecoverableConnectionError):
            channel.wait(method="dummy", timeout=0.1)
    finally:
        channel.release()
