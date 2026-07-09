"""Tests for KombuConnection.ensure() — the parallel-teardown race fix.

Upstream ensure() collects unconditionally on connection errors, so a thread
holding a stale error (its connection already replaced by another thread's
reconnect) tore down the live replacement — reconnect ping-pong. Our fork
collects only if the failing attempt's connection is still current.
"""

import threading

from amqp import RecoverableConnectionError

from testing import PropagatingThread


def test_ensure_does_not_collect_connection_that_replaced_seen_connection(connection) -> None:
    """Deterministic, single-threaded core regression.

    `fun` replaces the connection from inside (emulating a concurrent thread)
    after ensure() has already snapshotted `seen_connection` — stock kombu
    would collect the just-built replacement.
    """
    connection.ensure_connection(max_retries=1)
    c1 = connection._connection
    assert c1 is not None

    state: dict = {}

    def fun():
        if "c2" not in state:
            # Emulate a concurrent thread: c1 torn down, live c2 built —
            # all before our exception surfaces.
            connection.collect()
            connection.ensure_connection(max_retries=1)
            state["c2"] = connection._connection
            raise RecoverableConnectionError("stale error from c1")
        return "ok"

    ensured = connection.ensure(connection, fun, max_retries=3)
    assert ensured() == "ok"
    assert connection._connection is state["c2"], (
        "ensure() must not tear down a connection that replaced the one "
        "the failing call actually saw"
    )


def test_ensure_collects_and_reconnects_when_seen_connection_is_still_current(connection) -> None:
    """Contract preserved for a real error on the *current* connection.

    Nothing swapped the connection out from under us, so ensure() must still
    tear it down and reconnect — otherwise the fix would be too broad and mask
    real failures.
    """
    connection.ensure_connection(max_retries=1)
    c1 = connection._connection
    assert c1 is not None

    calls = {"n": 0}

    def fun():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RecoverableConnectionError("genuine connection error")
        return "ok"

    ensured = connection.ensure(connection, fun, max_retries=3)
    assert ensured() == "ok"
    assert connection._connection is not None
    assert connection._connection is not c1, (
        "a genuine error on the current connection must still trigger collect() + reconnect"
    )


def test_ensure_connects_without_collect_when_seen_connection_is_none(connection) -> None:
    """`seen_connection` is None before the first connection is established.

    Nothing to tear down, so `_ensure_connection()` alone connects.
    """
    assert connection._connection is None

    calls = {"n": 0}

    def fun():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RecoverableConnectionError("not connected yet")
        return "ok"

    ensured = connection.ensure(connection, fun, max_retries=3)
    assert ensured() == "ok"
    assert connection._connection is not None


def test_ensure_does_not_collect_connection_replaced_by_another_thread(connection) -> None:
    """Multi-threaded variant of the same interleaving.

    T2 blocks inside `fun` while T1 completes a full teardown+reconnect; T2's
    error then surfaces from the replaced connection, and T2's ensure() loop
    must not collect the live connection T1 built.
    """
    connection.ensure_connection(max_retries=1)
    c1 = connection._connection
    assert c1 is not None

    t2_entered_fun = threading.Event()
    release_t2_fun = threading.Event()
    state: dict = {}

    def fun():
        if "attempts" not in state:
            state["attempts"] = 0
        state["attempts"] += 1
        if state["attempts"] == 1:
            # Block until T1 fully replaces the connection, then raise a
            # stale error from the now-replaced c1.
            t2_entered_fun.set()
            release_t2_fun.wait(timeout=2.0)
            raise RecoverableConnectionError("stale error from c1")
        # Retry after revive: succeeds immediately.
        return "ok"

    def t2_runner():
        ensured = connection.ensure(connection, fun, max_retries=3)
        state["result"] = ensured()

    t2 = PropagatingThread(target=t2_runner)
    t2.start()
    assert t2_entered_fun.wait(timeout=2.0), "T2 must enter fun() first"

    # T1: complete teardown + reconnect cycle while T2 is blocked.
    connection.collect()
    connection.ensure_connection(max_retries=1)
    c2 = connection._connection
    assert c2 is not None
    assert c2 is not c1

    # Release the stale error; T2 must not collect c2 out from under us.
    release_t2_fun.set()
    t2.join(timeout=2.0)

    assert state.get("result") == "ok"
    assert connection._connection is c2, (
        "stale error from T2 must not tear down the live connection T1 already built"
    )
