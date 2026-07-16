"""Threadsafe implementation of pyamqp transport for kombu."""

import collections
import contextlib
import functools
import logging
import os
import ssl
import threading
import time
import typing
import weakref
from itertools import count

import amqp
import amqp.transport
import kombu
import kombu.connection
import kombu.resource
import kombu.simple
import kombu.transport
import kombu.transport.pyamqp
from amqp import RecoverableConnectionError, spec
from amqp.exceptions import RecoverableChannelError

from kombu_pyamqp_threadsafe.drainer import (
    DEDICATED_DRAINER_OPTION,
    ConnectionDrainer,
)
from kombu_pyamqp_threadsafe.drainer import (
    # Re-exported so users can `except kombu_pyamqp_threadsafe.ConnectionClosedIntentionally`.
    ConnectionClosedIntentionally as ConnectionClosedIntentionally,
)

if typing.TYPE_CHECKING:
    from kombu.transport.virtual import Channel


logger = logging.getLogger(__name__)

DEBUG = os.getenv("KOMBU_PYAMQP_THREADSAFE_DEBUG", "0").lower() in (
    "1",
    "true",
    "t",
    "y",
    "yes",
)


class ThreadSafeChannelPool(kombu.connection.ChannelPool):
    def __init__(self, connection, limit=None, **kwargs):
        assert isinstance(connection, KombuConnection), (
            f"Expect {KombuConnection.__qualname__}, given: {type(connection)}"
        )
        super().__init__(connection, limit=limit, **kwargs)

    @property
    def closed(self) -> bool:
        return self._closed or self.connection is None

    def setup(self):
        """Fill empty pool up to self.limit, if it's possible (limit is not None)"""
        # kombu.Resource use Queue internal lock to sync threads when they acquire resource from pool.
        # Instead, filling pool lazily when you need a new object kombu fill it on init.
        # This prevents locking and simplifies pool internals, but expensive
        super().setup()

    def acquire(self, block: bool = False, timeout: "float | None" = None) -> "ThreadSafeChannel":
        channel: ThreadSafeChannel = super().acquire(block=block, timeout=timeout)
        channel.change_owner(threading.get_ident())

        # support ThreadSafeChannel interface
        def release(close_unbound: bool = False):
            self.release(channel)

        channel.release = release  # type: ignore[assignment]

        return channel

    def prepare(self, channel: "ThreadSafeChannel") -> "ThreadSafeChannel":
        channel = super().prepare(channel)
        channel._bind_to_pool(self)
        return channel

    def release(self, resource: "ThreadSafeChannel"):
        if not resource.is_usable():
            if self.limit:
                self._dirty.discard(resource)
            return

        if self.limit:
            try:
                self._dirty.remove(resource)
            except KeyError:
                # prevent twice release
                pass
            else:
                self._resource.put_nowait(resource)
                self.release_resource(resource)
        else:
            self.close_resource(resource)


ChannelPool = ThreadSafeChannelPool


class ThreadSafeChannel(kombu.transport.pyamqp.Channel):
    connection: "ThreadSafeConnection"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner_ident = threading.get_ident()
        self._channel_pool: weakref.ReferenceType[ThreadSafeChannel] | None = None
        self._is_releasing = False
        self._coordinator = ChannelCoordinator()
        self.connection.channel_thread_bindings[self._owner_ident].add(self.channel_id)

    def _bind_to_pool(self, channel_pool: "ThreadSafeChannelPool"):
        self._channel_pool = weakref.ref(channel_pool)

    @property
    def channel_pool(self) -> "ThreadSafeChannelPool | None":
        if self._channel_pool is None:
            return None
        return self._channel_pool()

    def is_usable(self):
        if self.connection is None:
            return False

        if self.is_closing:
            return False

        return self.is_open

    def change_owner(self, new_owner):
        conn = self.connection
        if conn is None:
            raise RecoverableConnectionError("connection already closed")

        prev_owner = self._owner_ident
        self._owner_ident = new_owner
        bindings = conn.channel_thread_bindings
        bindings[prev_owner].discard(self.channel_id)
        bindings[new_owner].add(self.channel_id)

    def wait(self, *args, **kwargs):
        thread_ident = threading.get_ident()
        # workaround for case when channel used in another thread, e.g. through ChannelPool
        if thread_ident != self._owner_ident:
            self.change_owner(thread_ident)

        with channel_operation(self):
            return super().wait(*args, **kwargs)

    def collect(self):
        conn = self.connection

        # Let active operations drain before nulling self.connection. On
        # timeout we proceed anyway: a stuck publisher then sees OSError from
        # frame_writer (recoverable), never AttributeError.
        if not self._coordinator.begin_teardown():
            logger.warning(
                "channel %s teardown timeout: operations still active",
                self.channel_id,
            )

        channel_frame_buff = conn.channel_frame_buff.pop(self.channel_id, ())
        if channel_frame_buff:
            logger.warning(
                "No drained events after close (%s pending events)",
                len(channel_frame_buff),
            )

        bindings = conn.channel_thread_bindings.get(self._owner_ident)
        if bindings is not None:
            bindings.discard(self.channel_id)

        # Detach from pool before calling super().collect() to prevent re-entrant calls
        # super().collect() may trigger events that call close() again
        pool = self.channel_pool
        if pool is not None:
            self._channel_pool = None

        super().collect()

        # Release to pool only if we detached it above
        # This prevents double-release race condition
        if pool is not None:
            pool.release(self)

    def close(self, *args, **kwargs):
        """Return a channel to pool if it's possible, otherwise close it."""
        if self._is_releasing:
            return

        pool = self.channel_pool
        if pool is None:
            super().close(*args, **kwargs)
            return

        # Detach channel from pool before releasing
        # this prevents double-releasing on re-entrant calls
        # when pool.release() might call close_resource() -> super().close() -> events -> close() again
        self._channel_pool = None
        self._is_releasing = True
        try:
            pool.release(self)
        finally:
            self._is_releasing = False

    def force_close(self, *args, **kwargs):
        """Force close connection without pool interaction.
        Behavior like common Channel.close()
        """
        super().close(*args, **kwargs)

    def release(self, close_unbound: bool = False):
        # ChannelPool replace this method by own
        if close_unbound:
            self.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Return channel to ChannelPool, if it's acquired before, otherwise it will be closed."""
        self.release()

    def _basic_publish(
        self,
        msg,
        exchange="",
        routing_key="",
        mandatory=False,
        immediate=False,
        timeout=None,
        confirm_timeout=None,
        argsig="Bssbb",
    ):
        # Mirrors amqp.Channel._basic_publish, but reads through the snapshot
        # `conn`: a concurrent teardown can null self.connection mid-publish,
        # and the resulting AttributeError is not retried by kombu.
        with channel_operation(self) as conn:
            # Raw _transport (as frame_writer reads it): the `transport`
            # property force-connects when it is None (deprecated amqp
            # behavior), resurrecting the connection mid-teardown instead
            # of failing fast.
            transport = conn._transport
            if transport is None:
                raise RecoverableConnectionError("basic_publish: transport closed")

            capabilities = conn.client_properties.get("capabilities", {})
            if capabilities.get("connection.blocked", False):
                try:
                    conn.drain_events(timeout=0)
                except TimeoutError:
                    pass

            try:
                with transport.having_timeout(timeout):
                    return self.send_method(
                        spec.Basic.Publish,
                        argsig,
                        (0, exchange, routing_key, mandatory, immediate),
                        msg,
                    )
            except TimeoutError:
                raise RecoverableChannelError("basic_publish: timed out")

    basic_publish = _basic_publish

    # Wrappers that route every channel method touching self.connection
    # through channel_operation, so concurrent teardown cannot race them.

    def basic_get(self, *args, **kwargs):
        with channel_operation(self):
            return super().basic_get(*args, **kwargs)

    def basic_ack(self, *args, **kwargs):
        with channel_operation(self):
            return super().basic_ack(*args, **kwargs)

    def basic_reject(self, *args, **kwargs):
        with channel_operation(self):
            return super().basic_reject(*args, **kwargs)

    def basic_recover_async(self, *args, **kwargs):
        with channel_operation(self):
            return super().basic_recover_async(*args, **kwargs)

    def basic_recover(self, *args, **kwargs):
        with channel_operation(self):
            return super().basic_recover(*args, **kwargs)

    def basic_qos(self, *args, **kwargs):
        with channel_operation(self):
            return super().basic_qos(*args, **kwargs)

    def basic_consume(self, *args, **kwargs):
        with channel_operation(self):
            return super().basic_consume(*args, **kwargs)

    def basic_cancel(self, *args, **kwargs):
        with channel_operation(self):
            return super().basic_cancel(*args, **kwargs)

    def queue_declare(self, *args, **kwargs):
        with channel_operation(self):
            return super().queue_declare(*args, **kwargs)

    def queue_bind(self, *args, **kwargs):
        with channel_operation(self):
            return super().queue_bind(*args, **kwargs)

    def queue_unbind(self, *args, **kwargs):
        with channel_operation(self):
            return super().queue_unbind(*args, **kwargs)

    def queue_purge(self, *args, **kwargs):
        with channel_operation(self):
            return super().queue_purge(*args, **kwargs)

    def queue_delete(self, *args, **kwargs):
        with channel_operation(self):
            return super().queue_delete(*args, **kwargs)

    def exchange_declare(self, *args, **kwargs):
        with channel_operation(self):
            return super().exchange_declare(*args, **kwargs)

    def exchange_delete(self, *args, **kwargs):
        with channel_operation(self):
            return super().exchange_delete(*args, **kwargs)

    def exchange_bind(self, *args, **kwargs):
        with channel_operation(self):
            return super().exchange_bind(*args, **kwargs)

    def exchange_unbind(self, *args, **kwargs):
        with channel_operation(self):
            return super().exchange_unbind(*args, **kwargs)

    def confirm_select(self, *args, **kwargs):
        with channel_operation(self):
            return super().confirm_select(*args, **kwargs)

    def tx_select(self, *args, **kwargs):
        with channel_operation(self):
            return super().tx_select(*args, **kwargs)

    def tx_commit(self, *args, **kwargs):
        with channel_operation(self):
            return super().tx_commit(*args, **kwargs)

    def tx_rollback(self, *args, **kwargs):
        with channel_operation(self):
            return super().tx_rollback(*args, **kwargs)

    def flow(self, *args, **kwargs):
        with channel_operation(self):
            return super().flow(*args, **kwargs)


class DrainGuard:
    _drain_exc: Exception | None

    def __init__(self):
        cond_lock = threading.RLock()
        check_lock = threading.RLock()

        if DEBUG:
            cond_lock = LoggingLock(cond_lock, "DrainGuard-ConditionRLock")
            check_lock = LoggingLock(threading.RLock(), "DrainGuard-CheckRLock")

        self._drain_cond = threading.Condition(lock=cond_lock)
        self._drain_check_lock = check_lock
        self._drain_is_active_by = None
        self._drain_exc = None

    def is_drain_active(self):
        return self._drain_is_active_by is not None

    def start_drain(self):
        ctx = contextlib.ExitStack()
        if self._drain_is_active_by is None:
            # optimization: require lock only when race is possible
            # prevent `wait_drain_finished` exiting before drain really started
            # It's not important cause `drain_events` calls while inner `promise` obj not ready
            # but for correct thread-safe implementation we did it here
            # !!
            # That's mean `self._drain_is_active_by = ...` operation should be ALWAYS last in this function
            # to prevent race condition
            # (_drain_check_lock not acquired, but code below this lock still executed)
            ctx.enter_context(self._drain_cond)

        with ctx:
            acquired = self._drain_check_lock.acquire(blocking=False)
            if not acquired:
                return False

            assert self._drain_is_active_by is None, (
                "Drain already active; same thread cannot start drain twice"
            )
            self._drain_exc = None
            self._drain_is_active_by = threading.get_ident()

        return True

    def finish_drain(self, exc: Exception | None = None):
        caller = threading.get_ident()
        assert self._drain_is_active_by is not None, "Drain must be started"
        assert self._drain_is_active_by == caller, (
            "You can not finish drain started by other thread"
        )
        with self._drain_cond:
            self._drain_exc = exc
            self._drain_is_active_by = None
            self._drain_cond.notify_all()
            self._drain_check_lock.release()

    def wait_drain_finished(self, timeout=None):
        """Waits until the drain process has completed or until the specified timeout elapses.

        This method blocks execution while waiting for a drain operation to finish. It
        also ensures the caller is not its own blocker, preventing potential deadlocks.
        If the drain process raises an exception, that exception will be re-raised by
        this method.

        :param timeout: The time, in seconds, to wait for the drain to finish. If None,
            it waits until the drain process is complete regardless of duration.
        :type timeout: float or None
        :raises Exception: If an exception occurs during the drain process, it is
            re-raised by this method.
        """
        caller = threading.get_ident()
        assert self._drain_is_active_by != caller, "You can not wait your own; deadlock detected"
        with self._drain_cond:
            if self.is_drain_active():
                #  Important: wait_drain_finished(timeout=...) does NOT raise exception on timeout.
                #  This differs from drain_events(timeout=...) which expects socket.timeout.
                #  Reason: socket.timeout means "socket is alive, but no data" - concrete socket state.
                #  But wait_drain_finished() doesn't know socket state (only waits for another thread),
                #  so raising TimeoutError would mislead upper layers about actual socket condition.
                self._drain_cond.wait(timeout=timeout)

                if self._drain_exc is not None:
                    raise self._drain_exc


CHANNEL_TEARDOWN_WAIT_S: float = 0.5


class ChannelCoordinator:
    """Counts active operations per channel — operations that entered a critical
    section (enter_operation) but have not left it yet (exit_operation) — so
    begin_teardown() can wait for them to drain before self.connection is
    nulled; operations started after teardown is marked are rejected.

    Mark and count share one lock, so an operation racing teardown is reliably
    rejected rather than slipping in.
    """

    def __init__(self, teardown_wait_s: float = CHANNEL_TEARDOWN_WAIT_S):
        self._cond = threading.Condition(lock=threading.RLock())
        self._active_operations: int = 0
        self._marked_for_teardown: bool = False
        self._teardown_wait_s = teardown_wait_s

    @property
    def active_operations(self) -> int:
        """Number of operations currently between enter_operation and
        exit_operation. Diagnostics only: stale the moment the lock releases.
        """
        with self._cond:
            return self._active_operations

    @property
    def marked_for_teardown(self) -> bool:
        """Diagnostics only. The value is stale the moment the lock releases."""
        with self._cond:
            return self._marked_for_teardown

    def enter_operation(self) -> None:
        with self._cond:
            if self._marked_for_teardown:
                raise RecoverableConnectionError("channel teardown in progress")
            self._active_operations += 1

    def exit_operation(self) -> None:
        with self._cond:
            self._active_operations -= 1
            if self._active_operations == 0 and self._marked_for_teardown:
                self._cond.notify_all()

    def begin_teardown(self) -> bool:
        """Mark teardown and wait until active_operations reaches 0. Return True
        if it drained within the timeout (or was already 0, or teardown was
        already marked), False if the timeout expired with operations still
        active.

        A second caller, arriving after teardown is already marked, returns True
        at once instead of waiting on a drain the first caller already owns.
        """
        with self._cond:
            if self._marked_for_teardown:
                return True
            self._marked_for_teardown = True
            return self._cond.wait_for(
                lambda: self._active_operations == 0,
                timeout=self._teardown_wait_s,
            )


class ChannelOperation:
    """Critical section over channel.connection: yields the connection read
    once, and the reference stays valid for the whole block — teardown waits
    for active operations.

    A plain class, not @contextmanager: no generator overhead on every publish.
    """

    __slots__ = ("_channel", "_coord")

    def __init__(self, channel: ThreadSafeChannel):
        self._channel: ThreadSafeChannel = channel
        self._coord: ChannelCoordinator | None = None

    def __enter__(self):
        conn = self._channel.connection
        if conn is None:
            raise RecoverableConnectionError("channel already closed")
        if conn.marked_for_teardown:
            raise RecoverableConnectionError("connection teardown in progress")

        coord = self._channel._coordinator
        coord.enter_operation()
        self._coord = coord
        return conn

    def __exit__(self, exc_type, exc, tb):
        coord = self._coord
        if coord is not None:
            coord.exit_operation()
            self._coord = None
        return False


channel_operation = ChannelOperation


class ThreadSafeConnection(kombu.transport.pyamqp.Connection):
    _transport: amqp.transport.TCPTransport

    Channel = ThreadSafeChannel

    # The connection object itself is treated as channel 0
    CONNECTION_CHANNEL_ID = 0

    def __init__(self, *args, **kwargs):
        self._transport_lock = threading.RLock()
        self._connection_dispatch_lock = threading.RLock()

        self._create_channel_lock = threading.RLock()
        self._drain_guard = DrainGuard()
        self._teardown_event = threading.Event()
        self.channel_thread_bindings: collections.defaultdict[int, set[int]] = (
            collections.defaultdict(set)
        )  # thread_ident -> {channel_id, ...}
        self.channel_frame_buff = collections.defaultdict(
            collections.deque
        )  # channel_id: [frame, frame, ...]

        self.channel_thread_bindings[threading.get_ident()].add(self.CONNECTION_CHANNEL_ID)

        # Popped before super().__init__ rather than left in kwargs: passing
        # it through would just land in amqp.Connection's own unrelated
        # **kwargs sink (silently ignored there). Popping makes this
        # attribute the single source of truth for whether a drainer exists.
        self._dedicated_drainer_enabled = bool(kwargs.pop(DEDICATED_DRAINER_OPTION, False))
        self._drainer: ConnectionDrainer | None = (
            ConnectionDrainer(self) if self._dedicated_drainer_enabled else None
        )

        super().__init__(*args, **kwargs)

    def channel(self, *args, **kwargs):
        with self._create_channel_lock:
            return super().channel(*args, **kwargs)

    def _claim_channel_id(self, channel_id):
        with self._create_channel_lock:
            return super()._claim_channel_id(channel_id)

    def _get_free_channel_id(self):
        with self._create_channel_lock:
            return super()._get_free_channel_id()

    def _dispatch_channel_frames(self, channel_id) -> int:
        buff = self.channel_frame_buff.get(channel_id, ())
        processed_frames = len(buff)

        while buff:
            method_sig, payload, content = buff.popleft()
            self.channels[channel_id].dispatch_method(
                method_sig,
                payload,
                content,
            )

        return processed_frames

    def on_inbound_method(self, channel_id, method_sig, payload, content):
        if self.channels is None:
            raise amqp.exceptions.RecoverableConnectionError("Connection already closed")

        # collect all frames to late dispatch (after drain)
        self.channel_frame_buff[channel_id].append((method_sig, payload, content))

    def connect(self, *args, **kwargs):
        with self._transport_lock:
            res = super().connect(*args, **kwargs)

        if self._drainer is not None:
            # Started outside _transport_lock: in this phase the drainer only
            # ever takes a bare attribute snapshot of self._transport, never
            # this lock, so holding it here would just extend contention for
            # no safety benefit.
            self._drainer.start()

        return res

    def close(self, *args, **kwargs):
        # The outer _transport_lock must NOT wrap super().close(), in either
        # mode: close() sends Connection.Close and then blocks in
        # drain_events() waiting for CloseOk, and only the socket reader —
        # the drainer thread in drainer mode, or whichever thread wins
        # DrainGuard's start_drain() in legacy mode (possibly close() itself,
        # possibly a concurrent consumer) — can deliver it, and that reader
        # needs _transport_lock to do so. Holding the lock here would
        # deadlock — the lock owner waits for a frame the locked-out reader
        # can never deliver. Writes stay serialized regardless: the
        # frame_writer wrapper takes _transport_lock per frame.
        super().close(*args, **kwargs)

    @kombu.transport.pyamqp.Connection.frame_writer.setter
    def frame_writer(self, frame_writer):
        # frame_writer access to socket
        # make it thread-safe
        @functools.wraps(frame_writer)
        def wrapper(*args, **kwargs):
            with self._transport_lock:
                transport = self._transport

                if transport is None:
                    raise OSError("Socket closed")

                # The drainer thread's only write is the heartbeat. On a write
                # failure it must NOT reach collect(): collect() -> drainer.stop()
                # from the drainer's own thread is a self-stop (RuntimeError,
                # aborted teardown), reintroducing the "drainer never calls
                # collect()" violation on the write side. Skip collect() for the
                # drainer's own write and surface the error — _tick_heartbeat
                # routes it to _fail. Application threads (and option off) are
                # unaffected: they still collect() on a write failure.
                drainer = self._drainer
                writer_is_drainer = drainer is not None and drainer.owns_current_thread()

                if not transport.connected:
                    if not writer_is_drainer:
                        self.collect()
                    raise OSError("Socket closed")

                try:
                    res = frame_writer(*args, **kwargs)
                except (OSError, ssl.SSLError):
                    if not writer_is_drainer:
                        self.collect()
                    raise

            return res

        self._frame_writer = wrapper

    def blocking_read(self, timeout=None):
        with self._transport_lock:
            return super().blocking_read(timeout=timeout)

    def collect(self):
        if self._drainer is not None:
            # Stopped before the lock, not under it: stop() only touches its
            # own _lifecycle_lock and joins the drainer thread, never
            # _transport_lock, so ordering here is about not leaving a
            # background reader looking at _transport mid-teardown, not
            # about avoiding a deadlock.
            self._drainer.stop()

        with self._transport_lock:
            super().collect()

    def _dispatch_connection_events(self) -> int:
        """Dispatch CONNECTION_CHANNEL_ID events in a thread-safe manner.

        Only one thread can dispatch connection events at a time to prevent race conditions.
        """
        if not self.channel_frame_buff.get(self.CONNECTION_CHANNEL_ID, ()):  # inline optimization
            return 0

        acquired = self._connection_dispatch_lock.acquire(blocking=False)
        if not acquired:
            return 0

        try:
            return self._dispatch_channel_frames(self.CONNECTION_CHANNEL_ID)
        finally:
            self._connection_dispatch_lock.release()

    def _dispatch_pending_events(self) -> int:
        """Dispatch channel-specific events for the current thread."""
        processed_frames = self._dispatch_connection_events()
        me = threading.get_ident()
        my_channels = self.channel_thread_bindings[me]
        for channel_id in tuple(my_channels):
            processed_frames += self._dispatch_channel_frames(channel_id)

        return processed_frames

    def _should_skip_drain_with_pending_events(
        self, dispatched: int, timeout: float | None
    ) -> bool:
        """Check if we should return early when events already dispatched.

        EDGE-CASE (PART 2): previous drain_events(_nodispatch=True) may have buffered events
        that we just dispatched. If timeout=None, we risk infinite wait for events
        that already arrived. Return early and let kombu decide next action.
        """
        return dispatched > 0 and timeout is None

    def _drain_into_buffers(self, timeout: float) -> bool:
        """Read one AMQP method's frames into channel_frame_buff WITHOUT
        dispatching them. The dedicated drainer thread's only socket read.

        Returns True if a method was read, False if a legacy reader currently
        holds the socket (contended — uncontended in normal drainer
        operation). Raises socket.timeout when the socket is dry, and
        connection_errors / anything unexpected on a fatal error (the drainer
        routes those to _fail).

        Deliberately does NOT dispatch (unlike _execute_and_finish_drain):
        dispatching a channel-0 CloseOk/Close fires _on_close_ok/_on_close,
        which call self.collect(), which stops+joins the drainer — a self-join
        from the drainer's own thread. Leaving dispatch to app threads keeps
        teardown single-subject (README Rule 2, fix 2e2cf64) and lets a
        graceful broker Close surface as a recoverable error in the waiter.

        DrainGuard is reused as the "exactly one reader" invariant guard: in
        drainer mode the socket has a single reader, so start_drain() is
        uncontended, but the guard still mutually excludes any stray legacy
        reader from the socket rather than relying on the GIL. Lock order is
        the same as the legacy path: DrainGuard, then _transport_lock — held
        for exactly one drain_events(timeout=0), never longer.
        """
        if not self._drain_guard.start_drain():
            return False

        conn_exc = None
        try:
            with self._transport_lock:
                super().drain_events(timeout=timeout)
            return True

        except TimeoutError:
            # Dry socket. socket.timeout is a subclass of OSError (and thus of
            # connection_errors); catch it FIRST so it is never misclassified
            # as a connection failure.
            raise

        except amqp.Connection.connection_errors as exc:
            conn_exc = exc
            raise

        finally:
            self._drain_guard.finish_drain(exc=conn_exc)

    def _execute_and_finish_drain(self, timeout: float | None):
        """Execute actual drain from transport, handling all exceptions."""
        conn_exc = None

        try:
            with self._transport_lock:
                super().drain_events(timeout=timeout)

            self._dispatch_connection_events()

        except TimeoutError:
            raise

        except amqp.Connection.connection_errors as exc:
            conn_exc = exc
            raise

        except Exception:
            logger.critical("Unexpected error occurred during drain_events() calling:")
            raise

        finally:
            self._drain_guard.finish_drain(exc=conn_exc)

    def drain_events(self, timeout=None, _nodispatch=False):
        """Drains events from the transport and dispatches them if applicable.
        Called each time when we expect a response from the broker or any other reaction.

        :param timeout: Maximum time to wait for events to be drained. If None, wait indefinitely.
        :type timeout: Optional[float]
        :param _nodispatch: (internal only parameter) If True, events will not be dispatched after being drained.
        :type _nodispatch: bool
        :return: None
        """
        # When all threads go here only one really drain events,
        # because this action independent of caller.
        # All events will be dispatched to their channels

        drainer = self._drainer
        if drainer is not None and drainer.should_own_reads:
            # Dedicated-drainer mode: the drainer thread is the single socket
            # reader. This thread never reads here — it waits for the drainer
            # to pump frames, then dispatches from the buffer itself (README
            # Rule 2: frames dispatched by owner threads, including the
            # channel-0 Close that triggers teardown).
            #
            # Capture the generation BEFORE dispatching: a frame the drainer
            # pumps between this capture and wait_activity() still advances the
            # generation, so the wait returns at once instead of missing it
            # (lost-wakeup / TOCTOU on the buffer).
            since = drainer.generation

            # Channel-0 control frames (Connection.Close/Blocked/CloseOk) are
            # dispatched on BOTH paths, including _nodispatch. The drainer only
            # buffers frames; if a health check (connected -> drain_events(0,
            # _nodispatch=True)) skipped connection-level dispatch, a graceful
            # broker Close the drainer already buffered would never surface and
            # `connected` would report a dead connection as alive. This mirrors
            # the legacy path, where _execute_and_finish_drain dispatches
            # channel 0 regardless of _nodispatch. _nodispatch suppresses only
            # application-channel delivery, never connection control.
            if _nodispatch:
                self._dispatch_connection_events()
            else:
                dispatched = self._dispatch_pending_events()
                if self._should_skip_drain_with_pending_events(dispatched, timeout):
                    return

            drainer.wait_activity(timeout, since_generation=since)

            if _nodispatch:
                self._dispatch_connection_events()
            else:
                self._dispatch_pending_events()
            return

        if not _nodispatch:
            # Dispatch events buffered by previous drain_events(_nodispatch=True) calls
            dispatched = self._dispatch_pending_events()
            if self._should_skip_drain_with_pending_events(dispatched, timeout):
                return

        started = self._drain_guard.start_drain()

        if not started:
            self._drain_guard.wait_drain_finished(timeout=timeout)
        else:
            self._execute_and_finish_drain(timeout)

        if not _nodispatch:
            # Dispatch events received during this drain_events() call
            self._dispatch_pending_events()

    @property
    def marked_for_teardown(self) -> bool:
        """True once this connection has been marked for teardown. Publishers
        read it to fail instead of touching a connection under destruction.
        """
        return self._teardown_event.is_set()

    def mark_for_teardown(self) -> None:
        """Mark this connection for teardown. One-way and irreversible: the flag
        stays set until the connection is destroyed.
        """
        self._teardown_event.set()


class LoggingLock:
    def __init__(self, lock, name=None, threshold=0.01):
        if hasattr(lock, "_release_save"):
            self._release_save = lock._release_save
        if hasattr(lock, "_acquire_restore"):
            self._acquire_restore = lock._acquire_restore
        if hasattr(lock, "_is_owned"):
            self._is_owned = lock._is_owned

        self.owner = None
        self.lock = lock
        self.name = name or repr(lock)
        self.threshold = threshold
        self._acquired_at = 0

        logger.info("Lock(%s): created by %s", self.name, threading.get_ident())

    def acquire(self, blocking=True, timeout=-1):
        start = time.monotonic()
        if not self.threshold:
            logger.info("Lock(%s): try to acquire", self.name)

        res = self.lock.acquire(blocking, timeout)
        self.owner = threading.get_ident()

        acquired = time.monotonic()
        stuck = ""
        if acquired - start > self.threshold:
            stuck = "STUCK"

        logger.info("Lock(%s): acquired; %.2fs" + stuck, self.name, acquired - start)

        self._acquired_at = acquired

        return res

    def release(self):
        res = self.lock.release()
        logger.info("Lock(%s): released", self.name)
        return res

    def __enter__(self):
        """Acquire lock."""
        start = time.monotonic()
        logger.info("Lock(%s): try to acquire", self.name)

        res = self.lock.__enter__()

        acquired = time.monotonic()
        stuck = ""
        if acquired - start > self.threshold:
            stuck = "STUCK"
        logger.info("Lock(%s): acquired; %.2fs" + stuck, self.name, acquired - start)

        return res

    def __exit__(self, *args, **kwargs):
        """Release lock."""
        try:
            return self.lock.__exit__(*args, **kwargs)
        finally:
            logger.info("Lock(%s): released", self.name)


class KombuConnection(kombu.Connection):
    """Thread-safe variant of kombu.Connection."""

    # TODO: ensure only one thread make action (add threading.Condition) for:
    #   _ensure_connection, _close, collect

    _default_channel: "ThreadSafeChannel | None" = None

    def __init__(self, *args, default_channel_pool_size=100, **kwargs):
        transport_lock = threading.RLock()

        if DEBUG:
            transport_lock = LoggingLock(transport_lock, name="TransportLock")

        self._transport_lock = transport_lock
        self._teardown_lock = threading.Lock()
        self._default_channel_pool: ThreadSafeChannelPool | None = None
        self._default_channel_pool_size = default_channel_pool_size
        super().__init__(*args, **kwargs)

    @classmethod
    def from_kombu_connection(cls, connection: kombu.Connection, **kwargs) -> "KombuConnection":
        """Clone kombu.Connection as new KombuConnection instance."""
        # implementation copied from `kombu.Connection.clone()` method
        return cls(**dict(connection._info(resolve=False)), **kwargs)

    def Producer(self, channel=None, *args, **kwargs) -> kombu.Producer:
        from .producer import AutoChannelReleaseProducer

        return AutoChannelReleaseProducer(channel or self, *args, **kwargs)

    def SimpleQueue(
        self,
        name: str,
        no_ack: "bool | None" = None,
        queue_opts: "dict | None" = None,
        queue_args: "dict | None" = None,
        exchange_opts: "dict | None" = None,
        channel: "kombu.Connection | Channel" = None,
        **kwargs,
    ):
        """Thread-safe variant of SimpleQueue."""
        from .simple import SimpleQueue

        return SimpleQueue(
            channel or self,
            name,
            no_ack,
            queue_opts,
            queue_args,
            exchange_opts,
            **kwargs,
        )

    def SimpleBuffer(
        self,
        name: str,
        no_ack: "bool | None" = None,
        queue_opts: "dict | None" = None,
        queue_args: "dict | None" = None,
        exchange_opts: "dict | None" = None,
        channel: "kombu.Connection | Channel" = None,
        **kwargs,
    ):
        from .simple import SimpleBuffer

        return SimpleBuffer(
            channel or self,
            name,
            no_ack,
            queue_opts,
            queue_args,
            exchange_opts,
            **kwargs,
        )

    def get_transport_cls(self):
        transport_cls = super().get_transport_cls()

        if isinstance(transport_cls, (SharedPyamqpTransport, SharedPyamqpSSLTransport)):
            return transport_cls

        if transport_cls is kombu.transport.pyamqp.SSLTransport:
            transport_cls = SharedPyamqpSSLTransport

        elif transport_cls is kombu.transport.pyamqp.Transport:
            transport_cls = SharedPyamqpTransport

        else:
            raise RuntimeError(
                f"Unsupported transport type: {transport_cls}; Only py-amqp supported"
            )

        return transport_cls

    @property
    def transport(self):
        if self._transport is None:
            with self._transport_lock:
                if self._transport is None:
                    self._transport = self.create_transport()
        return self._transport

    @property
    def connected(self):
        """Check connection.

        Except basic implementation we make real check: try read from socket
        """
        with self._transport_lock:
            connected = (
                not self._closed
                and self._connection is not None
                and self.transport.verify_connection(self._connection)
            )
            if connected:
                try:
                    # SIDE EFFECT (PART 1):
                    # Kombu typically calls `drain_events()` only after transport actions (e.g., `send_method()`).
                    # We use it here strictly to check socket liveness (socket.timeout confirms the socket is readable).
                    #
                    # However, if we use the default `_nodispatch=False`, we might silently read and process frames
                    # that the calling context expects. Since Kombu often checks this property before calling
                    # `drain_events()`, consuming the event here could cause the subsequent `drain_events(timeout=None)`
                    # to wait indefinitely for an event that was already handled.
                    #
                    # This side effect is the origin of EDGE-CASE (PART 2). See `drain_events()` comments for details.

                    self._connection.drain_events(timeout=0, _nodispatch=True)
                except TimeoutError:
                    pass
                except self.connection_errors:
                    connected = False

        return connected

    @property
    def default_channel(self) -> ThreadSafeChannel:
        channel = self._default_channel

        if channel is None or not channel.is_usable():
            with self._transport_lock:
                channel = self._default_channel
                if channel is None or not channel.is_usable():
                    # do not acquire channel from pool
                    # this channel will be never released
                    # and default_channel can be reused by any thread
                    # guarantee pool channels not used by any other thread when acquired
                    conn_opts = self._extract_failover_opts()
                    self._ensure_connection(**conn_opts)

                    channel = self.channel()
                    self._default_channel = channel

        if channel is None:
            # mypy typeguard
            raise RuntimeError("Channel was not initialized properly")

        return channel

    @property
    def default_channel_pool(self) -> ThreadSafeChannelPool:
        pool = self._default_channel_pool
        if pool is None or pool.closed:
            with self._transport_lock:
                pool = self._default_channel_pool
                if pool is None or pool.closed:
                    conn_opts = self._extract_failover_opts()
                    self._ensure_connection(**conn_opts)

                    pool = self.ChannelPool(limit=self._default_channel_pool_size)
                    self._default_channel_pool = pool

        if pool is None:
            # mypy typeguard
            raise RuntimeError("Channel pool was not initialized properly")

        return pool

    def ChannelPool(self, limit=None, **kwargs):  # noqa: N802
        return ThreadSafeChannelPool(self, limit, **kwargs)

    def _do_close_self(self):
        pool = self._default_channel_pool
        if pool is not None:
            pool.force_close_all()
        self._default_channel_pool = None
        super()._do_close_self()
        self._default_channel = None

    def _close(self):
        with self._transport_lock:
            super()._close()

    def _ensure_connection(self, *args, **kwargs):
        # TODO: respect `_extract_failover_opts()`
        with self._transport_lock:
            return super()._ensure_connection(*args, **kwargs)

    def ensure(
        self,
        obj,
        fun,
        errback=None,
        max_retries=None,
        interval_start=1,
        interval_step=1,
        interval_max=1,
        on_revive=None,
        retry_errors=None,
    ):
        """Fork of kombu.Connection.ensure() with one behavioral change:
        collect() only the connection the failing attempt actually saw.

        Upstream collects unconditionally on conn_errors, so a thread holding
        a stale error (its connection was already replaced by another thread's
        reconnect) tore down the live replacement — reconnect ping-pong.

        Body copied verbatim from kombu 5.6.1 except the snapshot and the
        conditional collect.
        """
        if retry_errors is None:
            retry_errors = ()

        def _ensured(*args, **kwargs):
            got_connection = 0
            conn_errors = self.recoverable_connection_errors
            chan_errors = self.recoverable_channel_errors
            has_modern_errors = hasattr(
                self.transport,
                "recoverable_connection_errors",
            )
            with self._reraise_as_library_errors():
                for retries in count(0):  # for infinity
                    seen_connection = self._connection
                    try:
                        return fun(*args, **kwargs)
                    except retry_errors as exc:
                        if max_retries is not None and retries >= max_retries:
                            raise
                        self._debug("ensure retry policy error: %r", exc, exc_info=1)
                    except conn_errors as exc:
                        if got_connection and not has_modern_errors:
                            # transport can not distinguish between
                            # recoverable/irrecoverable errors, so we propagate
                            # the error if it persists after a new connection
                            # was successfully established.
                            raise
                        if max_retries is not None and retries >= max_retries:
                            raise
                        self._debug("ensure connection error: %r", exc, exc_info=1)
                        # Upstream collects unconditionally; we skip when the
                        # connection was already replaced — a stale error must
                        # not tear down the live replacement. Unlocked check is
                        # safe: _connection never returns to an old object.
                        if seen_connection is not None and self._connection is seen_connection:
                            with self._transport_lock:
                                if self._connection is seen_connection:
                                    self.collect()
                        errback and errback(exc, 0)
                        remaining_retries = None
                        if max_retries is not None:
                            remaining_retries = max(max_retries - retries, 1)
                        self._ensure_connection(
                            errback,
                            remaining_retries,
                            interval_start,
                            interval_step,
                            interval_max,
                            reraise_as_library_errors=False,
                        )
                        channel = self.default_channel
                        obj.revive(channel)
                        if on_revive:
                            on_revive(channel)
                        got_connection += 1
                    except chan_errors as exc:
                        if max_retries is not None and retries > max_retries:
                            raise
                        self._debug("ensure channel error: %r", exc, exc_info=1)
                        errback and errback(exc, 0)

        _ensured.__name__ = f"{fun.__name__}(ensured)"
        _ensured.__doc__ = fun.__doc__
        _ensured.__module__ = fun.__module__
        return _ensured

    def collect(self, *args, **kwargs):
        """Tear the current connection down. Does not reconnect — that is
        _ensure_connection's job, which skips work when self.connected.
        """
        if not self._teardown_lock.acquire(blocking=False):
            # Connection teardown is already in progress by another thread
            return
        try:
            with self._transport_lock:
                if self._connection is None:
                    return
                self._connection.mark_for_teardown()

                # Close pool channels while the transport is still alive, else
                # they leak: rabbit keeps them open (no close frame sent) and we
                # lose the references. close_pool=False keeps the pool usable on
                # the next transport.
                pool = self._default_channel_pool
                if pool is not None and not pool.closed:
                    pool.force_close_all(close_pool=False)
                super().collect(*args, **kwargs)
        finally:
            self._teardown_lock.release()

    def _connection_factory(self):
        with self._transport_lock:
            # kombu reassigns self._connection here without calling
            # collect()/close() on the connection being replaced, which happens
            # on the reconnect paths that skip our collect() (ensure_connection,
            # lazy default_channel/pool/connection restore). The outgoing
            # drainer would then orphan and self-terminate, but its self-pipe
            # fds close only from stop() — leaking 2 fds per reconnect. Snapshot
            # and stop it here, before building the replacement.
            #
            # intentional=False: this is a failure-driven replacement, not a
            # user close(), so a consumer still parked on the old connection
            # gets a recoverable error (ensure() reconnects), never
            # ConnectionClosedIntentionally. old may be None (first connect) or
            # have no drainer (option off) — getattr covers both.
            #
            # Lock order: this holds KombuConnection._transport_lock, then
            # stop() takes the drainer's _lifecycle_lock (and briefly its
            # _activity_cond) and joins the old drainer thread. That thread
            # never takes KombuConnection._transport_lock (it uses the OLD
            # ThreadSafeConnection's own _transport_lock, a different object),
            # so there is no lock-order inversion. Stopping before super() also
            # collapses the old/new drainer coexistence window to zero.
            old = self._connection
            old_drainer = getattr(old, "_drainer", None)
            if old_drainer is not None:
                old_drainer.stop(intentional=False)

            connection = super()._connection_factory()
            return connection

    def revive(self, new_channel: ThreadSafeChannel):
        # Nothing to do here
        # Connection revives through _ensure_connection,
        #   and this method called in Connection.ensure() with self.default_channel
        #   new_channel is always self.default_channel.
        # IDK, why you try to revive Connection by already opened channel.
        # If you have opened a channel, your Connection is already revived.
        super().revive(new_channel)

    def channel(self):
        with self._transport_lock:
            return super().channel()


class SharedPyamqpTransport(kombu.transport.pyamqp.Transport):
    Connection = ThreadSafeConnection


class SharedPyamqpSSLTransport(kombu.transport.pyamqp.SSLTransport):
    Connection = ThreadSafeConnection


def monkeypatch_pyamqp_transport():
    """Replace default implementation by thread-safe."""
    kombu.transport.pyamqp.Transport.Connection = ThreadSafeConnection
    kombu.transport.pyamqp.SSLTransport.Connection = ThreadSafeConnection


def add_shared_amqp_transport():
    """Register threadsafe transports in kombu.

    shared+pyamqp, shared+amqp, shared+amqps
    """
    kombu.transport.TRANSPORT_ALIASES["shared+pyamqp"] = (
        f"{SharedPyamqpTransport.__module__}:{SharedPyamqpTransport.__name__}"
    )
    kombu.transport.TRANSPORT_ALIASES["shared+amqp"] = (
        f"{SharedPyamqpTransport.__module__}:{SharedPyamqpTransport.__name__}"
    )
    kombu.transport.TRANSPORT_ALIASES["shared+amqps"] = (
        f"{SharedPyamqpSSLTransport.__module__}:{SharedPyamqpSSLTransport.__name__}"
    )
