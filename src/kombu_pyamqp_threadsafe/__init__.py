"""Threadsafe implementation of pyamqp transport for kombu."""

import collections
import contextlib
import functools
import logging
import os
import socket
import threading
import time
import weakref

import amqp
import kombu
import kombu.connection
import kombu.resource
import kombu.simple
import kombu.transport
import kombu.transport.pyamqp
from amqp import RecoverableConnectionError

logger = logging.getLogger(__name__)

DEBUG = os.getenv("KOMBU_PYAMQP_THREADSAFE_DEBUG", "0").lower() in ("1", "true", "t", "y", "yes")


class ThreadSafeChannelPool(kombu.connection.ChannelPool):
    def __init__(self, connection, limit=None, **kwargs):
        assert isinstance(
            connection, KombuConnection
        ), f"Expect {KombuConnection.__qualname__}, given: {type(connection)}"
        super().__init__(connection, limit=limit, **kwargs)

    def setup(self):
        # do not pre-create channels like parent implementation
        pass

    def acquire(self, block: bool = False, timeout: "float | None" = None) -> "ThreadSafeChannel":
        channel: ThreadSafeChannel = super().acquire(block=block, timeout=timeout)
        channel.change_owner(threading.get_ident())
        return channel

    def prepare(self, channel: "ThreadSafeChannel") -> "ThreadSafeChannel":
        channel = super().prepare(channel)
        channel._bind_to_pool(self)
        return channel

    def release(self, resource: "ThreadSafeChannel"):
        if resource.connection is None or not resource.is_open or resource.is_closing:
            if self.limit:
                self._dirty.discard(resource)
            return

        super().release(resource)


ChannelPool = ThreadSafeChannelPool


class ThreadSafeChannel(kombu.transport.pyamqp.Channel):
    connection: "ThreadSafeConnection"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner_ident = threading.get_ident()
        self._channel_pool: weakref.ReferenceType[ThreadSafeChannel] | None = None
        self.connection.channel_thread_bindings[self._owner_ident].append(self.channel_id)

    def _bind_to_pool(self, channel_pool: "ThreadSafeChannelPool"):
        self._channel_pool = weakref.ref(channel_pool)

    @property
    def channel_pool(self) -> "ThreadSafeChannelPool | None":
        if self._channel_pool is None:
            return None
        return self._channel_pool()

    def change_owner(self, new_owner):
        prev_owner = self._owner_ident
        self._owner_ident = new_owner
        bindings = self.connection.channel_thread_bindings
        bindings[prev_owner].remove(self.channel_id)
        bindings[new_owner].append(self.channel_id)

    def wait(self, *args, **kwargs):
        thread_ident = threading.get_ident()
        # workaround for case when channel used in another thread, e.g. through ChannelPool
        if thread_ident != self._owner_ident:
            self.change_owner(thread_ident)

        try:
            return super().wait(*args, **kwargs)
        except AttributeError as exc:
            if (
                not self.connection
                and str(exc) == "AttributeError: 'NoneType' object has no attribute 'drain_events'"
            ):
                raise RecoverableConnectionError("connection already closed") from None

    def collect(self):
        conn = self.connection
        channel_frame_buff = conn.channel_frame_buff.pop(self.channel_id, ())
        if channel_frame_buff:
            logger.warning(
                "No drained events after close (%s pending events)", len(channel_frame_buff)
            )

        bindings = conn.channel_thread_bindings.get(self._owner_ident) or []
        with contextlib.suppress(ValueError):
            bindings.remove(self.channel_id)

        super().collect()

    def close(self, *args, **kwargs):
        """Return a channel to pool if it's possible, otherwise close it"""
        pool = self.channel_pool
        if pool is not None:
            pool.release(self)
        else:
            super().close(*args, **kwargs)

    def force_close(self, *args, **kwargs):
        """Force close connection without pool interaction.
        Behavior like common Channel.close()
        """
        super().close(*args, **kwargs)

    def release(self):
        # ChannelPool replace this method by own
        self.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Return channel to ChannelPool, if it's acquired before, otherwise it will be closed."""
        self.release()


class DrainGuard:
    def __init__(self):
        cond_lock = threading.RLock()
        check_lock = threading.RLock()

        if DEBUG:
            cond_lock = LoggingLock(cond_lock, "DrainGuard-ConditionRLock")
            check_lock = LoggingLock(threading.RLock(), "DrainGuard-CheckRLock")

        self._drain_cond = threading.Condition(lock=cond_lock)
        self._drain_check_lock = check_lock
        self._drain_is_active_by = None

    def is_drain_active(self):
        return self._drain_is_active_by is not None

    def start_drain(self):
        ctx = contextlib.ExitStack()
        if self._drain_is_active_by is None:
            # optimization: require lock only when race is possible
            # prevent `wait_drain_finished` exiting before drain really started
            # It's not important cause `drain_events` calls while inner `promise` obj not ready
            # but for correct thread-safe implementation we did it here
            ctx.enter_context(self._drain_cond)

        with ctx:
            acquired = self._drain_check_lock.acquire(blocking=False)
            if not acquired:
                return False

            assert self._drain_is_active_by is None
            self._drain_is_active_by = threading.get_ident()

        return True

    def finish_drain(self):
        caller = threading.get_ident()
        assert self._drain_is_active_by is not None, "Drain must be started"
        assert (
            self._drain_is_active_by == caller
        ), "You can not finish drain started by other thread"
        with self._drain_cond:
            self._drain_is_active_by = None
            self._drain_cond.notify_all()
            self._drain_check_lock.release()

    def wait_drain_finished(self, timeout=None):
        caller = threading.get_ident()
        assert self._drain_is_active_by != caller, "You can not wait your own; deadlock detected"
        with self._drain_cond:
            if self.is_drain_active():
                self._drain_cond.wait(timeout=timeout)


class ThreadSafeConnection(kombu.transport.pyamqp.Connection):
    Channel = ThreadSafeChannel

    # The connection object itself is treated as channel 0
    CONNECTION_CHANNEL_ID = 0

    def __init__(self, *args, **kwargs):
        self._transport_lock = threading.RLock()

        self._create_channel_lock = threading.RLock()
        self._drain_guard = DrainGuard()
        self.channel_thread_bindings = collections.defaultdict(
            list
        )  # thread_ident -> [channel_id, ...]
        self.channel_frame_buff = collections.defaultdict(
            collections.deque
        )  # channel_id: [frame, frame, ...]

        self.channel_thread_bindings[threading.get_ident()].append(self.CONNECTION_CHANNEL_ID)
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

    def _dispatch_channel_frames(self, channel_id):
        buff = self.channel_frame_buff.get(channel_id, ())

        while buff:
            method_sig, payload, content = buff.popleft()
            self.channels[channel_id].dispatch_method(
                method_sig,
                payload,
                content,
            )

    def on_inbound_method(self, channel_id, method_sig, payload, content):
        if self.channels is None:
            raise amqp.exceptions.RecoverableConnectionError("Connection already closed")

        # collect all frames to late dispatch (after drain)
        self.channel_frame_buff[channel_id].append((method_sig, payload, content))

    def connect(self, *args, **kwargs):
        with self._transport_lock:
            res = super().connect(*args, **kwargs)
        return res

    def close(self, *args, **kwargs):
        with self._transport_lock:
            super().close(*args, **kwargs)

    @kombu.transport.pyamqp.Connection.frame_writer.setter
    def frame_writer(self, frame_writer):
        # frame_writer access to socket
        # make it thread-safe
        @functools.wraps(frame_writer)
        def wrapper(*args, **kwargs):
            with self._transport_lock:
                transport = self._transport
                if transport is None or not transport.connected:
                    raise OSError("Socket closed")
                res = frame_writer(*args, **kwargs)
            return res

        self._frame_writer = wrapper

    def blocking_read(self, timeout=None):
        with self._transport_lock:
            return super().blocking_read(timeout=timeout)

    def collect(self):
        with self._transport_lock:
            super().collect()

    def drain_events(self, timeout=None):
        # When all threads go here only one really drain events,
        # because this action independent of caller.
        # All events will be dispatched to their channels

        started = self._drain_guard.start_drain()

        if not started:
            self._drain_guard.wait_drain_finished()
        else:
            try:
                with self._transport_lock:
                    super().drain_events(timeout=timeout)

            finally:
                self._drain_guard.finish_drain()

        self._dispatch_channel_frames(self.CONNECTION_CHANNEL_ID)

        me = threading.get_ident()
        my_channels = self.channel_thread_bindings[me]
        for channel_id in my_channels:
            self._dispatch_channel_frames(channel_id)


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
        self._default_channel_pool: ThreadSafeChannelPool | None = None
        self._default_channel_pool_size = default_channel_pool_size
        super().__init__(*args, **kwargs)

    @classmethod
    def from_kombu_connection(cls, connection: kombu.Connection, **kwargs) -> "KombuConnection":
        """Clone kombu.Connection as new KombuConnection instance."""
        # implementation copied from `kombu.Connection.clone()` method
        return cls(**dict(connection._info(resolve=False)), **kwargs)

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
                    self._connection.drain_events(timeout=0)
                except socket.timeout:
                    pass
                except self.connection_errors:
                    connected = False

        return connected

    @property
    def default_channel(self) -> ThreadSafeChannel:
        channel = self._default_channel

        if channel is None:
            with self._transport_lock:
                channel = self._default_channel
                if channel is None:
                    conn_opts = self._extract_failover_opts()
                    self._ensure_connection(**conn_opts)

                    channel = self.channel()
                    self._default_channel = channel

        return channel

    @property
    def default_channel_pool(self) -> ThreadSafeChannelPool:
        pool = self._default_channel_pool
        if pool is None:
            with self._transport_lock:
                pool = self._default_channel_pool
                if pool is None:
                    conn_opts = self._extract_failover_opts()
                    self._ensure_connection(**conn_opts)

                    pool = self.ChannelPool(limit=self._default_channel_pool_size)
                    self._default_channel_pool = pool
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

    def collect(self, *args, **kwargs):
        with self._transport_lock:
            super().collect(*args, **kwargs)

    def _connection_factory(self):
        with self._transport_lock:
            connection = super()._connection_factory()
            self._default_channel_pool = None
            return connection

    def revive(self, new_channel):
        with self._transport_lock:
            super().revive(new_channel)
            self._default_channel_pool = None

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
