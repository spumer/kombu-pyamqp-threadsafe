"""Dedicated drainer thread pinned 1:1 to a ThreadSafeConnection.

The drainer thread is the connection's single socket reader. It polls the
transport socket (plus a self-pipe for instant wakeup), and on readable it
pumps every available frame into the connection's channel_frame_buff WITHOUT
dispatching them, bumping an activity generation after each. Application
threads calling drain_events() do not read the socket at all in this mode;
they block in wait_activity() until the generation advances (frames arrived)
or a fatal error is recorded, then dispatch the buffered frames themselves.

Two deliberate non-dispatch decisions:
- The drainer never dispatches frames — not even channel 0. Dispatching a
  channel-0 CloseOk/Close fires _on_close_ok/_on_close, which call collect(),
  which stops and joins the drainer: from the drainer's own thread that is a
  self-join. Leaving all dispatch to app threads keeps teardown a single
  subject (README Rule 2; reconnect ping-pong fix 2e2cf64) and lets a
  graceful broker Close surface as RecoverableConnectionError in the waiting
  app thread.
- The drainer never calls collect()/reconnect. On a fatal socket error it
  records the exception, marks the connection for teardown, wakes waiters,
  and exits; the app thread that receives the error drives teardown.

Heartbeat ticking rides the same loop: on top of polling for readability, the
loop also calls conn.heartbeat_tick() at the negotiated cadence, under
_transport_lock for the call only. A missed-heartbeat ConnectionForced goes
through the same _fail path as any other fatal drain error.
"""

import logging
import os
import selectors
import threading
import time
import typing

from amqp import ConnectionForced, RecoverableConnectionError
from amqp.exceptions import IrrecoverableConnectionError

if typing.TYPE_CHECKING:
    from kombu_pyamqp_threadsafe import ThreadSafeConnection

logger = logging.getLogger(__name__)


class ConnectionClosedIntentionally(IrrecoverableConnectionError):  # noqa: N818
    """Drainer stopped because the application closed the connection on purpose.

    Raised to a drain_events waiter when the stop came from an intentional
    close()/collect()/direct stop(), as opposed to a socket failure. (No "Error"
    suffix, matching its amqp sibling ConnectionForced.)

    Base choice is deliberate. It subclasses amqp's IrrecoverableConnectionError
    so it is NOT a member of connection.recoverable_connection_errors: kombu's
    ensure()/Consumer therefore does NOT retry or reconnect on it — an
    application that closed its own connection must not have it resurrected
    underneath it. It remains an amqp.exceptions.ConnectionError, so existing
    `except amqp ...ConnectionError` blocks still catch it (note: NOT the
    builtin ConnectionError — amqp's is an AMQPError, not an OSError). A
    dedicated subclass (rather
    than raising IrrecoverableConnectionError directly) is the whole point of
    this signal: it lets callers and logs tell an intentional close apart from a
    genuine irrecoverable failure, which is exactly the distinction being added.
    """


# transport_options key read by ThreadSafeConnection.__init__. Absent or
# falsy keeps behavior identical to before this option existed.
DEDICATED_DRAINER_OPTION = "dedicated_drainer"

# Safety-net tick, not the wakeup mechanism: stop() wakes the loop instantly
# through the self-pipe below regardless of this value. It only bounds how
# quickly a transport that died without a clean stop() gets noticed. Also the
# heartbeat-check cadence ceiling: see _loop, which uses
# min(poll_tick_s, heartbeat/4) once a heartbeat is negotiated.
_DEFAULT_POLL_TICK_S = 1.0

# amqp.Connection.heartbeat_tick's own default: send a heartbeat frame at
# most once every heartbeat/rate seconds, and fail after two full intervals
# with nothing received. Passed through unchanged; not configurable here
# because nothing in this codebase has needed a different rate yet
# (Ontological Parsimony — add a knob only once something needs it).
_HEARTBEAT_TICK_RATE = 2

# Blocking read timeout for one frame, used instead of timeout=0. At timeout=0
# amqp's TCPTransport._read spins a Python continue-loop at ~100% CPU while a
# fragmented frame BODY trickles in (non-initial EAGAIN never raises), all
# while holding _transport_lock. A small NON-ZERO timeout makes that recv block
# on the socket instead (CPU idle), and a mid-frame stall past this bound
# raises socket.timeout — read_frame prepends the partial bytes back onto the
# transport buffer, so no half-frame is lost. Must stay comfortably above
# normal inter-packet gaps so a steadily-arriving frame is not chopped into
# needless retries; it only bounds how long the lock is held once a peer goes
# silent mid-frame.
_DEFAULT_READ_TIMEOUT_S = 0.1

# Bound for the drainer's heartbeat WRITE (see _tick_heartbeat). The heartbeat
# send is the drainer's only socket write, and without a timeout it is a blocking
# sock.sendall() held under _transport_lock: a peer whose TCP receive window is
# shut (not reading, kernel send buffer full) makes that sendall block for tens
# of minutes, wedging publishers and close() while the self-pipe is powerless
# (this thread is stuck in a write syscall, not in select). The default bound is
# derived from the negotiated heartbeat so the write must complete within half
# the liveness window, then clamped to [floor, ceiling]: if an 8-byte heartbeat
# frame cannot be flushed within that time the connection is effectively dead, so
# failing beats blocking. Override via the constructor (tests, tuning) — mirrors
# poll_tick_s / read_timeout_s.
_DEFAULT_WRITE_TIMEOUT_CEILING_S = 5.0
_DEFAULT_WRITE_TIMEOUT_FLOOR_S = 1.0


class ConnectionDrainer:
    """Owns the background thread for one ThreadSafeConnection.

    One instance per connection, constructed in ThreadSafeConnection.__init__
    and discarded with it: a reconnect builds a new ThreadSafeConnection and
    therefore a new ConnectionDrainer, so there is never a stale fd to
    re-register after reconnect — the old drainer simply dies with the old
    connection. Consequently this instance is not designed to be restarted
    after stop() has actually stopped it; start() raises if you try.
    """

    def __init__(
        self,
        conn: "ThreadSafeConnection",
        poll_tick_s: float = _DEFAULT_POLL_TICK_S,
        read_timeout_s: float = _DEFAULT_READ_TIMEOUT_S,
        write_timeout_s: "float | None" = None,
    ):
        self._conn = conn
        self._poll_tick_s = poll_tick_s
        self._read_timeout_s = read_timeout_s
        # None -> derive the heartbeat-write bound from the negotiated heartbeat
        # (see _resolve_write_timeout). An explicit value overrides that.
        self._write_timeout_s = write_timeout_s
        self._thread: threading.Thread | None = None
        self._pid: int | None = None
        self._closed = False

        # Serializes start()/stop(): without it, two threads racing start()
        # could both observe is_running is False and each spawn a thread for
        # the same connection.
        self._lifecycle_lock = threading.Lock()

        # Self-pipe wakeup: a bare `selector.select(timeout=tick)` on the
        # transport socket alone cannot be woken from another thread — a
        # stop() request would sit unnoticed until the next tick elapses.
        # Writing a byte here wakes select() immediately, independent of how
        # long the tick is.
        #
        # Allocated in start(), not here: a drainer that is constructed but
        # never started (a speculative connection, or an exception in
        # ThreadSafeConnection.__init__ before connect) must not hold two fds
        # it will never close. The pipe is owned as a symmetric start()/stop()
        # pair, not by the constructor (Pattern 8 start-timing).
        self._wakeup_r: int | None = None
        self._wakeup_w: int | None = None

        # Activity signalling. The drainer bumps _generation after each frame
        # it pumps and notifies; app threads block here until the generation
        # moves past the value they captured (see wait_activity). A fatal
        # socket error is recorded in _exc and re-raised to every waiter.
        #
        # Invariant guarded: without a monotonically-rising generation an app
        # thread could miss a wake (lost-wakeup / TOCTOU on the buffer) — it
        # would wait for "the next notify" while the frame it wanted already
        # arrived just before it started waiting. Capturing the generation
        # BEFORE dispatching, then waiting for it to change, closes that hole.
        #
        # _terminated is the terminal signal: it turns True once the drainer
        # thread has left _run for ANY reason (stop, clean self-termination,
        # OSError in select, or an unexpected crash). Every exit path sets it
        # and notifies (see _terminate, called from _run's finally), so no
        # waiter is ever left parked after the reader is gone. wait_activity
        # folds it into the predicate; without it a waiter that already passed
        # should_own_reads and blocked would sleep forever on a dead reader.
        self._activity_cond = threading.Condition(threading.Lock())
        self._generation = 0
        self._exc: Exception | None = None
        self._terminated = False

        # Distinguishes the two terminal causes for a waiter with nothing
        # buffered and no _fail error: an intentional stop() (close/collect/user
        # -> ConnectionClosedIntentionally, non-recoverable) from a clean
        # self-termination on a dead transport (a failure -> recoverable). Set
        # by stop() only when it actually terminates a live thread, so a stop()
        # arriving after the thread already died on its own does not relabel a
        # failure as intentional.
        self._intentional_stop = False

    @property
    def is_running(self) -> bool:
        """True only if the thread is alive AND owned by this process.

        After os.fork(), the child inherits a Thread object that still
        reports is_alive() == True even though no real OS thread is running
        in the child. The pid check catches that instead of lying about
        liveness.
        """
        thread = self._thread
        return thread is not None and thread.is_alive() and self._pid == os.getpid()

    def owns_current_thread(self) -> bool:
        """True iff the caller runs on this drainer's own thread.

        Used by frame_writer to recognise the drainer's own write (the
        heartbeat) and skip its collect() error-path: collect() -> stop() from
        this thread is a self-stop deadlock/RuntimeError. The drainer routes its
        write failures through _fail itself instead.
        """
        return threading.current_thread() is self._thread

    @property
    def should_own_reads(self) -> bool:
        """True while application threads must defer socket reads to the drainer.

        The drainer is this connection's single reader for its whole life. It
        stays the owner while alive, and also after a fatal _fail: the stored
        error must surface to app threads on every drain_events (README Rule 2)
        instead of being lost the moment the thread exits.

        This is a routing hint, not the safety boundary: the "exactly one
        reader" invariant is enforced by DrainGuard inside the actual read
        (ThreadSafeConnection._drain_into_buffers), so a racing read here is
        serialized rather than relying on the GIL.

        Stays True once the drainer has ever terminated (any exit path,
        including a clean self-termination with no _exc), so a new drain_events
        routes to the drainer branch and gets the terminal recoverable error
        from wait_activity — never falls through to the legacy path to read a
        torn-down socket, and a waiter parked before termination is released.
        """
        return self.is_running or self._exc is not None or self._terminated

    @property
    def generation(self) -> int:
        """Monotonic activity counter, bumped once per pumped frame.

        Capture this before dispatching buffered frames, then hand it to
        wait_activity: any frame the drainer pumps after the capture advances
        the counter, so the wait cannot miss it.
        """
        with self._activity_cond:
            return self._generation

    def _notify_activity(self) -> None:
        """Announce that a frame was pumped: advance the generation, wake waiters."""
        with self._activity_cond:
            self._generation += 1
            self._activity_cond.notify_all()

    def _fail(self, exc: Exception) -> None:
        """Record a fatal drain error and wake every waiter with it.

        Called only from the drainer thread when a socket/connection error
        ends draining. Marks the connection for teardown so publishers stop
        touching it, but does NOT call collect()/reconnect — that would make
        the drainer a second teardown subject (reconnect ping-pong, fix
        2e2cf64). The first error wins and is kept, so the same error is
        re-raised on every subsequent wait_activity (Rule 2).

        Does not bump the generation: _exc means "no more frames", distinct
        from _notify_activity's "a frame arrived". wait_activity prefers a
        genuine frame (a buffered graceful Close) over the raw EOF error.
        """
        with self._activity_cond:
            if self._exc is None:
                self._exc = exc
            self._conn.mark_for_teardown()
            self._activity_cond.notify_all()

    def _terminate(self) -> None:
        """Terminal signal: the drainer thread is leaving _run for good.

        Called from _run's finally on EVERY exit path (stop, clean
        self-termination, OSError in select, unexpected crash), so a waiter
        parked in wait_activity is always released — never left hanging on a
        reader that no longer exists (README Rule 2). Idempotent.
        """
        with self._activity_cond:
            self._terminated = True
            self._activity_cond.notify_all()

    def wait_activity(self, timeout: "float | None", since_generation: int) -> None:
        """Block until the drainer pumps a frame past `since_generation`.

        Wakes and resolves on, in priority order:
        - generation advanced -> return (buffered frames ready to dispatch);
        - stored fatal error -> re-raise it;
        - drainer terminated with nothing buffered -> RecoverableConnectionError
          (the reader is gone; a blocked waiter must not hang, and the caller
          should reconnect — parity with the legacy path, where a consumer
          draining the dead socket itself would get a connection error);
        - deadline elapsed while the drainer is still alive -> socket.timeout
          (a deliberate difference from DrainGuard.wait_drain_finished: here
          the socket state is known — nothing arrived — so a timeout is
          truthful).

        Predicate waited strictly in a while loop (no single-writer guarantee
        to lean on): spurious wakeups and the capture-before-wait ordering are
        both handled by re-checking the generation.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._activity_cond:
            while (
                self._generation == since_generation and self._exc is None and not self._terminated
            ):
                if deadline is None:
                    self._activity_cond.wait()
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self._activity_cond.wait(remaining)

            if self._generation != since_generation:
                # Activity happened; the caller dispatches the buffered frames.
                # This wins even if _exc or _terminated is also set, so a
                # graceful Close that was pumped just before the reader went
                # away surfaces as its real (recoverable) error rather than
                # being masked by the terminal signal.
                return
            if self._exc is not None:
                raise self._exc
            if self._terminated:
                if self._intentional_stop:
                    # The application closed this connection on purpose. Signal
                    # a NON-recoverable error so ensure()/Consumer propagate it
                    # instead of reconnecting and resurrecting a connection the
                    # app deliberately tore down.
                    raise ConnectionClosedIntentionally(
                        "dedicated drainer stopped: connection closed intentionally"
                    )
                # Terminated without an intentional stop and without a _fail
                # error: a clean self-termination on a dead transport. That is a
                # failure, so it stays recoverable — the caller may reconnect.
                raise RecoverableConnectionError("dedicated drainer stopped; connection is gone")
            raise TimeoutError

    def start(self) -> None:
        """Start the drainer thread; idempotent, single-flight under a lock.

        A second call while already running is a no-op. Concurrent callers
        are serialized by _lifecycle_lock so they cannot both pass the
        is_running check and spawn duplicate threads for the same connection.
        """
        with self._lifecycle_lock:
            if self._closed:
                # The self-pipe fds are closed once stop() has actually
                # stopped the thread (see stop()). Registering a closed fd
                # with the selector inside a background thread would fail
                # silently from the caller's point of view — raise here
                # instead, in the thread that made the mistake.
                raise RuntimeError(
                    "ConnectionDrainer already stopped; it is not restartable "
                    "(one drainer per ThreadSafeConnection, by design)"
                )

            if self.is_running:
                return

            if self._wakeup_r is None:
                # Allocate the self-pipe here, paired with _close_wakeup_pipe in
                # stop(): an unstarted drainer holds no fds. start() is
                # single-flight under _lifecycle_lock, so this runs once.
                self._wakeup_r, self._wakeup_w = os.pipe()
                os.set_blocking(self._wakeup_r, False)

            self._pid = os.getpid()
            thread = threading.Thread(
                target=self._run,
                name=f"kombu-pyamqp-drainer-{id(self)}",
                daemon=True,  # safety net only; normal shutdown goes through stop()
            )
            self._thread = thread
            thread.start()

    def stop(self, join_timeout: float = 2.0, intentional: bool = True) -> None:
        """Request the loop to exit and wait up to join_timeout for it.

        Safe to call twice: a second call finds no thread (already cleared
        below) and returns immediately. Must never be called from the
        drainer's own thread — that thread joining itself would deadlock, so
        this fails fast instead.

        intentional=True (close()/collect()/direct user stop) marks the stop as
        an application close, so a waiter released by it raises
        ConnectionClosedIntentionally (non-recoverable). intentional=False is
        for a failure-driven replacement (a reconnect stopping the outgoing
        connection's drainer): the waiter must stay recoverable so ensure()
        reconnects rather than surfacing an intentional-close signal.
        """
        with self._lifecycle_lock:
            thread = self._thread
            if thread is None or not thread.is_alive():
                self._thread = None
                self._close_wakeup_pipe()
                return

            if thread is threading.current_thread():
                raise RuntimeError("ConnectionDrainer.stop() called from its own drainer thread")

            # Terminating a live thread on purpose: mark the stop intentional
            # BEFORE waking it, so a waiter released by the terminal signal sees
            # the flag already set and raises ConnectionClosedIntentionally
            # rather than a recoverable error. Skipped for intentional=False
            # (reconnect replacement) and for the early-return branch above
            # (thread already dead on its own — a failure) — both stay
            # recoverable.
            if intentional:
                with self._activity_cond:
                    self._intentional_stop = True

            # A live thread implies start() ran, which allocated the pipe.
            assert self._wakeup_w is not None
            os.write(self._wakeup_w, b"\x00")
            thread.join(timeout=join_timeout)

            if thread.is_alive():
                logger.warning(
                    "drainer thread %s did not stop within %.1fs", thread.name, join_timeout
                )
                # Thread may still be selecting on the pipe — closing the fds
                # underneath it here could corrupt its selector. Leave both
                # the thread and the fds alone; this is a stuck-thread edge
                # case, not the normal path.
            else:
                self._close_wakeup_pipe()

            self._thread = None

    def _close_wakeup_pipe(self) -> None:
        if self._closed:
            return
        wakeup_r, wakeup_w = self._wakeup_r, self._wakeup_w
        if wakeup_r is None or wakeup_w is None:
            # Never started -> no pipe was ever allocated. A bare stop() before
            # start() is a pure no-op and must not burn the drainer (leave it
            # startable, _closed stays False).
            return
        os.close(wakeup_r)
        os.close(wakeup_w)
        self._closed = True

    def _run(self) -> None:
        # start() allocates the pipe before spawning this thread.
        assert self._wakeup_r is not None
        sel = selectors.DefaultSelector()
        try:
            sel.register(self._wakeup_r, selectors.EVENT_READ)
            self._loop(sel)
        except Exception as exc:
            # Any error escaping the loop body outside _drain_into_buffers
            # (e.g. sel.register on a socket a concurrent teardown just closed,
            # or an unexpected selectors error) must reach waiters, not die
            # silently on this thread with the cause lost (README Rule 2).
            logger.exception("dedicated drainer loop crashed unexpectedly")
            self._fail(exc)
        finally:
            # Terminal signal on EVERY exit path (clean or crashed): release any
            # waiter parked in wait_activity before the reader disappears.
            # Ordered before sel.close() so waking waiters never observe a
            # half-closed selector.
            self._terminate()
            sel.close()

    def _loop(self, sel: selectors.BaseSelector) -> None:
        conn_sock = None

        # Negotiated once: Tune-Ok completes inside ThreadSafeConnection.connect()
        # before start() is ever called, and this drainer never outlives its
        # connection (1:1 lifecycle — a reconnect gets a fresh drainer), so
        # conn.heartbeat cannot change out from under this read. 0 (or falsy)
        # means the broker/client negotiated no heartbeat at all: the ticker
        # stays fully off for this drainer's whole life, byte-for-byte the
        # same as before heartbeat ticking existed.
        heartbeat_interval = self._conn.heartbeat
        next_hb_at = time.monotonic() if heartbeat_interval else None

        # Resolved once, alongside heartbeat_interval and for the same reason:
        # conn.heartbeat is fixed for this drainer's whole life (1:1 lifecycle,
        # negotiated before start()). None here can only mean heartbeat is off,
        # in which case _tick_heartbeat is never reached.
        write_timeout = self._resolve_write_timeout(heartbeat_interval)

        while True:
            # Snapshot before use: conn._transport can be reassigned by a
            # concurrent reconnect between this read and a use of it: a local
            # copy avoids acting on a transport half-replaced under us
            # (composite check-then-use, not a single atomic read). In the 1:1
            # lifecycle the transport never actually changes for this drainer,
            # but the snapshot keeps the guarantee explicit.
            transport = self._conn._transport
            if transport is None or not transport.connected:
                return

            if conn_sock is None:
                # Register the transport socket once. 1:1 lifecycle: a reconnect
                # builds a new connection+drainer, so this socket is never
                # swapped and never needs re-registration. A failure here (fd
                # closed by a racing teardown) propagates to _run's handler and
                # routes to _fail — waiters still wake.
                conn_sock = transport.sock
                sel.register(conn_sock, selectors.EVENT_READ)

            select_timeout = self._poll_tick_s
            if heartbeat_interval:
                # Heartbeat cadence caps the wait: a 1s safety-net tick would
                # let up to a full second pass between checks on a 1s
                # heartbeat, well past the "call about once a second" amqp
                # asks for. min(), not a replacement, so a short poll_tick_s
                # (tests) is never slowed down by a longer heartbeat.
                select_timeout = min(select_timeout, heartbeat_interval / 4)

            try:
                events = sel.select(timeout=select_timeout)
            except OSError:
                # The transport socket was closed underneath select() by a
                # concurrent local teardown; nothing left to read. Exit cleanly
                # — _run's finally still fires the terminal signal, so waiters
                # wake with a recoverable error rather than hanging.
                return

            if any(key.fd == self._wakeup_r for key, _ in events):
                # stop() fired. Takes priority over draining: teardown is in
                # progress and the socket read would just race it.
                return

            if next_hb_at is not None and time.monotonic() >= next_hb_at:
                # Due regardless of whether select() returned on data, the
                # tick, or a spurious wakeup: heartbeat liveness does not wait
                # for the socket to have something to read.
                if not self._tick_heartbeat(write_timeout):
                    return  # fatal ConnectionForced; _fail already woke waiters
                next_hb_at = time.monotonic() + heartbeat_interval / 4

            # The only other registered fd is the transport socket, so a
            # leftover readable event means the socket has frames.
            if events and not self._drain_until_dry(sel):
                return  # fatal error; _fail already woke the waiters

    def _resolve_write_timeout(self, heartbeat_interval: "float | None") -> "float | None":
        """Bound for the heartbeat write (see _tick_heartbeat).

        An explicit constructor value wins. Otherwise derive it from the
        negotiated heartbeat — the write must complete within half the liveness
        window — and clamp to [floor, ceiling]. Returns None when heartbeat is
        off and no override is set: the ticker never runs, so there is no
        heartbeat write to bound.
        """
        if self._write_timeout_s is not None:
            return self._write_timeout_s
        if not heartbeat_interval:
            return None
        return min(
            _DEFAULT_WRITE_TIMEOUT_CEILING_S,
            max(_DEFAULT_WRITE_TIMEOUT_FLOOR_S, heartbeat_interval / 2),
        )

    def _tick_heartbeat(self, write_timeout: "float | None" = None) -> bool:
        """Send/check the negotiated heartbeat for one due tick.

        _transport_lock is held only for this one call (send_heartbeat, when
        it fires, writes through the same locked frame_writer publishers use
        — same one-call-at-a-time discipline as _drain_into_buffers).

        The heartbeat SEND is bounded by write_timeout via the transport's own
        having_timeout() — the same scoped-timeout mechanism publishers use in
        _basic_publish. Without it, send_heartbeat -> frame_writer -> sock.sendall
        is a blocking write with no timeout: if the peer's TCP receive window is
        shut (peer not reading, kernel send buffer full), sendall blocks for tens
        of minutes while _transport_lock is held, wedging publishers and close(),
        and the self-pipe cannot help (this thread sits in a write syscall, not in
        select). A write that overruns write_timeout raises socket.timeout
        (TimeoutError, an OSError subclass), caught below and routed to _fail like
        any other write failure. (transport.write_timeout is NOT the tool here: it
        is consumed once at _init_socket via setsockopt(SO_SNDTIMEO); reassigning
        it after connect does nothing to the live socket. having_timeout is the
        runtime path.)

        Invariant — the socket-timeout setting here is race-free. having_timeout's
        settimeout/restore runs entirely under _transport_lock, so it is
        serialized against publisher writes (which also take the lock), and the
        socket's only reader is this same drainer thread (reads run sequentially
        in _loop, never concurrently with this write). The previous timeout is
        restored in having_timeout's finally before the lock is released, so
        application writes with timeout=None — which pass through
        having_timeout(None) untouched — still see the ambient blocking mode:
        their behavior is byte-for-byte unchanged.

        Invariant — this write-path socket.timeout must NOT be conflated with the
        read-path TimeoutError in _drain_into_buffers/_drain_until_dry, where a
        timeout means "socket dry, keep running". Here it means "the write did not
        complete = the connection is effectively dead"; _tick_heartbeat's own
        except routes it to _fail, so the two paths never cross.

        Invariant — a partial heartbeat frame left half-written on timeout is safe
        only because _fail immediately marks the connection for teardown and no
        further frames are written on it: the stream is abandoned, not resumed.

        Returns True to keep the loop running. Returns False on a fatal
        heartbeat error, routed through _fail exactly like a socket read
        failure so a waiter blocked in drain_events gets it (README Rule 2)
        instead of the drainer going quiet with no one told why:
          - ConnectionForced — "too many heartbeats missed" (receive side);
          - OSError — the heartbeat SEND failed (RST/EPIPE that did not flip
            transport.connected, or a write that overran write_timeout).
            frame_writer recognises this write is on the drainer's own thread and
            skips its collect() (which would self-stop the drainer), re-raising
            the OSError for us to route to _fail here — keeping the "drainer never
            calls collect()" invariant on the write side too. OSError is
            recoverable, so ensure() reconnects; the pre-fix path surfaced a
            RuntimeError instead.
        """
        try:
            with (
                self._conn._transport_lock,
                self._conn._transport.having_timeout(write_timeout),
            ):
                self._conn.heartbeat_tick(rate=_HEARTBEAT_TICK_RATE)
            return True
        except (ConnectionForced, OSError) as exc:
            self._fail(exc)
            return False

    def _has_input(self, sel: selectors.BaseSelector, transport) -> "bool | str":
        """Is there anything to read right now — without a blocking read?

        Returns "stop" if the wakeup pipe fired, True if a frame (whole or
        partial) is waiting, False if the socket is genuinely dry.

        Three sources are checked, because a plain select() on the socket fd
        misses buffered input:
          - the transport's own read buffer holds bytes a prior recv pulled
            past the last frame boundary (a whole next frame can sit here with
            the socket already drained);
          - an SSL socket buffers decrypted records below the fd, invisible to
            select — sock.pending() surfaces them;
          - finally a non-blocking select for fresh bytes on the wire, which
            also polls the stop pipe so a long delivery stays interruptible
            between frames.

        Reaching into transport._read_buffer couples to amqp's transport
        internals; pinned by tests so an amqp change cannot silently strand a
        buffered frame.
        """
        if transport._read_buffer:
            return True

        pending = getattr(transport.sock, "pending", None)
        if pending is not None and pending():
            return True

        events = sel.select(timeout=0)
        if any(key.fd == self._wakeup_r for key, _ in events):
            return "stop"
        return any(key.fd != self._wakeup_r for key, _ in events)

    def _drain_until_dry(self, sel: selectors.BaseSelector) -> bool:
        """Pump frames until the socket is empty, notifying after each.

        One AMQP method per step (ThreadSafeConnection._drain_into_buffers),
        so consumers wake per delivered method. Returns True if the drainer
        should keep running (socket drained, a transient contended step, a stop
        request, or a mid-frame stall), False if a fatal error ended it (after
        _fail records+notifies).

        Closes two race/failure classes at once:
          - reader starvation: app threads never read, so a readable socket is
            always serviced by this one thread;
          - writer starvation + CPU burn: the dry check is a non-blocking
            _has_input() (never a blocking read holding _transport_lock while
            the socket is idle), and each actual read uses a small non-zero
            timeout so a fragmented body blocks on recv instead of busy-spinning
            at timeout=0.
        """
        conn = self._conn
        transport = conn._transport
        while True:
            status = self._has_input(sel, transport)
            if status is False:
                return True  # socket dry and buffers empty — nothing to read
            if status == "stop":
                return True  # stop pending; _loop's next select acts on it

            try:
                read = conn._drain_into_buffers(timeout=self._read_timeout_s)
            except TimeoutError:
                # Peer stalled mid-frame past read_timeout_s. read_frame has
                # prepended the partial bytes back onto the transport buffer,
                # so no half-frame is lost; yield the lock now and resume on
                # the next readable event.
                return True
            except Exception as exc:
                self._fail(exc)
                return False

            if not read:
                # Contended: a legacy reader holds the socket this instant.
                # Uncontended in normal drainer operation; retry next select().
                return True

            self._notify_activity()
