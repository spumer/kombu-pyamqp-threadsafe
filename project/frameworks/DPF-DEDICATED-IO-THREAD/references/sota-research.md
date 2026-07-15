---
artifact: "Phase-1 SoTA Harvest (G.2)"
dpf_id: "DPF-DEDICATED-IO-THREAD"
phase: 1
date: "2026-07-14"
mode: "PRETRAIN-ONLY RESEARCH RUN — WebSearch/WebFetch withheld by explicit customer decision for this run (2026-07-14)"
gate_target: "FamilyCoverageFloorK=3 (G.2:4.1); every claim carries source+date (A.10)"
---

# DPF-DEDICATED-IO-THREAD — Phase 1: SoTA Harvest & Synthesis

> **Structural note for the reader:** this file is `G.2`'s harvester output, restricted to the
> components the method's Phase 1 gate actually requires: `G.2a CorpusLedger`, `G.2b ClaimSheets`
> per `Tradition` (≥3), a mandatory AI-in-this-domain slice, `G.2e MicroExamples`, and a light
> `G.2c OperatorAndObjectInventory`. The heavier G.2 apparatus (BridgeMatrix, UTSProposals,
> SoSIndicatorFamilies, GeneratorFamilyCards, full PRISMA flow) either belongs to Phase 2
> (`theses-antitheses.md`, not this file) or is not load-bearing for a DPF of this size and is
> skipped rather than padded — do not read this as G.2 in full.
>
> **Trust regime (read before trusting any claim below):** this run explicitly excludes
> WebSearch/WebFetch (customer decision, 2026-07-14 prompt). Every claim below is **pretrain recall
> only**, carries the literal tag `pretrain recall, не верифицирован`, and its "evidence anchor" is
> a named source + approximate date recalled from training, not a fetched/re-read document. This is
> weaker than A.10 wants long-term. Web-verification of these claims is registered as an explicit,
> named repair step for a later phase (see `Freshness & repair register` at the end) — not silently
> smoothed over. Do not promote any single claim here to `admissibleForDeclaredDPFUse` status
> without that repair pass; Phase 6 (`E.4.DPF.DA`) must weigh this regime into `D11` (currentness).

## G.2a — CorpusLedger

| # | Source (as recalled) | Tradition | Approx. date | Triage | Rationale |
|---|---|---|---|---|---|
| S1 | Buschmann, Meunier, Rohnert, Sommerlad, Stal — *Pattern-Oriented Software Architecture, Vol. 2: Patterns for Concurrent and Networked Objects* (Wiley) — Reactor, Active Object, Half-Sync/Half-Async, Leader/Followers | T1 Concurrency-pattern literature | ~2000 | **include** | Canonical, still-cited backbone vocabulary for "who owns the loop/socket" question; every other tradition below is a concrete instantiation of one of these shapes |
| S2 | Schmidt, D. — "Reactor: An Object Behavioral Pattern for Demultiplexing and Dispatching Handles for Synchronous Events" (paper, pre-POSA2) | T1 | ~1995 | **include** | Origin paper for S1's Reactor chapter; names the "one thread runs the demux loop, must not block in a handler" invariant explicitly |
| S3 | Lea, D. — *Concurrent Programming in Java*, 2nd ed. | T1 | ~1999 | **park** | Overlaps S1/S2 content from a Java-specific angle; not pulled into claims below to avoid restating S1/S2, kept parked as a cross-check candidate for the web-verification repair pass |
| S4 | pika (Python AMQP 0-9-1 client) official docs, "FAQ" / threading guidance | T2 Messaging/broker client libraries | ~2019–2023 (docs generation recalled, not pinned to one release) | **include** | Directly documents the single-thread-per-connection rule and the `add_callback_threadsafe` marshal-in primitive — closest documented analogue to this repo's own problem statement |
| S5 | RabbitMQ Java client guide — "Consumer Operation Thread Pool" / connection thread-safety notes | T2 | ~2015–2023 (long-stable doc section, exact edition not pinned) | **include** | Documents the split between the IO-owning thread and a separate dispatch pool — a concrete "why not just do everything on the IO thread" case |
| S6 | Apache Kafka producer internals — `Sender` background thread / `RecordAccumulator` design | T2 | ~2013–2016 origin (KIP/design era), stable since | **include** | Different broker family, same shape (background IO thread owns the wire, app threads only enqueue) — useful for K≥3 diversity within messaging itself, and for the "producer.close() must join with a timeout" lifecycle claim |
| S7 | kombu — `kombu.asynchronous.hub.Hub` (source + Celery project docs/comments) | T2 | ~2013–2016 origin, long-stable | **include** | Directly in this project's own dependency tree; the "classical" single-dedicated-thread reactor instance this repo's own design (turn-taking, not pinned ownership) deliberately departs from — necessary contrast case named in scope.md |
| S8 | This repo's own `README.md`, citing `github.com/celery/py-amqp/issues/420` | T2 (corpus item, not adopted-as-SoTA) | issue referenced, exact date not recalled | **include as corpus item, not as an independent Tradition claim** | Names the origin problem ("py-amqp Connection not safe to share across threads") this whole package exists to solve differently; kept as provenance, not cited as external SoTA authority since it is the target project's own framing |
| S9 | libuv — "Design overview" docs, `uv_async_t` / `uv_async_send` | T3 Event-loop/async-runtime tradition | docs stable since ~2013 | **include** | Names the one-thread-owns-the-loop invariant plus the one documented safe cross-thread call (`uv_async_send`) — clean minimal instance of "cross-thread wakeup primitive" as a named operator |
| S10 | Python official docs — `asyncio`, "Concurrency and Multithreading" section, `loop.call_soon_threadsafe()` | T3 | stable ~3.4+ through mid-2020s doc generations | **include** | Same invariant in a runtime this project's own ecosystem (kombu/Celery) sits next to; gives the DPF a reader-familiar reference point |
| S11 | Redis documentation / design rationale for `io-threads` (Redis 6.0) and antirez (Salvatore Sanfilippo) blog posts on the decision | T3 | 2020 (Redis 6.0 release) | **include** | Shows a tradition *deliberately keeping* the single-owner-thread boundary for the state-mutating part while only parallelizing the IO edges — a nuance directly relevant to this repo's own "shared connection, serialized turns" design |
| S12 | Qt official docs — "Threads and QObjects", queued signal/slot connections across threads | T4 GUI/UI-thread tradition | long-stable across Qt4/5/6 doc generations | **include** | Structurally identical "single owner + cross-thread marshalled queue" idiom applied to UI state instead of a socket; useful to show the pattern is not networking-specific |
| S13 | Android Developers docs — "Processes and Threads", `Looper`/`Handler`/`MessageQueue` | T4 | long-stable guidance, Kotlin-first docs refresh ~2019–2023 | **include** | Second GUI-tradition instance; the `Looper`+`Handler` vocabulary maps almost 1:1 onto "dedicated loop thread + cross-thread post-a-message primitive" | 
| S14 | psycopg2 / libpq documentation — connection thread-affinity warnings ("a single connection must not be used by concurrent threads without an external lock") | T5 DB-driver tradition (boundary case, not fully harvested) | long-stable | **park** | Same-shaped constraint, different resolution family (external caller-supplied lock, no dedicated thread or turn-taking primitive of its own) — flagged in scope.md's non-use boundary as adjacent-but-different; parked rather than given a full ClaimSheet to keep Phase 1 focused per the research-first-but-not-endless forces tension (method §3) |
| S15 | General pattern-matching over publicly-discussed LLM code-generation failure modes for threaded network/socket code (Stack Overflow / GitHub issue commentary patterns, developer-blog postmortems, circa 2022–2024) | AI-in-domain slice | 2022–2024, diffuse | **include, flagged low-confidence** | No single citable paper; this is synthesized pattern-matching over many diffuse pretrain observations, not a single source — kept because the task mandates an AI-in-domain slice, but explicitly marked weaker than S1–S13 (see AI slice section) |

**Coverage check:** 4 independently-sourced `Tradition`s reach `include` status with ≥2 sources
each (T1, T2, T3, T4) — `FamilyCoverageFloorK=3` (G.2:4.1) is met with margin. T5 is intentionally
parked, not counted toward the floor, to avoid diluting focus (Forces §3: cost of research vs.
richness, resolved by "enough to pass the gate honestly," not "harvest everything adjacent").

## G.2b — ClaimSheets per Tradition

Each claim: bounded context (where it holds) · evidence anchor (source id from ledger + approx.
date) · freshness · trust-cue. All trust-cues in this file are the same because the run mode is
uniform — repeated per claim anyway per method's explicit requirement, not elided.

### Tradition 1 — Concurrency pattern literature (Active Object / Half-Sync-Half-Async / Reactor / Leader-Followers)

- **T1-C1.** *Active Object* pattern: a concurrently-accessed object is given a request queue and a
  single "scheduler" thread that pulls requests off the queue and executes them serially against the
  object's protected state; calling threads only enqueue a request (optionally getting back a
  future/promise), they never touch the state directly. This decouples method invocation from
  method execution and gives a single-writer guarantee without the caller blocking on internal
  locks.
  — Bounded context: general concurrent-object design, language-agnostic.
  — Evidence anchor: S1/S1's Active Object chapter (Lavender & Schmidt origin paper folded into
  POSA2), ~1995/2000.
  — Freshness: durable/backbone; the shape recurs unmodified in modern actor frameworks.
  — Trust-cue: pretrain recall, не верифицирован.

- **T1-C2.** *Half-Sync/Half-Async* pattern: a synchronous IO layer (one thread doing blocking
  reads/writes on a low-level resource — a socket in the canonical case) is explicitly separated
  from asynchronous application-level processing by a queueing layer; the sync IO thread is the
  sole owner of the low-level connection endpoint and must not run application logic, only
  transport/framing work.
  — Bounded context: systems with one blocking-IO resource shared by async application logic.
  — Evidence anchor: S1, ~2000.
  — Freshness: durable/backbone.
  — Trust-cue: pretrain recall, не верифицирован.

- **T1-C3.** *Reactor* pattern: a single thread runs an event-demultiplexing loop
  (`select`/`poll`/`epoll`-shaped) and synchronously dispatches each ready event to a registered
  handler in that same thread; if a handler blocks or runs long, it stalls dispatch for every other
  registered handle sharing that reactor — this is presented as the central discipline violation to
  avoid, not an edge case.
  — Bounded context: single-threaded event-driven IO servers/clients.
  — Evidence anchor: S2 (~1995), restated in S1 (~2000).
  — Freshness: durable/backbone; directly recognizable in every "don't block the event loop" warning
  in modern async runtimes (T3 below).
  — Trust-cue: pretrain recall, не верифицирован.

- **T1-C4.** *Leader/Followers* pattern: rather than pinning one thread as permanent owner, a pool
  of threads takes turns being "leader" — the leader waits on the event source; when an event
  arrives it promotes a follower to leader *before* processing the event itself, so the wait slot is
  never empty, trading a more complex handoff protocol for removing the single-thread bottleneck.
  — Bounded context: high-throughput servers where one dedicated thread would bottleneck; explicitly
  presented as the documented alternative family to "one fixed dedicated thread," not a variant of
  it.
  — Evidence anchor: S1, ~2000.
  — Freshness: durable/backbone.
  — Trust-cue: pretrain recall, не верифицирован.
  — **Scope note:** this is the closest documented literature analogue to this repo's own
    turn-taking design (any thread may become the momentary drain-owner via `DrainGuard`), but it is
    not a clean match — Leader/Followers rotates *who waits on the socket next*, while this repo's
    `DrainGuard` instead makes *whichever thread already wants to drain* take a single-flight turn
    and lets other simultaneous callers just wait on the outcome rather than pre-electing a
    successor. Flagging the difference now (not silently fusing) for Phase 2's BridgeMatrix.

### Tradition 2 — Messaging / broker client libraries

- **T2-C1.** pika documents that a `Connection`/`Channel` object is not thread-safe and must be
  driven from exactly one thread; when other threads need to publish or otherwise act on that
  connection, the documented recipe is to run the connection's IO loop in one dedicated thread and
  use a thread-safe hand-off primitive (`connection.add_callback_threadsafe(callback)`) to marshal
  the actual work onto the IO thread, rather than calling connection/channel methods directly from
  other threads.
  — Bounded context: Python AMQP 0-9-1 client usage in multithreaded apps.
  — Evidence anchor: S4, pika docs ~2019–2023 (exact version not pinned).
  — Freshness: recurring guidance across several pika doc generations; low drift risk but not
  re-verified this run.
  — Trust-cue: pretrain recall, не верифицирован.

- **T2-C2.** RabbitMQ's Java client documents a deliberate split between the connection's own
  frame-reading IO thread and a separate, configurable consumer-dispatch thread pool, specifically
  so that slow or blocking consumer callback code cannot delay frame reading or heartbeat
  processing on the IO thread — i.e., the dedicated IO thread's job is scoped narrowly (protocol
  framing/heartbeats) and application work is explicitly kept off it.
  — Bounded context: Java AMQP client, consumer-heavy workloads.
  — Evidence anchor: S5, ~2015–2023 (long-stable doc section).
  — Freshness: durable within this client family.
  — Trust-cue: pretrain recall, не верифицирован.

- **T2-C3.** Kafka's Java Producer keeps a background `Sender` thread that owns the network client
  and performs the actual socket writes/batches; calling `producer.send()` from an application
  thread only appends the record to an in-memory `RecordAccumulator` and returns a future —
  the two are decoupled by design so application threads never touch the socket. `producer.close()`
  is documented to flush and join this background thread, optionally with a timeout, and a
  too-short timeout is a documented way to lose buffered messages.
  — Bounded context: Java Kafka producer client.
  — Evidence anchor: S6, design ~2013–2016, stable since.
  — Freshness: durable/backbone within Kafka client design.
  — Trust-cue: pretrain recall, не верифицирован.

- **T2-C4.** kombu's `asynchronous.hub.Hub` implements a single-threaded reactor-shaped event loop
  (in the S2/S1 sense) used by parts of the Celery/kombu ecosystem; the loop is intended to run in
  one thread for its lifetime, and cross-thread or signal-handler-driven wakeup into a blocking
  `poll`/`epoll_wait` call is handled by a self-pipe-style primitive rather than by touching loop
  state directly from the other thread.
  — Bounded context: kombu/Celery's own async event-loop subsystem — same dependency family as this
  project, but a different subsystem than the one this project modifies.
  — Evidence anchor: S7, kombu source ~2013–2016 origin, long-stable.
  — Freshness: **medium confidence** — the self-pipe mechanism detail is recalled at a coarser grain
  than T2-C1–C3; flagged explicitly as a repair-candidate for a source re-read in a later phase
  (this project already has kombu as a direct dependency, so a code re-read is cheap once
  web/file access is back in scope for that phase).
  — Trust-cue: pretrain recall, не верифицирован (lower confidence than sibling claims in this
  tradition).

- **T2-C5 (corpus/provenance claim, not adopted as external SoTA authority).** This project's own
  `README.md` states the underlying `py-amqp` connection is not safe to share across threads and
  cites `github.com/celery/py-amqp/issues/420` as the origin discussion; the content of that GitHub
  issue itself is recalled only vaguely from pretraining and is **not** independently re-verified
  this run.
  — Bounded context: this repository's own stated problem framing.
  — Evidence anchor: S8, this repo's `README.md` (read directly this run — that part is fact, not
  recall) citing an external issue (recall only, unverified).
  — Freshness: n/a (self-referential provenance note, not an external claim).
  — Trust-cue: `README.md` citation itself — direct read, verified this run; the underlying GitHub
  issue's content — pretrain recall, не верифицирован.

### Tradition 3 — Event-loop / async-runtime tradition

- **T3-C1.** libuv is documented as requiring its event loop (`uv_run`) to be driven from a single
  thread; most libuv API calls are not safe to call from a different thread while the loop is
  running, with `uv_async_send()` documented as the specific exception — a lightweight, thread-safe
  primitive whose whole job is to wake the loop and let it notice work queued by another thread.
  — Bounded context: libuv-based runtimes (Node.js and others).
  — Evidence anchor: S9, docs stable since ~2013.
  — Freshness: durable/backbone; unlikely to have drifted materially.
  — Trust-cue: pretrain recall, не верифицирован.

- **T3-C2.** Python's `asyncio` documentation states an event loop must be run from the thread that
  owns it, and the sanctioned way to schedule a callback onto a running loop from another thread is
  `loop.call_soon_threadsafe(callback, *args)`; calling loop-affecting APIs directly from another
  thread, or running blocking/CPU-bound work inside a loop callback, are both documented anti-
  patterns because they either race loop internals or stall every other scheduled callback (a direct
  restatement of T1-C3's Reactor discipline in a concrete runtime).
  — Bounded context: Python `asyncio` applications.
  — Evidence anchor: S10, docs stable ~3.4+ through mid-2020s generations.
  — Freshness: durable; low drift risk (this API has been stable for many Python releases).
  — Trust-cue: pretrain recall, не верифицирован.

- **T3-C3.** Redis ran a single-threaded command-execution loop by design through its early
  history (to avoid locking data structures); Redis 6.0 (2020) added optional `io-threads`, but
  scoped strictly to the socket read/parse and write/reply-serialization edges of the request
  lifecycle — command execution against the keyspace stayed on the single main thread. The documented
  rationale was that the single-owner-thread boundary was cheap correctness insurance for the
  mutation-sensitive part, and only the genuinely parallelizable IO edges were pulled out.
  — Bounded context: Redis server internals, not a client library.
  — Evidence anchor: S11, Redis 6.0 docs + antirez design-rationale posts, 2020.
  — Freshness: specific to the 6.0-era design decision; current default `io-threads` behavior in
  later Redis major versions not re-checked this run.
  — Trust-cue: pretrain recall, не верифицирован.
  — **Relevance note:** structurally the closest external analogue to this repo's own choice to keep
  a shared connection but serialize the sensitive parts (`_transport_lock`, `DrainGuard`) instead of
  fully isolating IO onto one pinned thread — flagged for Phase 2 bridging, not asserted as
  equivalence here (no silent fusion, G.2d).

### Tradition 4 — GUI / UI-thread tradition

- **T4-C1.** Qt requires GUI objects to be accessed only from the thread that owns them — normally
  the thread running the Qt event loop via `QApplication::exec()`. Cross-thread interaction is done
  through signal/slot connections: when a signal crosses a thread boundary, Qt automatically queues
  the call as an event on the receiving object's owning thread instead of executing it directly on
  the caller's thread, giving the same "single owner thread + marshalled cross-thread queue"
  shape as T1-C1/T2-C1/T3-C1, applied to UI state instead of a socket.
  — Bounded context: Qt-based GUI applications.
  — Evidence anchor: S12, Qt docs stable across Qt4/5/6 doc generations.
  — Freshness: durable/backbone within Qt.
  — Trust-cue: pretrain recall, не верифицирован.

- **T4-C2.** Android's main ("UI") thread runs a `Looper` pulling `Message`/`Runnable` work off a
  `MessageQueue`; other threads must not touch UI objects directly, and instead post work onto the
  main thread via a `Handler` bound to the main `Looper`. This is presented in Android's own docs as
  the required discipline, not an optimization — touching UI state off the main thread is a runtime
  error class (`CalledFromWrongThreadException`), not just a style violation.
  — Bounded context: Android application UI thread.
  — Evidence anchor: S13, Android Developers docs, long-stable guidance.
  — Freshness: durable; terminology refreshed in Kotlin-first docs but semantics unchanged.
  — Trust-cue: pretrain recall, не верифицирован.
  — **Cross-tradition note:** T4-C1/T4-C2 exist in this pack specifically to show the "dedicated
  owner thread + cross-thread post/marshal primitive" shape recurs outside networking entirely —
  it is a general single-writer-ownership idiom, and the messaging/event-loop traditions (T2, T3)
  are its networking-specific instances, not the whole of the idiom.

## Mandatory slice — AI in this domain

> Explicitly marked **lower-confidence than T1–T4 above**: no single citable paper backs this
> section; it is pattern-matching over diffuse, non-pinned pretrain exposure to how LLM code
> assistants tend to generate dedicated-IO-thread / background-socket-thread code, and to publicly
> discussed failure reports about that generated code (developer forums, issue trackers, blog
> postmortems, circa 2022–2024). Flagged per S15 in the CorpusLedger. Trust-cue for every item below:
> **pretrain recall / synthesized pattern-matching, не верифицирован — weaker than T1–T4, explicit
> web-verification repair candidate.**

- **Tooling context.** LLM coding assistants (Copilot/Cursor/Claude-style chat assistants circa
  2022–2024) are routinely asked to scaffold "run this blocking/socket-based client's loop in a
  background thread and make it usable from multiple threads" — this exact prompt shape (wrap a
  synchronous network client for multithreaded use) is a recurring, generic request across many
  unrelated libraries (MQTT clients, AMQP clients, raw sockets, serial-port drivers), not specific
  to any one broker.

- **AI-F1 — Missing/weak cross-thread wakeup.** Generated code frequently implements the poll loop
  with a bare timeout (`select(..., timeout=1.0)` style) as the *only* mechanism for the loop to
  ever notice external state changes (shutdown flag, new work), instead of a wakeup primitive
  (self-pipe, `eventfd`, `uv_async_send`-equivalent, condition variable). This "works" in a demo
  (notices things within one timeout period) but silently degrades latency/correctness guarantees
  under review — a plausible-looking loop that is subtly wrong, not obviously broken.

- **AI-F2 — Missing or unsafe shutdown/join semantics.** Generated background-thread code commonly
  sets `daemon=True` and never calls `.join()`, or joins without a timeout. The first produces
  "the process exits with in-flight work silently dropped"; the second produces "close() can hang
  forever" once the same snippet is reused in a context where the loop doesn't reliably exit on its
  own (e.g., after this repo's own kind of reconnect logic is layered on top).

- **AI-F3 — "The GIL makes it thread-safe" reasoning.** Generated explanations and code comments
  frequently invoke CPython's GIL as a reason concurrent access to a shared socket/connection object
  is safe, when the GIL only serializes individual bytecode-level operations, not multi-step
  protocol state machines (open a channel → send a frame → await a reply is not atomic even under
  the GIL). This is exactly the class of bug this repository's own `ThreadSafeChannel` /
  `ChannelCoordinator` machinery is built to prevent, which is why it is named here specifically
  rather than left generic.

- **AI-F4 — Wrong concurrency primitive for the runtime.** `asyncio.Lock`/`asyncio.Queue` showing up
  inside plain-`threading` code, or `threading.Lock` showing up inside coroutine code, because both
  idioms answer to the same natural-language prompt ("make this concurrency-safe") from the same
  training distribution without the surrounding runtime context disambiguating which is meant. The
  failure mode is not a crash — it is a lock that never actually serializes the intended callers
  (silent no-op) or a coroutine that blocks the whole event loop while "holding" a thread lock.

- **AI-F5 — Non-idempotent generated reconnect loops.** Generated reconnect/retry code often reopens
  a socket and/or spins up a new background thread on every observed error without first checking
  whether a reconnect is already in flight, which under bursty errors (the case this repo's own
  `_teardown_lock` / `marked_for_teardown` / `ensure()` fork explicitly guards against) produces
  multiple threads racing to replace the same connection object.

- **Read on tooling impact:** none of AI-F1–F5 are novel bugs — they are old bug classes (missed
  wakeup, unjoined thread, false safety assumption, wrong primitive, non-idempotent retry) that
  pre-date LLM code assistants by decades (they are the exact failure modes T1's literature already
  warns about). What is plausibly new is *frequency and plausibility*: generated code tends to look
  complete and idiomatic while missing exactly these invariants, so review effort has to shift from
  "does this compile / look right" toward "does this loop have a wakeup path, a bounded shutdown,
  and an idempotency guard" as an explicit checklist — which is itself the kind of thing a DPF like
  this one is meant to hand a reviewer directly instead of leaving to be rediscovered.

## G.2e — MicroExamples

> General, illustrative sketches from the literature/traditions above — **not this project's own
> code**. Kept intentionally short; they exist to make the claims above checkable at a glance, not
> to be production-ready.

**ME1 — Active Object shape (T1-C1), generic Python sketch:**
```python
# One thread owns `state`; callers only ever go through `queue`.
import queue, threading

class ActiveObject:
    def __init__(self):
        self._q = queue.Queue()
        self._state = {}
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(self, fn, *args):
        fut = Future()
        self._q.put((fn, args, fut))
        return fut

    def _run(self):
        while (item := self._q.get()) is not None:
            fn, args, fut = item
            fut.set_result(fn(self._state, *args))
```
Illustrates: single scheduler thread, callers never touch `_state` directly, `submit()` is the only
cross-thread-safe entry point (mirrors T2-C1's `add_callback_threadsafe`, T3-C2's
`call_soon_threadsafe`, T4-C1's queued signal/slot).

**ME2 — Cross-thread wakeup primitive (T3-C1/T3-C2), generic shape:**
```python
# asyncio: scheduling work from a non-loop thread
loop.call_soon_threadsafe(callback, *args)

# libuv (C): the one call safe from another thread while uv_run() is active
uv_async_send(&async_handle);  // wakes uv_run(); handle's callback runs on loop thread
```
Illustrates: both runtimes expose exactly one narrow, documented safe crossing point rather than
letting any API be called from any thread — the "wakeup primitive" is a *named, singular* operator
in both traditions, not an emergent property of "just use a lock somewhere."

**ME3 — Non-idempotent reconnect anti-pattern (AI-F5), generic shape:**
```python
def on_error(exc):
    # BUG: no check whether a reconnect is already in flight;
    # under a burst of errors this spawns N racing reconnects.
    threading.Thread(target=reconnect, daemon=True).start()
```
vs. the guarded shape (structurally what T2-C3's producer.close()-joins-Sender-thread and this
repo's own teardown-lock both do — named here only as a *generic* contrast, not cited as our code):
```python
def on_error(exc):
    if not _reconnect_lock.acquire(blocking=False):
        return  # a reconnect is already in flight; do not race it
    try:
        reconnect()
    finally:
        _reconnect_lock.release()
```

## G.2c — Operator / Object Inventory (light, stub-level per G.2:4.2 item 3)

Candidate terms surfaced across T1–T4 for later CHR/CAL-shaped authoring in Phase 4/5 of this DPF.
Stubs only — no legality/threshold claims asserted here.

| Candidate term | Rough meaning (as used across traditions) | Traditions it appears in |
|---|---|---|
| **Loop-owner thread** | The thread that is, for some window, the sole entity allowed to drive the poll/drain/dispatch loop over the shared resource | T1 (Reactor), T2 (all), T3 (all), T4 (all) |
| **Turn / single-flight ownership** | A weaker variant of loop-owner thread: ownership is per-call, not per-thread-lifetime; any thread may take a turn, but only one at a time | T1 (Leader/Followers, partial match), this repo's own `DrainGuard` (named as the instantiating case, not a tradition claim) |
| **Cross-thread wakeup/marshal primitive** | The single, narrow, documented-safe operation for a non-owner thread to get work or a notification into the owner's loop | T2-C1 (`add_callback_threadsafe`), T3-C1 (`uv_async_send`), T3-C2 (`call_soon_threadsafe`), T4-C1 (queued signal/slot), T4-C2 (`Handler.post`) |
| **Work/request queue (mailbox)** | The structure a non-owner thread enqueues onto instead of touching owned state directly | T1-C1, all of T2/T3/T4's marshal primitives implicitly queue underneath |
| **Backpressure** | What happens when producers enqueue faster than the owner thread can drain — named explicitly in T2-C3 (Kafka's `RecordAccumulator` + send-blocking config) | T2 (Kafka), T1 (implicit in Active Object queue bounding) |
| **Graceful shutdown / bounded join** | Owner thread must be stoppable with a bound on wait time; a documented failure mode (AI-F2) when this is missing or unbounded | T2-C3 (Kafka producer.close(timeout)), general |
| **Reconnect idempotency guard** | A check that a reconnect/re-own attempt is not already in flight before starting another | AI-F5 (named failure mode), this repo's own `_teardown_lock`/`marked_for_teardown` (instantiating case only) |
| **Scoped IO-thread responsibility** | The IO-owning thread's job is kept deliberately narrow (framing/heartbeats/socket read-write), with application-level work explicitly pushed off it | T2-C2 (RabbitMQ consumer thread pool), T3-C3 (Redis io-threads scoped to socket edges only) |
| **Thread affinity without ownership (contrast case)** | A resource is *not* handed to one owner thread or loop, but the caller is instead required to supply external mutual exclusion themselves | T5/S14 (DB-driver tradition, parked — non-use boundary case per scope.md, not adopted into the main inventory) |

## Freshness & repair register (honest gaps, not silently smoothed)

- **Every claim above** is pretrain recall, not re-verified against a live source this run —
  customer-mandated mode for 2026-07-14. Web-verification of S1–S13 (skip S15, which is explicitly
  a synthesis, not a document to re-fetch) is the standing repair step before any of these claims
  should be treated as `admissibleForDeclaredDPFUse`-grade evidence in Phase 6.
- **T2-C4** (kombu Hub self-pipe detail) is flagged at *lower* confidence than its siblings in the
  same tradition — this project already vendors/depends on kombu, so a direct source read (not even
  web access, just `Read` on the installed package) is a cheap, specific repair step available even
  within the current pretrain-only constraint, and is recommended before Phase 2 leans on T2-C4.
- **AI-in-domain slice (S15/AI-F1–F5)** is explicitly weaker evidence than T1–T4: no single citable
  paper, synthesized over diffuse exposure. Recommended repair: a targeted web search for published
  empirical studies of LLM-generated concurrency bugs (a few are known to exist in the broader ML/SE
  literature) once web access is back in scope, rather than treating this section's confident tone
  as equivalent to T1–T4's literature grounding.
- **T5 (DB-driver tradition)** was deliberately parked, not fully harvested, to keep this Phase 1 run
  focused (Forces §3). If Phase 2's BridgeMatrix work finds it load-bearing after all, promoting it
  from parked to included is a small, well-scoped follow-up, not a reopening of the whole harvest.

**Addendum, 2026-07-14 (repair round, `DPF-KNOWLEDGE-CURATION` curator, Mode C круг 1) — added, not
rewriting the ClaimSheets above:** the standing repair step named in this section's first bullet was
taken. S1–S13 were web-verified against live sources; 11 of 13 confirmed as recalled, S6 confirmed and
sharpened (KIP-15 gives the exact origin of the documented `close(timeout)` API). S14 (used only as a
counterexample, not a ClaimSheet entry in this file) was found partially inaccurate as stated elsewhere
in the package and corrected there — see `references/web-verification-2026-07-14.md` and
`references/source-pack.md` for the full ledger and the correction; this file's own T1–T4 ClaimSheet
prose above is left as originally written (Phase 1 artifact, not this curator's mandate to rewrite) —
readers should treat the *trust-cue* on each claim as superseded by `source-pack.md`'s updated
Currentness column, not by an edit to the sentences above. The AI-in-domain slice (S15) was not
re-verified (still not a fetchable document, per this section's own note) and T5 remains parked.

## Gate check (G.2:4.1 FamilyCoverageFloorK=3)

- Traditions with `include` status and ≥2 claims each: **T1, T2, T3, T4 → 4 traditions**, floor of 3
  met with margin.
- Every claim above carries an evidence anchor (source id + approximate date) and an explicit
  trust-cue.
- AI-in-domain slice present (mandatory per this run's instructions), explicitly flagged as
  lower-confidence than the literature-grounded traditions rather than presented at equal weight.
- **Gate: PASSED** for Phase 1's purposes (≥3 traditions, every claim sourced+dated). Not the same
  as Phase 6's `E.4.DPF.DA` adequacy gate, which this file does not attempt to satisfy on its own —
  see Freshness & repair register above for what a later phase still owes this pack.

## Next phase

Phase 2 (`theses-antitheses.md`) — BridgeMatrix across T1–T4 (alignment/divergence, explicit losses,
no silent fusion — in particular the T1-C4/DrainGuard non-match and the T2-C4/T3-C3 "scoped IO
responsibility vs. this repo's shared-connection turn-taking" contrast both flagged above need
honest scope lines there, not resolution here), scoped theses with anti-theses (NQD ≥3), and the
counterexample catalog (T5 and any others found in Bridge work).
