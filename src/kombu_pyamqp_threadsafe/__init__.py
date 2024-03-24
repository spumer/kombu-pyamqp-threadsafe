import collections
import contextlib
import functools
import logging
import socket
import threading

import amqp
import kombu
import kombu.resource
import kombu.simple
import kombu.connection
import kombu.transport
import kombu.transport.pyamqp
from amqp import RecoverableConnectionError

logger = logging.getLogger(__name__)


class ChannelPool(kombu.connection.ChannelPool):
    def __init__(self, connection, limit=None, **kwargs):
        assert isinstance(connection, ThreadSafeConnection)
        super().__init__(connection, limit=limit, **kwargs)

    def acquire(self, *args, **kwargs):
        channel: ThreadSafeChannel = super().acquire(*args, **kwargs)
        channel.change_owner(threading.get_ident())
        return channel


class ThreadSafeChannel(kombu.transport.pyamqp.Channel):
    connection: "ThreadSafeConnection"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner_ident = threading.get_ident()
        self.connection.channel_thread_bindings[self._owner_ident].append(self.channel_id)

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
                and "AttributeError: 'NoneType' object has no attribute 'drain_events'" == str(exc)
            ):
                raise RecoverableConnectionError("connection already closed")

    def collect(self):
        conn = self.connection
        channel_frame_buff = conn.channel_frame_buff.pop(self.channel_id, ())
        if channel_frame_buff:
            logger.warning(
                "No drained events after close (%s pending events)", len(channel_frame_buff)
            )

        bindings = conn.channel_thread_bindings.get(self._owner_ident) or []
        try:
            bindings.remove(self.channel_id)
        except ValueError:
            pass

        super().collect()


class DrainGuard:
    def __init__(self):
        self._drain_cond = threading.Condition()
        self._drain_is_active_by = None
        self._drain_check_lock = threading.RLock()

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
                    raise IOError("Socket closed")
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
        # When all threads go here only one really drain events
        # Because this action independent of caller, all events will be dispatched to their channels

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


class KombuConnection(kombu.Connection):
    """Thread-safe variant of kombu.Connection"""

    def __init__(self, *args, default_channel_pool_size=100, **kwargs):
        self._transport_lock = threading.RLock()
        self._default_channel_pool: kombu.resource.Resource | None = None
        self._default_channel_pool_size = default_channel_pool_size
        super().__init__(*args, **kwargs)

    @property
    def transport(self):
        if self._transport is None:
            with self._transport_lock:
                if self._transport is None:
                    self._transport = self.create_transport()
        return self._transport

    @property
    def connected(self):
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
    def default_channel_pool(self):
        pool = self._default_channel_pool
        if pool is None:
            with self._transport_lock:
                pool = self._default_channel_pool
                if pool is None:
                    pool = self.ChannelPool(limit=self._default_channel_pool_size)
                    self._default_channel_pool = pool
        return pool

    def ChannelPool(self, limit=None, **kwargs):
        return ChannelPool(self, limit, **kwargs)

    def _do_close_self(self):
        pool = self._default_channel_pool
        if pool is not None:
            pool.force_close_all()
        self._default_channel_pool = None
        super()._do_close_self()

    def _close(self):
        with self._transport_lock:
            super()._close()

    def _ensure_connection(self, *args, **kwargs):
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
    """Replace default implementation by thread-safe
    """
    kombu.transport.pyamqp.Transport.Connection = ThreadSafeConnection
    kombu.transport.pyamqp.SSLTransport.Connection = ThreadSafeConnection


def add_shared_amqp_transport():
    """Register threadsafe transports in kombu

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
