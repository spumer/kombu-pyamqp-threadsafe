# Dedicated Drainer

Benchmarks for the optional `dedicated_drainer` transport option: a
background thread that owns the socket read so publishers never queue up
behind another thread's blocking `drain_events()` call.

!!! note "Local run, not a guaranteed threshold"
    All numbers on this page come from a single local run (macOS host,
    RabbitMQ in Docker behind Toxiproxy) — directional evidence, not SLAs.
    Session-to-session variance is called out where it matters.

## What it is

By default a connection reads frames off the socket lazily, inside whichever
application thread happens to call `drain_events()`. That thread holds the
connection's transport lock for the entire blocking socket read — up to the
call's own timeout — and every other thread sharing the connection (in
particular, publishers) queues up behind it.

Setting `transport_options={"dedicated_drainer": True}` (default `False`)
gives the connection its own background thread that owns the socket read
instead. It polls the socket via `select`, pumps every available frame into
the connection's buffers, and takes the transport lock only for frames that
are already fully available — never for a blocking read. Other threads park
in `wait_activity()` instead of racing for the socket themselves. See the
README's [Dedicated drainer thread section](https://github.com/spumer/kombu-pyamqp-threadsafe/blob/master/README.md#dedicated-drainer-thread-optional)
for the full contract (lifecycle, heartbeat, closing semantics).

## Benchmark 1: publish latency with a stalled consumer

A background thread sits in a blocking `drain_events()` loop on the same
connection a publisher thread uses — modeling an idle consumer sharing a
connection with a publisher. In legacy mode, every blocking read that thread
makes holds the transport lock for the read's own timeout; a publish can end
up waiting behind it.

| Mode | P50 | P95 | P99 | Max |
|------|-----|-----|-----|-----|
| Legacy | 0.04 ms | 1001 ms | 1956 ms | 1956 ms |
| `dedicated_drainer` | 0.02 ms | 0.08 ms | 2.1 ms | 2.1 ms |

P99 improved roughly **900x** in this run. Across repeated sessions the
ratio ranged from 380x to 1566x — both numerators and denominators are in
the low-millisecond range, so the ratio itself is noisy even though the
direction is consistent. The benchmark asserts a single hard ceiling in
both modes: publish P99 must stay at or under 5 seconds; it is not meant as
a tight regression trip-wire otherwise.

Reproduce: `pytest tests/benchmarks/test_drainer_benchmarks.py -v -m benchmark`

## Benchmark 2: throughput parity

The same publish-throughput scenario as [Throughput](throughput.md), run
against both the legacy path and `dedicated_drainer` back to back.

| Threads | Mode | Throughput | P99 |
|---------|------|------------|-----|
| 10 | Legacy | 28,202 msg/s | 3.3 ms |
| 10 | `dedicated_drainer` | 36,626 msg/s | 1.5 ms |
| 100 | Legacy | 24,681 msg/s | 7.0 ms |
| 100 | `dedicated_drainer` | 23,756 msg/s | 8.9 ms |

At moderate concurrency `dedicated_drainer` is faster on both throughput and
tail latency — there's no idle consumer here, but the drainer still holds
the transport lock for less time per frame than a blocking read would. At
100 threads the two modes are within noise of each other: with this many
threads the bottleneck shifts to lock contention and broker backpressure
that neither mode changes. The option does not trade away throughput to fix
the stalled-consumer case above.

Reproduce: `pytest tests/benchmarks/bench_throughput.py -v -m benchmark`

## Benchmark 3: recovery after a connection reset

Simulates an RabbitMQ crash (TCP RST via Toxiproxy's `reset_peer` toxic) with
several worker threads sharing one connection, and measures how long it
takes for the error to propagate to *all* of them.

| Workers | Mode | Error propagation |
|---------|------|--------------------|
| 10 | Legacy | 468 ms |
| 10 | `dedicated_drainer` | 2.2 ms |
| 50 | Legacy | 523 ms |
| 50 | `dedicated_drainer` | 4.1 ms |

In legacy mode, workers are serialized behind the transport lock, so each
one only discovers the connection is dead once it gets its own turn to read.
With a dedicated drainer, the drainer thread hits the error once and every
waiting thread is released together.

Reproduce: `pytest tests/benchmarks/bench_recovery_latency.py -v -k reset_peer -m benchmark`

## Benchmark 4: bounded shutdown under load

Calls `close()` on a connection that has an active background consumer and
an active publisher both still running, 10 fresh connections per mode.

| Mode | Completed | Deadlocks | P50 | P95 |
|------|-----------|-----------|-----|-----|
| Legacy | 0/10 | 10/10 | — | — |
| `dedicated_drainer` | 10/10 | 0/10 | 508 ms | 513 ms |

!!! danger "Legacy mode deadlocks here, not just slows down"
    In legacy mode, `close()` holds the transport lock for its entire wait
    on the broker's `CloseOk` reply. If a background consumer's blocking
    read is in flight at that exact moment, it's waiting on the same lock
    to do its own read — a circular wait, confirmed with thread dumps in
    this benchmark. This is a long-standing property of the legacy path;
    this benchmark is the first time it's been measured rather than just
    suspected. `dedicated_drainer` avoids it structurally: `close()` never
    holds the transport lock across that wait, because the drainer thread
    (not the caller) does the actual socket read.

The benchmark asserts zero deadlocks and P95 under 4 seconds for
`dedicated_drainer`; legacy's deadlock count is reported as this
benchmark's expected finding, not asserted to be zero.

Reproduce: `pytest tests/benchmarks/test_drainer_shutdown.py -v -m benchmark`

## Fragmented frames

A separate check, not a legacy-vs-drainer comparison: what happens when a
single AMQP frame body (close to `frame_max`, 131,072 bytes) arrives in many
small, throttled chunks instead of one read — simulated with Toxiproxy
`bandwidth` (16 KB/s) and `slicer` (~512-byte slices) toxics stacked on one
proxy.

The message is delivered intact in every run. While it's arriving, the
drainer thread's CPU usage stays low: a busy ratio of 0.003–0.005 of one
core over the delivery window (measured via `psutil`). Earlier, before a fix
to how the drainer handles a read-timeout mid-frame, the same scenario
pegged a full core (busy ratio ≈ 0.97) — the drainer was spinning in a tight
loop waiting for the rest of the frame instead of yielding between chunks.

Reproduce: `pytest tests/benchmarks/test_drainer_fragmentation.py -v -m benchmark`

## Heartbeat and intentional close

With the option enabled, the connection ticks its own heartbeat as part of
the same drainer loop — no separate `heartbeat_check` call needed.

An intentional `close()`/`collect()` wakes any thread blocked in
`drain_events()` with `ConnectionClosedIntentionally`, so kombu's
`ensure()`/`Consumer` retry machinery doesn't mistake a deliberate shutdown
for a failure worth reconnecting from. See the
[README section](https://github.com/spumer/kombu-pyamqp-threadsafe/blob/master/README.md#dedicated-drainer-thread-optional)
linked above for the full details on both.
