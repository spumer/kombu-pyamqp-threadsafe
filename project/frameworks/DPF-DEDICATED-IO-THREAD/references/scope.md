---
artifact: "Phase-0 scope note (E.4.DPF:1)"
dpf_id: "DPF-DEDICATED-IO-THREAD"
phase: 0
date: "2026-07-14"
mode: "pretrain-only research run (no WebSearch/WebFetch — explicit customer decision for this run)"
---

# DPF-DEDICATED-IO-THREAD — Phase 0 Scope

> Structural note for the reader of this file: this is the scope declaration that gates Phase 1
> (SoTA Harvest). It is intentionally short — a paragraph per CC-DPF.1 slot, not a survey. Detail on
> sources lives in `sota-research.md` (next phase); detail on our own code lives in the target repo,
> not here.

## Bounded context

A **dedicated IO thread** in a multithreaded network client is a thread that is the sole,
unambiguous owner of a socket (or of the connection object that wraps it) and of the read/dispatch
loop over that socket for some window of time. The competency covers the *lifecycle and servicing*
concerns of that ownership arrangement:

- **Start** — where and when the thread (or the "owning turn", in designs that rotate ownership
  instead of pinning it) begins: lazy-on-first-use vs. explicit `start()`, who is the lifecycle
  owner, daemon vs. non-daemon, thread naming/observability.
- **Servicing** — the poll/drain loop itself: cross-thread wakeup (how a non-owner thread gets work
  or a notification into the loop without racing the socket read), timers/heartbeat servicing,
  loop-level error handling, write-side backpressure.
- **Stop** — graceful shutdown, join semantics and timeouts, what happens to work in flight.
- **Survival across reconnect and fork** — does the same thread/ownership arrangement persist
  across a broker-side disconnect, and what a fork() does to a live socket-owning thread.

**Instantiating project:** `kombu-pyamqp-threadsafe` (this repository) — a threadsafe rewrite of
kombu's pyamqp transport that deliberately does **not** pin one dedicated OS thread as sole socket
owner for the connection's lifetime. Instead it uses a *turn-taking* variant of the same underlying
problem: any thread may call `drain_events()`, but a `DrainGuard` (mutex + condition variable)
ensures only one thread is "the driver" for the duration of a single drain call, frames are
dispatched only into the thread that owns the channel they arrived for
(`channel_thread_bindings`), and a lock-protected `_transport_lock` serializes all direct socket
access. This is a documented departure from the classical "1 OS thread = 1 owner for the
connection's whole life" shape and is itself part of what this DPF must be able to explain,
contrast, and place a scope boundary around (see Non-use boundary). Secondary reference instance
inside the same bounded context: kombu's own `kombu.asynchronous.hub.Hub`, an actual
single-dedicated-thread event-loop reactor used elsewhere in the kombu/Celery ecosystem — useful
as the "classical" comparison case, not this repo's own design.

## Intended reader

`architect` role authoring or reviewing designs for multithreaded network clients (message-broker
clients, but the pattern generalizes to any client wrapping one non-thread-safe socket/connection
under multithreaded application code) inside this project and structurally similar ones. Secondary
reader: `dev` implementing against the resulting DPF's patterns; `guardian`/`cto` doing the Phase 6
adequacy pass.

## First use

Given a design question of the shape *"we have one non-thread-safe socket/connection and N
application threads that all want to publish/consume/observe it — how do we structure ownership of
the IO loop so that (a) nothing races the socket, (b) shutdown is clean, (c) reconnect doesn't
silently orphan a thread"* — the DPF should let the reader recognize which known pattern family
(dedicated-owner-thread vs. turn-taking/lock-based vs. rotating-leader) fits their constraints, and
what the known failure modes of each are before they re-derive them by incident.

## Non-use boundary

- **NOT** a general asyncio/Trio "how to write an event loop" primer — this DPF is scoped to the
  *ownership and lifecycle* of a resource-owning thread/turn, not to async syntax or coroutine
  scheduling mechanics in general.
- **NOT** a thread-pool-of-interchangeable-workers competency (e.g., `concurrent.futures.ThreadPoolExecutor`
  fan-out patterns) — those pools own no persistent exclusive resource across calls; this competency
  is specifically about a thread (or turn) that *is* the resource's access point for a stretch of
  time. Overlaps at the edge with `DPF-CONCURRENT-PROGRAMMING` (sibling package in this same
  `project/frameworks/` catalog) — that package should own general
  locking/synchronization-primitive choice; this package owns IO-thread-shaped instantiations of
  that choice specifically.
- **NOT** a message-broker selection/comparison guide (RabbitMQ vs. Kafka vs. NATS, etc.) — brokers
  appear here only as *sources of the dedicated-IO-thread pattern in their client libraries*, not as
  subjects of comparison on their own merits.
- **NOT** a verified/production-checked claim set at the end of Phase 1 — this run is explicitly
  pretrain-only (WebSearch/WebFetch withheld by customer decision, run 2026-07-14); every claim in
  the resulting `sota-research.md` carries a `pretrain recall, не верифицирован` trust-cue and
  web-verification is an explicit, named repair step for a later phase, not a silent gap.

## Owner + critic (E.4.DPF:1)

- **Owner (this phase):** architect role, acting as the universal research agent per method §4.
- **Critic (later, Phase 6):** guardian role — completeness-critic pass against `E.4.DPF.DA`, not
  self-assessed by the same agent that ran Phase 1/2 (method's own anti-pattern #7, "AI-consensus as
  evidence").

## Gate

Scope note exists (this file). Proceed to Phase 1 (`sota-research.md`).
