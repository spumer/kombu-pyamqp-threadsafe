---
dpf_id: "DPF-DEDICATED-IO-THREAD"
name: "Dedicated IO Thread: Ownership, Servicing, and Lifecycle in a Multithreaded Network Client"
kind: "Domain Principle Framework"
owner: ["architect"]
referenced_by: ["architect", "dev", "guardian", "cto"]
status: "active"
maturity: "conformant"
grounded_in: ["FPF E.4.DPF", "FPF E.4.DPF.DA", "FPF G.2", "FPF E.4.PFR", "FPF A.2.6", "FPF B.5.2.1", "FPF A.11", "FPF A.7", "FPF A.10", "FPF F.18", "FPF E.8"]
fpf_edition: "ailev/FPF@f7c7e93f (snapshot 2026-07-03; local copy ~/.claude/knowledge/fpf/FPF-Spec.md; E.4.DPF §1-§7/E.8/F.18 headers grepped live 2026-07-14; A.2.6/B.5.2.1/A.11/E.4.PFR line-anchors inherited from theses-antitheses.md, live-grepped the same day)"
date: "2026-07-14"
updated: "2026-07-14"
review_due: "2026-09-29"
---

# DPF-DEDICATED-IO-THREAD: Dedicated IO Thread — Ownership, Servicing, and Lifecycle in a Multithreaded Network Client

> A **dedicated IO thread** (or, more generally, a **dedicated ownership turn**) is whatever entity is,
> for some window of time, the sole unambiguous owner of a socket/connection and of the read/dispatch
> loop over it. This file is the pattern-language carrier (`E.4.DPF` publication-carrier shape) for
> that competency: how such ownership starts, how it is serviced while alive, how it stops cleanly,
> and how it survives reconnect and fork.

## Структурный отчёт носителя (CC-DPF.8 / PFM11)

- **For whom, and first task.** `architect`, designing or reviewing a multithreaded network client that
  wraps one non-thread-safe socket/connection (message-broker client is the motivating case; the
  pattern generalizes). First task: given a design question of the shape *"N application threads want
  to use one non-thread-safe connection — how do we structure ownership of the IO loop so nothing
  races the socket, shutdown is clean, and reconnect doesn't silently orphan a thread"*, use Section 4
  to recognize which ownership family (pinned thread / rotating leader / per-call turn) fits the
  constraints, and Section 6 to check the code against the known failure list before it is discovered
  by incident. Secondary readers: `dev` implementing against the resulting patterns; `guardian`/`cto`
  running the Phase 6 `E.4.DPF.DA` adequacy pass against this package (see Section 11 for current status).
- **What is foregrounded.** Eight patterns (Section 4): six built 1:1 from six SoTA-scoped theses in
  `references/theses-antitheses.md` — (1) single ownership has three non-equivalent instantiations,
  (2) the safe cross-thread crossing is one named narrow primitive, (3) the owner's job stays narrow,
  (4) shutdown is bounded, (5) reclaiming ownership after failure is idempotent, (6) AI-generated
  IO-thread code plausibly omits exactly these five invariants and needs an explicit review checklist —
  plus two closing a named coverage gap (`references/critic-review.md` §0.2): (7) write-side
  backpressure needs an explicit watermark pair, and (8) ownership's start-timing (lazy-on-first-use vs.
  explicit `start()`) must be named, not implied. Patterns 7–8 are grounded directly in web-verified
  sources (`references/web-verification-2026-07-14.md`); a formal Phase-1/2 backfill (`sota-research.md`
  CorpusLedger, `theses-antitheses.md` Thesis/NQD entries) for their sources remains an open follow-up
  outside this curator's mandate — flagged, not silently skipped (`references/
  quality-record-2026-07-14.md` §5).
  Patterns are the main language of this carrier and come before the source-pack summary and the
  heavy BridgeMatrix, per `E.4.DPF:4` publication order and PFM2 (`DPF-KNOWLEDGE-CURATION` Pattern 2).
- **What is deliberately coarsened or omitted, and where it returns.** Full ClaimSheets with every
  evidence anchor — `references/sota-research.md`. Full BridgeMatrix (alignment/divergence across the
  four traditions) and the full NQD ≥3 anti-thesis for each thesis — `references/theses-antitheses.md`.
  Per-source adopted/rejected decisions and the two `verified by file read` rows — `references/
  source-pack.md`. This project's own code (`DrainGuard`, `_transport_lock`, `channel_thread_bindings`,
  `_teardown_lock`) is cited only as the *instantiating worked slice* per pattern, never restated in
  full — return to `src/kombu_pyamqp_threadsafe/__init__.py`. General asyncio-loop mechanics, thread-pool
  fan-out patterns, and broker-selection comparisons are out of scope entirely (Section 1 non-use
  boundary), not merely coarsened.
- **Honest status of this carrier.** Architecture decision is folded into this structural report plus
  the `E.4.PFAD`-shaped Section 9. This package's self-declared status and the independent Phase 6
  (`guardian` completeness-critic + `E.4.DPF.DA` adequacy scoring) verdict are stated in Section 11 and
  the Conformance checklist at the end, not duplicated here — see `references/critic-review.md` and
  `references/critic-review-2026-07-14-r1.md` for the independent pass. Every literature claim in this
  file carries a per-claim trust-cue in Section 7 (SoTA-Echoing): `verified <date>, <URL>` where a live
  source was checked, `verified by file read` for the two repository-internal facts, `pretrain recall,
  не верифицирован` where it was not — see `references/web-verification-2026-07-14.md` and the Carrier
  note. Process history of this file's assembly and repair rounds is kept in `references/
  quality-record-2026-07-14.md`, not narrated here.

## Оглавление (PFM1 — patterns first)

1. [Patterns](#4-patterns-e8) — eight patterns, Section 4, the main language of this carrier.
2. [Context](#1-context-cc-dpf1) · [Source pack summary](#2-source-pack--g2-cc-dpf2) · [Forces](#3-forces-e4dpf3-scoped)
3. [Pattern relations](#5-pattern-relations-e4pfr) · [Typical errors](#6-typical-errors-e4dpf8) · [SoTA-Echoing](#7-sota-echoing-e4dpf11)
4. [Names](#8-names--f18-cc-dpf4) · [Relations](#9-relations-e4pfr) · [Quality & refresh](#11-quality--refresh-e4dpfda-cc-dpf7)
5. [Heterogeneous acceptance cases](#10-heterogeneous-acceptance-cases-d8)
6. [Artifacts](#artifacts-references--assets) · [Carrier note](#carrier-note-cc-dpf5) · [Conformance](#conformance-checklist-e4dpf7)

---

## 1. Context (CC-DPF.1)

- **Bounded context:** a thread (or a rotating/per-call "turn") that is, for some window, the sole
  owner of a socket/connection and of the read/dispatch loop over it, inside a multithreaded
  application. Covers: where/when ownership starts (lazy-on-first-use vs. explicit `start()`,
  lifecycle owner, daemon vs. non-daemon, naming); how it is serviced (poll/drain loop, cross-thread
  wakeup, timers/heartbeat, loop-level error handling, write backpressure); how it stops (graceful
  shutdown, join semantics/timeouts, in-flight work); how it survives reconnect and `fork()`.
- **Intended reader:** `architect` (primary); `dev` (secondary, implementing); `guardian`/`cto`
  (secondary, Phase 6).
- **First use:** recognize which ownership family (pinned / rotating-leader / per-call-turn) fits a
  given multithreaded-client design question, and check a design or a generated diff against the known
  failure list, before re-deriving the failures by incident.
- **Non-use boundary:**
  - **NOT** a general asyncio/Trio "how to write an event loop" primer — scoped to ownership/lifecycle
    of a resource-owning thread/turn, not coroutine-scheduling mechanics.
  - **NOT** a thread-pool-of-interchangeable-workers competency (`ThreadPoolExecutor` fan-out) — a pool
    owns no persistent exclusive resource across calls; this competency is specifically about a
    thread/turn that *is* the resource's access point for a stretch of time. Overlaps at the edge with
    sibling package `DPF-CONCURRENT-PROGRAMMING` (general locking/synchronization-primitive choice);
    that package owns the primitive choice, this one owns its IO-thread-shaped instantiation.
  - **NOT** a broker-selection/comparison guide (RabbitMQ vs. Kafka vs. NATS) — brokers appear only as
    *sources of the pattern in their client libraries*.
  - **NOT** a production-checked claim set — every claim carries a per-claim trust-cue (Section 7); most
    of the literature basis (S1–S13) is web-verified (`references/web-verification-2026-07-14.md`), but
    the AI-in-domain slice (Pattern 6) remains recall-only by construction (no single citable paper);
    this package's status per the independent Phase 6 pass is stated in Section 11, not restated here.

**Instantiating project:** `kombu-pyamqp-threadsafe` (this repository), a threadsafe rewrite of kombu's
pyamqp transport that deliberately does **not** pin one OS thread as the connection's sole owner for
its whole lifetime. Instead it uses a turn-taking variant: any thread may call `drain_events()`, a
`DrainGuard` (mutex + condition variable) ensures only one thread drives a given drain call at a time,
frames are dispatched only into the thread that owns the channel they arrived for
(`channel_thread_bindings`), and a lock-protected `_transport_lock` serializes direct socket access —
verified by direct file read (`src/kombu_pyamqp_threadsafe/__init__.py`, classes/attributes at
lines 353, 549, 555, 827/1103/1121). Secondary reference instance in the same bounded context: kombu's
own `kombu.asynchronous.hub.Hub`, an actual single-dedicated-thread reactor used elsewhere in the
kombu/Celery ecosystem — the "classical" comparison case (see Pattern 2, CE2).

---

## 2. Source pack — G.2 (CC-DPF.2)

> Full provenance registry — [`references/source-pack.md`](references/source-pack.md) (S1–S23). Full
> ClaimSheets — [`references/sota-research.md`](references/sota-research.md). Full Bridge —
> [`references/theses-antitheses.md`](references/theses-antitheses.md). Below is a summary only.

- **Adopted:** 4 independently-sourced traditions at `FamilyCoverageFloorK=3` margin — **T1** concurrency
  patterns (Reactor/Active Object/Half-Sync-Half-Async/Leader-Followers, POSA2 + Schmidt's Reactor
  paper), **T2** messaging/broker client libraries (pika, RabbitMQ Java client, Kafka producer, kombu
  Hub), **T3** event-loop/async-runtime tradition (libuv, Python `asyncio`, Redis `io-threads`), **T4**
  GUI/UI-thread tradition (Qt signal/slot, Android `Looper`/`Handler`) — plus a mandatory, explicitly
  lower-confidence **AI-in-domain slice** (S15, synthesized LLM-code-generation failure-mode
  pattern-matching, no single citable paper). Two rows are **verified by direct file read**,
  not recall: this repository's own `DrainGuard`/`_transport_lock`/`channel_thread_bindings`/
  `_teardown_lock` machinery, and installed kombu 5.6.2's `hub.py` (used to **falsify** a sub-claim, see
  next bullet).
- **Rejected / retired:** S3 (Lea, *Concurrent Programming in Java*) parked — overlaps S1/S2 from a
  Java-specific angle, no independent claim built on it (A.11 parsimony). S14 (psycopg2/libpq
  thread-affinity docs) parked as Tradition, used only as counterexample CE3 (different resolution
  family from Patterns 1–2: no owning thread/turn — see Pattern 5 CE3 for the precise boundary:
  psycopg2 itself locks the shared connection internally; what it lacks is a Pattern-2-shaped
  *crossing-into-an-owner's-loop* primitive, not locking as such — source `references/
  web-verification-2026-07-14.md` §1 row S14). **Retired premise (RP-1):**
  `sota-research.md`'s original T2-C4 claim that kombu `Hub` has a "self-pipe-style" cross-thread
  wakeup primitive was **falsified** by direct read of installed kombu 5.6.2 — no `os.pipe`/self-pipe,
  no `*_threadsafe` method, no `wakeup`; only non-threadsafe `call_soon`/`call_later` and
  `poll(timeout)`. The rest of T2-C4 (single-threaded reactor loop, one thread for the whole lifecycle)
  stands. This correction feeds Pattern 2's counterexample CE2 directly, and is the reason this
  repository built `DrainGuard` rather than reusing `Hub`.
- **Claim status:** T1–T4 literature claims = **fact** (durable, industry-consensus shape). S1–S13 are
  web-verified against live sources (`references/web-verification-2026-07-14.md`): 11 of 13 confirmed as
  stated, one (S6/Kafka) confirmed-and-sharpened, and the adjacent S14 counterexample corrected (see
  above) — trust-cues in Section 7 read `verified 2026-07-14, <URL>` per row. AI-slice claims
  (S15/AI-F1–F5, Thesis 6) = **opinion/hypothesis, explicitly lower-confidence** than T1–T4 — no single
  citable paper, synthesized over diffuse pretrain exposure, not re-verified (not a fetchable document).
  This repository's own five instantiating facts (`DrainGuard` et al.) = **fact, verified by file read**.
- **Currentness:** scope/sota-research/theses-antitheses/source-pack all dated 2026-07-06 → **2026-07-14
  for this DPF's own artifacts**, web-verification pass **2026-07-14**; `fpf_edition` grepped live for
  `E.4.DPF`/`E.8`/`F.18`, inherited for `A.2.6`/`B.5.2.1`/`A.11`/`E.4.PFR` from the same-day Phase 2
  grep. `review_due` 2026-09-29.

---

## 3. Forces / tensions (E.4.DPF:3, scoped)

> Domain-scoped tensions surfaced by the BridgeMatrix (`references/theses-antitheses.md` §1) and the
> six theses — not the *method's* own forces (those live in `DPF-AUTHORING/DPF.md` §3).

| # | Tension | Scope | How it resolves |
|---|---------|-------|------------------|
| F-1 | **Pinning vs. rotation vs. per-call turn-taking** (BridgeMatrix Ось A) | Choosing which of the three non-equivalent "owner" instantiations fits a given design | No single winner — Pattern 1 gives the recognition criteria (throughput bottleneck risk vs. lifecycle-simplicity vs. reconnect-orphan risk); the choice is part of the design task, not a detail to skip |
| F-2 | **"Do everything on the IO thread" simplicity vs. narrow-scoped owner responsibility** (BridgeMatrix Ось B) | Whether application/handler work runs on the owner thread itself | RabbitMQ's second dispatch pool and Redis's socket-edges-only `io-threads` both resolve it the same direction (narrow), by different mechanisms (Pattern 3) — "simpler" silently buys a slow-consumer-stalls-heartbeat failure mode |
| F-3 | **Bounded-join timeout too short (loses buffered work) vs. too long (shutdown hangs)** | Any owner thread with in-flight work at shutdown time | Not "bigger timeout is safer" — a documented balance (Pattern 4); `daemon=True` alone resolves neither side, it just hides the tension |
| F-4 | **Reconnect-idempotency-guard complexity vs. happy-path simplicity** | Design of the reconnect/re-ownership path under a burst of near-simultaneous errors | The guard is cheap (a non-blocking `acquire` + an in-flight flag) relative to the cost of N racing reconnects; happy-path-only code silently assumes single-threaded error delivery, which the bounded context explicitly denies (Pattern 5) |
| F-5 | **Generated-code fluency vs. actual invariant correctness** (AI-specific) | Reviewing LLM-produced dedicated-IO-thread/background-socket-thread code | Fluency is not evidence; Pattern 6 turns the five AI-F failure modes into an explicit review checklist so "looks idiomatic" stops being treated as "is correct" |
| F-6 | **Confidence of guidance vs. honesty about each claim's evidence grade** | Every claim in Sections 4/6/7 of this file | Every claim keeps its per-claim trust-cue (`pretrain recall` / `verified <date>, <URL>` / `verified by file read`); Section 11 states the package's self-declared status plainly and points to the independent Phase 6 verdict rather than asserting readiness itself — urgency to declare the package "ready" is resisted (Research-first / honest-status discipline, `DPF-AUTHORING` method) |
| F-7 | **Backpressure policy owned by the library vs. owned by the caller** | Deciding where the write-side watermark/pause-resume state machine lives | Not one right answer — `asyncio`/Netty embed the policy in the library (Pattern 7); libuv deliberately does not, exposing only the queue-size primitive for the caller to build its own loop around; either is legitimate, but leaving it unnamed (neither embedded nor caller-built) is not |
| F-8 | **Explicit `start()` visibility vs. lazy-on-first-use convenience** | When ownership of the loop/turn actually begins | Not one right answer — pika's two connection adapters and Kafka vs. aio-pika each resolve it differently (Pattern 8); the failure mode is not picking one, it is leaving the choice unstated so a caller cannot reason about when a thread/turn actually starts existing |

---

## 4. Patterns (E.8)

> Rule: **general SoTA principle before our particular instantiation** (A.1.1). Patterns 1–6 map 1:1
> onto one thesis each in `references/theses-antitheses.md` §2; the anti-theses (NQD ≥3) and full
> scope lines live there and are not repeated in full here (faithful pointer, not restated content).
> Patterns 7–8 ground their principle directly in web-verified sources (`references/
> web-verification-2026-07-14.md`) instead — they do not yet have a matching Phase-2 thesis/NQD entry,
> an explicitly open follow-up (`references/quality-record-2026-07-14.md` §5), not a silent gap.

---

### Pattern 1: Single Ownership With Non-Equivalent Instantiations

**Recognition** — a design question of the shape "N application threads share one non-thread-safe
socket/connection; who is allowed to touch it, and for how long."

**Principle (SoTA-grounded).**
Four independent traditions converge on the same two-part invariant: (1) access to a not-thread-safe
resource for some window belongs to exactly one owner; (2) the owner is reached by exactly one named
crossing primitive, not by "call any API from any thread under a shared lock." But *how* ownership is
held is not one shape — the concurrency-pattern literature alone names at least three non-equivalent
families: **pin** one thread for the resource's whole lifetime (Reactor/Half-Sync-Half-Async — a
single-threaded demultiplexing loop that must never block in a handler, or the failure stalls every
other registered handle on it); **rotate a leader** (Leader/Followers — a pool of threads takes turns
being "leader," promoting a follower to leader *before* processing an event so the wait slot is never
empty, trading a more complex handoff protocol for removing the single-pinned-thread bottleneck); or
**per-call turn** — no thread is *the* owner ongoingly, ownership is granted for one call at a time to
whichever thread already wants it. Choosing among these is part of the design task, not a detail to
elide after the fact (POSA2 [S1], ~2000; Schmidt's Reactor paper [S2], ~1995).

**Our instantiation (worked slice).**
This repository picks the third family, and does not pin one OS thread as the connection's lifetime
owner: any thread may call `drain_events()`, but `DrainGuard` (a mutex + condition variable, class at
`src/kombu_pyamqp_threadsafe/__init__.py:353`) grants single-flight ownership of one drain call at a
time to whichever thread already wants to drive it, while other simultaneous callers wait on the
outcome rather than being pre-elected as a successor — a deliberate, named departure from the classic
"1 OS thread = 1 owner for the connection's whole life" shape (verified by file read).

**Counterexample [A.11 Sharp Boundary] (CE1).**
Leader/Followers is *not* a drop-in description of `DrainGuard`, even though both "rotate who drives."
Leader/Followers rotates *who waits on the event source next* and pre-promotes a successor before the
current leader processes anything (a handoff protocol). `DrainGuard` instead gives the turn to
*whoever already wants to drain right now*, with no pre-elected successor — other callers just block on
a condition variable until the turn is free. Collapsing these into "it's all turn-taking" erases that
Leader/Followers solves "never leave the wait slot empty" while `DrainGuard` solves "never let two
threads read the socket at once"; different problems, different contracts (BridgeMatrix Ось A).
Separately: `ThreadPoolExecutor`-style worker pools (CE4) are *not* this pattern at all — a pool of
interchangeable workers owns no persistent exclusive resource across calls, so there is no "owner" to
instantiate in the first place (scope.md non-use boundary).

**Anti-pattern [E.8].**
Choosing "Redis io-threads parallelizes IO, so parallelize our IO thread too" or the reverse — pinning
one thread where a burst-error-tolerant design actually needs per-call turn-taking — without checking
which of the three families the throughput/lifecycle constraints actually call for (typical error #8
below; BridgeMatrix Divergence Ось A/B).

**Conformance.**
- The design names which of the three families (pin / rotate-leader / per-call-turn) it uses, and why,
  rather than leaving "who owns the socket right now" implicit.
- If the chosen family is per-call-turn, the guard structure gives single-flight ownership without
  silently degrading to "any thread that gets the lock first, forever" (i.e., it is bounded to one call).
- Reconnect/fork do not silently re-pin a thread that the design intended to rotate or turn-take (see
  Pattern 5).

**Connections [E.4.PFR].**
- **requires** Pattern 2 (however ownership is held, a non-owner still needs *some* safe way in).
- **composes** with Pattern 3 (the owner's *scope of work*, once chosen, layers on top of *who* owns).
- **requires** Pattern 5 for the per-call-turn and rotating-leader families specifically (reclaiming
  ownership after an error must not race).

---

### Pattern 2: One Named, Narrow Cross-Thread Crossing

**Recognition** — a non-owner thread needs to get work or a notification into the owner's loop without
racing the socket read.

**Principle (SoTA-grounded).**
Every tradition names exactly **one** narrow, documented-safe operation for this, not "any API is fine
under a lock": pika's `connection.add_callback_threadsafe(callback)` [S4]; libuv's `uv_async_send()`,
the sole documented exception to "most libuv API calls are unsafe from another thread while the loop
runs" [S9]; Python `asyncio`'s `loop.call_soon_threadsafe(callback, *args)`, with calling loop-affecting
APIs directly from another thread named as a documented anti-pattern [S10]; Qt's queued signal/slot
connection, which automatically marshals a cross-thread call onto the receiving object's owning thread
[S12]; Android's `Handler.post()` onto the main `Looper` [S13]. A lock around the shared object is not
the same primitive — a lock serializes access but does not *wake* a thread blocked inside
`poll()`/`epoll_wait()`; only the named crossing primitive does both jobs (marshal + wake).

**Our instantiation (worked slice).**
`_transport_lock` (an `RLock`, `src/kombu_pyamqp_threadsafe/__init__.py:549`) serializes direct socket
access, and `channel_thread_bindings` (a `defaultdict[int, set[int]]`, line 555) routes each arrived
frame only into the thread that owns the channel it belongs to — the repository's concrete answer to
"how does a non-driving thread's work reach the connection safely" (verified by file read).

**Counterexample [A.11 Sharp Boundary] (CE2).**
kombu's own `kombu.asynchronous.hub.Hub` looks like a ready-made dedicated-IO-thread reactor this
repository could have reused directly — same "single thread runs the event loop" shape as T2/T3. It is
**not** safely reusable from multiple threads as-is: a direct read of installed kombu 5.6.2's
`kombu/asynchronous/hub.py` (file read) found **no** `os.pipe`/self-pipe, **no**
`*_threadsafe` method, and **no** `wakeup` — only non-threadsafe `call_soon`/`call_later` and
`poll(timeout)`. A single-threaded reactor without a named safe crossing point is not a multithread-safe
owner; the absence of that primitive is exactly why this repository built `DrainGuard` +
`_transport_lock` instead of reusing `Hub`. (This also corrects an earlier over-claim in this
competency's own `sota-research.md` T2-C4 row — see Section 2 Retired premise.)

**Anti-pattern [E.8].**
Treating a `threading.Lock` wrapped around the connection object as equivalent to a named crossing
primitive (typical error #1 territory when combined with a bare-timeout poll loop) — it serializes but
cannot wake a thread already blocked inside the owner's `poll`/`epoll_wait`, producing a plausible loop
that is subtly, not obviously, wrong.

**Conformance.**
- Exactly one narrow, named operation exists for a non-owner thread to inject work/notification into
  the owner's loop; ad hoc direct calls into owner-only state from other threads are not present.
- That operation both marshals *and* wakes — a lock alone does not satisfy this pattern.
- Before treating any pre-existing loop/reactor as reusable across threads, its source is checked for
  an actual safe-crossing primitive rather than assumed present because the loop shape looks familiar.

**Connections [E.4.PFR].**
- **requires** Pattern 1 (there must be an owner to cross *into*).
- **composes** with Pattern 3 (the crossing primitive is how off-owner work gets queued for a
  narrow-scoped owner to eventually pick up).
- **conflicts with** treating "lock" and "crossing primitive" as synonyms (typical error #1).

---

### Pattern 3: Owner's Job Stays Narrow; Application Work Is Explicitly Pushed Off It

**Recognition** — deciding what the owning thread/turn is and is not allowed to do while it holds
ownership.

**Principle (SoTA-grounded).**
The owner's job is framing/heartbeat/socket read-write; a slow or blocking application callback must
not run on it, or it stalls frame reading and heartbeat processing for every consumer sharing that
owner (Reactor discipline: a blocking handler stalls every other registered handle, [S1]/[S2]).
RabbitMQ's Java client documents a deliberate split between the connection's frame-reading IO thread and
a separate, configurable consumer-dispatch pool specifically so slow consumer code cannot delay framing
or heartbeats [S5]. Redis kept the single-owner-thread boundary for the state-mutating part of its
design and *only* parallelized the socket read/parse and write/serialize edges when it added
`io-threads` in 6.0 — command execution against the keyspace stayed on the one main thread [S11]. Two
different mechanisms (a second pool vs. edge-only parallelism), same direction: keep the owner narrow.

**Our instantiation (worked slice).**
The repository's `_transport_lock` (line 549) and `channel_thread_bindings` (line 555) exist precisely
so that the drain-owning thread's job stays "read a frame, route it to the channel that owns it" —
application-level handler work happens in the channel-owning thread, not forced onto whichever thread
happened to win the current `DrainGuard` turn (verified by file read).

**Counterexample [A.11 Sharp Boundary] (CE5).**
Redis's `io-threads` feature is *not* evidence that "parallelize the whole IO thread" is the general
lesson — it is evidence for the opposite emphasis. Redis deliberately kept single-owner *for the
sensitive part* (keyspace mutation) and parallelized *only* the genuinely parallelizable socket edges
[S11]. Citing Redis to justify fully multithreading an owner's command-execution path inverts the
design decision it actually documents.

**Anti-pattern [E.8].**
Running application/handler logic directly inside the owner's poll/drain loop "because it's simpler
than adding a dispatch layer" (typical error #6) — works until a handler blocks or runs long, at which
point framing and heartbeat processing for every other consumer on that owner stall, and the broker may
tear down the connection for a missed heartbeat.

**Conformance.**
- The owner's loop body is inspectable as doing only framing/heartbeat/socket-edge work; any
  application callback invoked from it is either provably fast/non-blocking or is handed to a separate
  execution context (dispatch pool, queue, or an equivalent turn-boundary).
- A decision to add a second dispatch layer (or not) is explicit and sized to whether handler work can
  actually block — not a reflexive "always add a pool" nor a reflexive "never bother."

**Connections [E.4.PFR].**
- **composes** with Pattern 1 (the *scope* of the owner's work sits on top of *who* the owner is).
- **scope-dependent** on whether handler work can block — for a genuinely trivial handler, a second
  dispatch layer is unneeded complexity, not a universal requirement (BridgeMatrix Divergence Ось B).

---

### Pattern 4: Bounded Shutdown — Join With a Timeout, Not `daemon=True` Alone

**Recognition** — the owning thread/turn must be stoppable, and there may be in-flight work at the
moment shutdown is requested.

**Principle (SoTA-grounded).**
Kafka's Java producer keeps a background `Sender` thread that owns the network client; `producer.close()`
is documented to flush and join this thread, optionally with a timeout — and a too-short timeout is a
documented, named way to lose buffered messages [S6]. The tension is genuinely two-sided: `daemon=True`
with no `.join()` at all lets the process exit with in-flight work silently dropped; `.join()` with no
timeout can hang forever once the loop no longer reliably exits on its own (for instance, once reconnect
logic is layered on top of it). Neither extreme is safe; a bounded join is the documented middle
resolution.

**Our instantiation (worked slice).**
This project's own `_teardown_lock` (`threading.Lock`, `src/kombu_pyamqp_threadsafe/__init__.py:827`)
guards a single-flight teardown path (non-blocking `acquire` at line 1103, `release` at line 1121) —
the mechanism this repository uses to make sure a shutdown/reconnect transition has a bounded,
non-racing entry point rather than an unbounded wait or a silent drop (verified by file read).

**Counterexample [A.11 Sharp Boundary].**
`ThreadPoolExecutor.shutdown(wait=True)` (CE4, reused from Pattern 1) is not the same shape of problem:
its workers are interchangeable and hold no persistent per-owner in-flight state to flush before they
can be safely abandoned, so there is no equivalent to "did the one connection-owning thread finish its
one piece of in-flight protocol work" to reason about — bounded-join-of-an-owner and
drain-a-worker-pool solve different problems even though both involve "wait for threads to finish."

**Anti-pattern [E.8].**
`daemon=True` with no `.join()` call anywhere in the shutdown path (typical error #2) — the thread dies
with the process, and any publish/ack that was in flight at that instant is silently lost; this is not
a rare edge case once reconnect logic means shutdown can race an active drain.

**Conformance.**
- Every code path that stops the owner calls `.join(timeout=...)` with an actual, non-infinite,
  non-zero timeout — not bare `daemon=True`, and not an untimed `.join()`.
- The timeout's failure mode (what happens if the join times out) is handled, not left as an unhandled
  exception or a silent pass-through.
- In-flight work at shutdown time is either flushed before join or explicitly, visibly discarded — not
  ambiguous.

**Connections [E.4.PFR].**
- **requires** Pattern 1 (there must be a specific owner to join).
- **composes** with Pattern 5 (idempotent teardown is part of what "bounded" means once reconnects can
  race a shutdown).

---

### Pattern 5: Reclaiming Ownership After Failure Is Idempotent (Single-Flight-Guarded)

**Recognition** — the owner has failed or disconnected and must be re-established, potentially observed
by more than one thread at once.

**Principle (SoTA-grounded).**
A reconnect/retry path that does not check whether a reconnect is already in flight before starting
another one will, under a burst of near-simultaneous errors, spawn N threads/attempts all racing to
replace the same connection object. This is a documented, named old bug class (non-idempotent retry),
independent of any specific broker library — the fix is a single-flight guard (a non-blocking acquire
plus an explicit "already tearing down" flag), not merely "add a lock," because a lock alone still lets
every waiting caller execute its own reconnect one after another (N sequential instead of N parallel —
the same loss, spread over time instead of concurrent).

**Our instantiation (worked slice).**
`_teardown_lock.acquire(blocking=False)` (line 1103) combined with the `marked_for_teardown` flag
(set at line 455/467/496, checked at line 521 and elsewhere) is exactly this guard: a thread that loses
the race simply returns rather than launching a second, competing teardown/reconnect (verified by
file read) — the burst-of-errors scenario is not an edge case here, since a broker-side disconnect is by
construction visible to every thread that was draining the same connection at once.

**Counterexample [A.11 Sharp Boundary] (CE3).**
psycopg2/libpq's thread-affinity constraint looks like the same problem ("one connection, multiple
threads, don't race it") but resolves it in a structurally different family: there is no owning
thread/turn and no library-provided *idempotency guard to reclaim ownership* — because there is no
library-managed ownership object (Pattern 1/5's subject) in the first place, only a connection object
that happens to serialize concurrent calls. The raw **libpq** C API requires the C caller to serialize
`PGconn` access itself (PostgreSQL docs `libpq-threading.html`); **psycopg2**, the Python driver this
counterexample actually names, satisfies that requirement *internally* — its own documentation states
connection objects are thread-safe because psycopg2 serializes query execution/results retrieval on a
shared connection itself (psycopg2 project discussion + independent mirror; `references/
web-verification-2026-07-14.md` §1, row S14). So a psycopg2 caller does **not** need to add their own
lock — but that internal lock is still not the same *kind* of
primitive this competency is about: it is a plain mutex around synchronous calls, not a crossing-into-an-
owner's-loop primitive (Pattern 2) and not a reconnect-idempotency guard (Pattern 5) — reasoning about
"is our reconnect idempotent" still does not transfer to this family, because there is no owning
thread/turn to re-establish in the first place, only a connection object with an internal lock around it.

**Anti-pattern [E.8].**
An `on_error` handler that unconditionally starts a new reconnect thread/attempt on every observed
error (typical error #5) — under a burst, N threads race to replace one connection object; and its
close cousin, a `fork()` that leaves a stale owner reference around without re-establishing ownership in
the child (typical error #10) — the child inherits the file descriptor but not the parent's
owning-thread state, so ownership must be re-initialized explicitly, not assumed to have survived.

**Conformance.**
- A reconnect/re-ownership attempt checks an explicit "already in flight" state before starting, using a
  non-blocking acquire rather than a blocking lock that would just serialize redundant attempts.
- The guard covers `fork()` as a re-ownership trigger, not only network-error-triggered reconnects — a
  forked child re-establishes ownership rather than inheriting a stale reference.
- Under a simulated burst of concurrent errors, exactly one reconnect attempt proceeds; the rest observe
  "already in progress" and return without side effects.

**Connections [E.4.PFR].**
- **composes** with Pattern 4 (idempotent teardown is part of what makes shutdown genuinely bounded).
- **requires** Pattern 1 (there is a specific ownership arrangement being re-established, not a
  worker-pool slot being refilled).

---

### Pattern 6 (AI-specific): Generated IO-Thread Code — Explicit Invariant Checklist Before Trusting Fluency

**Recognition** — reviewing LLM-generated or LLM-assisted code that implements a background/dedicated
socket-owning thread, especially for a novel client library where no ready-made SoTA wrapper exists.

**Principle (SoTA-grounded, explicitly lower-confidence than Patterns 1–5).**
None of the failure modes below are new bug classes — missed wakeup, unjoined thread, false safety
assumption, wrong concurrency primitive, non-idempotent retry are exactly what the T1 literature has
warned about for decades. What plausibly *is* different with LLM-generated code is frequency and
plausibility: generated code tends to look complete and idiomatic while missing exactly these
invariants, so review effort has to explicitly shift from "does this compile and look right" to "does
this loop have a wakeup path, a bounded shutdown, and an idempotency guard" (synthesized pattern-matching
over diffuse pretrain exposure to LLM-code-generation postmortems, ~2022–2024 [S15] — no single citable
paper backs this section, and it is held below T1–T4 in this competency's own evidence hierarchy).

**Our instantiation (worked slice).**
The five-item checklist below is this pattern's payoff, mapped directly onto Patterns 1–5 above so a
reviewer does not need to rediscover the mapping: (1) is there a named wakeup primitive, not just a
bare-timeout poll (Pattern 2)? (2) is shutdown bounded with a real timeout, not `daemon=True` alone
(Pattern 4)? (3) does any comment/code justify shared-connection safety by citing the GIL, when the
actual protocol is multi-step (open channel → send frame → await reply is not atomic even under the
GIL) — exactly the class of bug this repository's `ThreadSafeChannel`/`ChannelCoordinator` machinery
exists to prevent (Pattern 1/2)? (4) does the concurrency primitive match the actual runtime
(`threading.Lock` inside coroutine code, or `asyncio.Queue` inside plain-`threading` code, are both
silent-failure shapes, not crashes)? (5) is reconnect/re-ownership guarded against firing once per
error under a burst (Pattern 5)?

**Counterexample [A.11 Sharp Boundary].**
Treating *this pattern's own confident tone* as equal-weight evidence to Patterns 1–5 is exactly the
mistake it warns against — this section is a synthesis without a citable source, explicitly flagged
lower-confidence in `sota-research.md`/`theses-antitheses.md`, and a genuine open web-verification
repair candidate (Section 11). Fluency of the writing is not evidence of the writing's correctness,
including this DPF's own AI-authored prose about AI-authored prose.

**Anti-pattern [E.8].**
Accepting a generated background-thread implementation because it "looks idiomatic" without walking the
five-item checklist against it — the whole point of naming AI-F1–F5 explicitly is that idiomatic-looking
code is exactly where these five invariants tend to go missing (typical errors #1, #2, #3, #4, #5 below
map directly onto this checklist's five items).

**Conformance.**
- A reviewer of generated dedicated-IO-thread code can point at where the wakeup primitive, the bounded
  join, the non-GIL protocol serialization, the runtime-matched primitive, and the reconnect guard each
  live in the code — or names which is missing.
- This pattern's own claims are not cited as equal-strength evidence to Patterns 1–5 in any downstream
  use of this DPF; the trust-cue is preserved, not smoothed over.

**Connections [E.4.PFR].**
- **composes** with Patterns 2/4/5 (the checklist operationalizes their invariants as review questions).
- **conflicts with** "looks idiomatic = correct" as a review heuristic.

---

### Pattern 7: Bounded Write Backpressure — Explicit Watermarks, Not an Unbounded Queue

> Closes a coverage gap named in the bounded context (§1) and the §8 glossary term "Backpressure":
> write-side backpressure was named as in-scope, but no pattern delivered on it until this one. Sources
> verified 2026-07-14, `references/web-verification-2026-07-14.md` §3 (S16–S18).

**Recognition** — a design question of the shape: "producers (application threads) can enqueue
writes/frames faster than the owner can drain them to the socket — what stops the queue from growing
without bound, and who finds out when to slow down?"

**Principle (SoTA-grounded).**
Three independent event-loop/network-runtime traditions converge on the same shape: backpressure is a
**named two-threshold (high/low watermark) state machine** on the write side with an **explicit
pause/resume signal** back to the producer — not an unbounded queue, and not a single trigger point
(which flaps rapidly at the boundary). Python `asyncio` transports expose `set_write_buffer_limits(high,
low)`; the protocol's `pause_writing()` fires once the buffered byte count reaches `high`, and
`resume_writing()` once it drops to `low` — two different thresholds by design, not one (S16, Python
docs `asyncio-protocol.html`, verified 2026-07-14). libuv does not bake the *policy* into the library for
the general stream case — it exposes `uv_stream_get_write_queue_size()` so the **caller** builds its own
high/low-watermark loop around `uv_write()`/`uv_try_write()` (S17, libuv docs `stream.html` + libuv
GitHub Discussion #3434 "how to back pressure correctly?", verified 2026-07-14) — same two-threshold
shape, different *ownership* of the policy (library-embedded vs. caller-built). Netty's `Channel`
exposes `WriteBufferWaterMark` (default low 32KB / high 64KB); `Channel.isWritable()` flips false at the
high mark and true again at the low mark, notified via `channelWritabilityChanged()` (S18, Netty 4.1 API
docs, verified 2026-07-14) — a third independent runtime, the same hysteresis shape again.

**Our instantiation (worked slice) — honestly flagged as an ABSENT worked slice, not a fabricated one.**
A repository-wide search (`grep -in "watermark\|backpressure\|high_water\|
pause_writing\|resume_writing" src/kombu_pyamqp_threadsafe/*.py`, 2026-07-14) found **no** watermark
pair, no pause/resume-equivalent callback, and no explicitly bounded producer-side queue on the
publish/write path. `DrainGuard`/`channel_thread_bindings` (Patterns 1–3) govern *read-side* turn
ownership and dispatch; the write side has no equivalent yet. This is a genuine, not-yet-closed gap in
the instantiating project, named here rather than silently glossed — see the new typical-error row and
open item below (A.10 Weightless-claims guard: no invented worked slice stands in for a real one).

**Counterexample [A.11 Sharp Boundary].**
A plain `queue.Queue()` feeding the owner's write loop *looks* like backpressure (`put()` can block once
the queue is literally full) but is **not** this pattern unless it has an explicit, deliberately-chosen
`maxsize` **and** the block-on-`put()` behavior is the actual signal the application code is designed
to react to. An unbounded queue (`maxsize=0`, the `queue.Queue()` default) or a "very large just in
case" bound defers the failure rather than solving it — exactly the §8 glossary's pre-existing "is not"
line for Backpressure: "An unbounded queue silently growing forever."

**Anti-pattern [E.8].**
Treating "we have a queue in front of the socket" as sufficient backpressure without a bound and an
observable producer-facing signal; or picking a single threshold (stop at N items, resume at N items)
instead of the documented two-threshold hysteresis, which flaps open/closed rapidly under bursty writes.

**Conformance.**
- The write path names an explicit bound (byte count or item count) with distinct high and low
  thresholds — not an unbounded structure and not one flip point.
- Crossing the high threshold produces an observable signal to the producer (a pause callback, a
  backpressure exception, or a blocking enqueue call); crossing the low threshold clears it.
- The two thresholds are genuinely different values (hysteresis), matching the SoTA shape in all three
  traditions above.

**Connections [E.4.PFR].**
- **composes** with Pattern 3 (backpressure bookkeeping is IO-owner scope, not application work).
- **requires** Pattern 2 (however "pause" is communicated to a producer thread, it needs *some* safe
  crossing into/out of the owner, not an ad hoc side-channel).

---

### Pattern 8: Start-Timing & Lifecycle Ownership — Lazy-on-First-Use vs. Explicit `start()`, Named and Owned

> Closes the second half of the same coverage gap: the bounded context (§1) names "lazy-on-first-use vs.
> explicit `start()`, lifecycle owner, daemon vs. non-daemon, naming" as first-class scope; Pattern 1
> answers *which family* owns, this pattern answers *when* ownership begins. Sources verified
> 2026-07-14, `references/web-verification-2026-07-14.md` §3 (S19–S23).

**Recognition** — a design question of the shape: "when does the owner (thread/turn) actually begin
driving IO — on first use, or at an explicit call — and who is responsible for stopping and, if needed,
restarting it?"

**Principle (SoTA-grounded).**
Messaging-client libraries resolve this axis at least two documented, non-equivalent ways, and **name**
the choice rather than leaving it implicit. pika's `SelectConnection` requires the caller to explicitly
create the IO-loop object and call `.ioloop.start()` — typically from a thread the caller itself spawns
— making the start of ownership a distinct, caller-visible step; `BlockingConnection`, in the same
library, instead activates its internal poller as a side effect of establishing the connection, with no
separate "start" call at all (S19, pika docs `select.html`/`blocking.html`, verified 2026-07-14).
`aio-pika` deliberately moved connection establishment **out of** `__init__` and into an explicit,
awaited `connect()` factory function specifically so that "when does ownership start" is a distinct,
name-able, awaitable step rather than a side effect of object construction (S20, `aio_pika/
connection.py`, verified 2026-07-14). Kafka's Java producer takes the opposite, eager-pinned position:
the background `Sender` I/O thread is started as a side effect of constructing `KafkaProducer` itself,
not a separate call — which is exactly why forgetting `close()` leaks a live thread (S21/S6, Kafka
producer Javadoc, verified 2026-07-14 — same source already adopted for Pattern 4, new angle here).
`rabbitpy` names its own choice explicitly in source: `_connect()` creates **and** starts a daemonized
IO thread as one explicit step (S22, `rabbitpy/connection.py`, verified 2026-07-14). A fourth, distinct
position: `confluent-kafka`'s Python producer defers the actual network work and delivery-report
processing until the caller explicitly calls `poll()`/`flush()` — the client is constructed lazily with
respect to *processing*, even though the underlying `librdkafka` background thread itself is created at
construction (verified 2026-07-14, Confluent docs) — a caller-visible reminder that "when does the
thread exist" and "when does it actually do the work it was started for" are two different, both
name-able, questions. The convergence is not "lazy is right" or "explicit is right" — every mature
library **names** which one (or which mix) it does, rather than leaving "when does ownership actually
begin" to be discovered by reading source or by incident.

**Our instantiation (worked slice).**
This repository sidesteps the lazy-vs-explicit-start dichotomy rather than picking a side within it:
because ownership is per-call turn-taking (`DrainGuard.start_drain()`, Pattern 1), there is no
persistent background thread whose start needs naming at all — "start" is implicit in each application
thread's own call to `drain_events()`. Verified by file read and repository-wide
search (`src/kombu_pyamqp_threadsafe/__init__.py`; `grep -n "daemon\|Thread(" src/
kombu_pyamqp_threadsafe/__init__.py` found no `Thread(...)` construction and no `daemon=` flag anywhere
in the module, 2026-07-14): this repository's own library code never spawns an OS thread of its own.
This is a legitimate, named third position — no dedicated thread to start lazily *or* explicitly — that
is a direct consequence of Pattern 1's family choice, stated out loud here for the first time in this
package.

**Counterexample [A.11 Sharp Boundary].**
A class whose `__init__` silently opens a socket and spawns a thread (an *undocumented* eager start)
superficially resembles Kafka's eager-pinned choice but is **not** the same: Kafka's eager start is
documented and paired with a documented `close()` obligation. An undocumented eager start gives the
caller no way to learn a thread now exists without reading the source, and no natural place to be told
to call a matching shutdown — same mechanism (thread created in a constructor), missing the naming
discipline that makes Kafka's choice safe to depend on.

**Anti-pattern [E.8].**
Starting a background thread as an invisible side effect of an unrelated call (e.g., the first
`publish()`), undocumented, so a caller who never exercises that path never triggers thread creation and
a caller who does has no explicit lifecycle hook to reason about for shutdown — an un-nameable owner
cannot be `.join()`-ed correctly (Pattern 4) because the caller does not reliably know it exists.

**Conformance.**
- The design states, in one sentence, whether ownership begins lazily (first use) or at an explicit
  call, and names the exact trigger (a method, a context-manager `__enter__`, a constructor).
- If there is a persistent background thread, its creation point is documented and paired with an
  equally explicit stop/`close()` obligation (composes with Pattern 4).
- If the family is per-call turn-taking (Pattern 1) with no persistent thread, that fact is stated
  explicitly rather than left as an unanswered question implied by pinned-thread framing.

**Connections [E.4.PFR].**
- **requires** Pattern 1 (which ownership family is chosen constrains whether "start" is even a
  meaningful separate event).
- **composes** with Pattern 4 (an explicit start needs an equally explicit, bounded stop).

---

## 5. Pattern relations (E.4.PFR)

| Pattern | P1 Ownership Families | P2 Named Crossing | P3 Narrow Owner Scope | P4 Bounded Shutdown | P5 Idempotent Reclaim | P6 AI Checklist | P7 Backpressure | P8 Start-Timing |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **P1 Ownership Families** | — | requires (owner needs an entry point) | composes (scope layers on who) | requires (a specific owner to join) | requires (re-establishing, not refilling) | uses (checklist item 3) | — | requires (P8) |
| **P2 Named Crossing** | requires | — | composes (crossing feeds the narrow-scope owner) | — | — | uses (checklist item 1) | requires (P7 needs a crossing to signal pause) | — |
| **P3 Narrow Owner Scope** | composes | composes | — | — | — | — | composes (backpressure bookkeeping is owner scope) | — |
| **P4 Bounded Shutdown** | requires | — | — | — | composes (idempotent teardown) | uses (checklist item 2) | — | composes (explicit start needs explicit stop) |
| **P5 Idempotent Reclaim** | requires | — | — | composes | — | uses (checklist item 5) | — | — |
| **P6 AI Checklist** | uses | uses | — | uses | uses | — | — | — |
| **P7 Backpressure** | — | requires | composes | — | — | — | — | — |
| **P8 Start-Timing** | requires | — | — | composes | — | — | — | — |

**Sequence:** P1 (name which ownership family the design uses) → P8 (name when that ownership actually
begins) → P2 (name the one safe crossing into it) → P3 (keep the owner's job narrow) → P7 (bound the
write side with an explicit watermark) → P4 (make it stoppable, bounded) → P5 (make re-establishing it
idempotent) ↔ P6 (operationalize P1/P2/P4/P5 as a review checklist specifically for generated code, not
a separate design decision).

**Conflict, not silently fused (BridgeMatrix Divergence, no silent fusion):** the *choice* among P1's
three ownership families and the *choice* of whether P3 needs a second dispatch pool are each
scope-dependent, not resolved once for all designs — collapsing either into a single universal answer
is exactly the mistake Section 6's typical errors #8 and #6 name. P7's *choice* of who owns the
backpressure policy (library vs. caller, F-7) and P8's *choice* of lazy-vs-explicit start (F-8) are
likewise scope-dependent, not resolved once for all designs — see Section 3 Forces.

---

## 6. Typical errors (E.4.DPF:8)

> Symptom → why → fix → source. Beginner and experienced-practitioner-from-stale-practice mistakes
> together (D7); AI-specific rows marked. Rows 1–10 are faithfully carried from `references/
> theses-antitheses.md` §4 (full NQD anti-theses there), not re-derived here. Rows 11–12 correspond to
> Patterns 7–8 — not yet backfilled into `theses-antitheses.md` §4 (curator-mandate boundary, see
> `references/quality-record-2026-07-14.md` §5).

| # | Symptom | Why it happens | Fix | Source |
|---|---------|-----------------|-----|--------|
| 1 (AI) | Loop polls with a bare `select(..., timeout=1.0)` as the *only* way to notice external state (shutdown flag, new work) | Missed/weak wakeup: generated code produces a plausible loop with no wakeup primitive, "works in a demo" | Add a named wakeup (self-pipe/`eventfd`/`uv_async_send`-equivalent/condition variable); timeout is a safety net, not the mechanism | AI-F1; ME2; T3-C1/C2; Pattern 2 |
| 2 (AI) | `daemon=True` and `.join()` is never called, or `.join()` has no timeout | Unsafe shutdown semantics: daemon drops in-flight work; unbounded join can hang | Bounded shutdown: explicit `.join(timeout)`; flush before exit | AI-F2; T2-C3 (Kafka `close(timeout)`); Pattern 4 |
| 3 (AI) | Code/comment justifies shared-connection safety by citing the CPython GIL | Fluency-as-safety: the GIL serializes bytecode operations, not multi-step protocol transitions | Explicitly serialize protocol steps (`_transport_lock` + turn-owner), do not rely on the GIL | AI-F3; this repo's `ThreadSafeChannel`/`ChannelCoordinator`; Pattern 1 |
| 4 (AI) | `asyncio.Lock`/`asyncio.Queue` inside plain-`threading` code (or `threading.Lock` inside a coroutine) | Wrong primitive under runtime: both idioms answer the same natural-language prompt ("make this thread-safe") | Choose the primitive matching the *actual* runtime; do not mix asyncio- and threading-primitives | AI-F4; Pattern 2 |
| 5 (AI) | Reconnect code reopens the socket / spins a new thread on *every* error without checking "already in flight" | Non-idempotent retry: under a burst, N threads race to replace one connection object | Single-flight guard: non-blocking `acquire` + an in-flight flag before reconnecting | AI-F5; ME3; this repo's `_teardown_lock`; Pattern 5 |
| 6 | A slow/blocking application callback runs on the IO owner, stalling framing/heartbeat for everyone | Reactor discipline ("don't block the handler") violated; "one thread is simpler" | Move application work off the owner (second pool) when it can block; otherwise heartbeats miss and the broker tears the connection down | T1-C3; T2-C2 (RabbitMQ pools); Pattern 3 |
| 7 | A single-thread reactor (e.g. kombu `Hub`) is reused from multiple threads assuming it is "already a thread-safe IO thread" | A single-thread reactor is mistaken for a multithread-safe owner; it has no cross-thread primitive | Check for an actual named safe-crossing point *before* multithreaded reuse; if absent, build a turn/lock layer (as `DrainGuard` does) | CE2; verified by file read (kombu 5.6.2 source) |
| 8 | "Redis io-threads → parallelize the whole IO thread" — or the opposite: pinning one thread where turn-taking would suffice | Scope mischaracterization: conflating "parallelize the socket edges" with "parallelize the mutation"; or over-engineering ownership | Keep single-owner for the sensitive part, parallelize only genuinely parallelizable edges (Redis's own lesson); choose the ownership instantiation to fit actual throughput needs | T3-C3; T1-C4; Patterns 1/3, BridgeMatrix Divergence Ось B |
| 9 (research/AI) | A source is cited as having a property ("has a cross-thread wakeup primitive") without checking that it actually does | Over-attribution/fluency-as-authority — exactly what happened to this competency's own first-pass claim about kombu `Hub` | Verify a load-bearing claim by direct source read, even when web access is unavailable; a broken attribution is a stop-and-correct finding, not a footnote | Section 2 Retired premise (T2-C4 falsified); CE2 |
| 10 | `fork()` happens while a socket-owning thread is alive; the child inherits the file descriptor but not the owning thread | The owning thread does not survive `fork()` — only the calling thread exists in the child; the fd is now orphaned | Re-initialize the connection/ownership arrangement in the child after fork (an `ensure()`-style fork guard); never share a live socket across a fork silently | scope.md (survival across fork); AI-F2 (kin failure); Pattern 5 |
| 11 | A write path has a queue in front of the socket but no bound and no producer-facing signal — it just grows | Backpressure conflated with "we have a queue"; no explicit high/low watermark or pause/resume signal | Add an explicit two-threshold watermark pair with an observable pause/resume signal (Pattern 7) | S16–S18 (`references/web-verification-2026-07-14.md`); Pattern 7 — *not yet backfilled into `theses-antitheses.md` §4, see `quality-record-2026-07-14.md` §5* |
| 12 | A background thread is spun up as an invisible side effect of an unrelated call (e.g. the first `publish()`), undocumented | Start-timing left implicit; caller has no way to know a thread now exists or when to stop it | Name whether ownership starts lazily or explicitly, document the trigger, pair with an explicit stop (Pattern 8) | S19–S23 (`references/web-verification-2026-07-14.md`); Pattern 8 — *not yet backfilled into `theses-antitheses.md` §4, see `quality-record-2026-07-14.md` §5* — includes confluent-kafka's poll/flush-deferred distinction |

---

## 7. SoTA-Echoing (E.4.DPF:11)

| # | Claim | Source | Status in claim sheet | Adoption in this DPF |
|---|-------|--------|------------------------|-----------------------|
| SE-1 | Active Object: single scheduler thread + request queue gives single-writer safety without caller-side blocking | Lavender & Schmidt / POSA2 [S1], ~1995/2000 | fact (durable) / `verified 2026-07-14, https://www.wiley.com/en-us/shop/general-introductory-computer-science/pattern-oriented-software-architecture-volume-2-patterns-for-concurrent-and-networked-objects-p-9781118725177` | Adopted: Pattern 1 principle |
| SE-2 | Reactor: single demux-loop thread must never block a handler, or every other registered handle stalls | Schmidt [S2], ~1995; POSA2 [S1] | fact / `verified 2026-07-14, https://www.dre.vanderbilt.edu/~schmidt/PDF/reactor-siemens.pdf` | Adopted: Pattern 1 principle, Pattern 3 principle |
| SE-3 | Leader/Followers: rotate leadership, pre-promote a follower *before* processing an event, to remove the pinned-thread bottleneck | POSA2 [S1] | fact / `verified 2026-07-14` (same source as SE-1) | Adopted: Pattern 1 (family #2); scoped away from `DrainGuard` in CE1 |
| SE-4 | pika: Connection/Channel not thread-safe; drive from one thread; marshal via `add_callback_threadsafe` | pika docs [S4], ~2019–2023 | fact / `verified 2026-07-14, https://pika.readthedocs.io/en/stable/faq.html` | Adopted: Pattern 2 principle |
| SE-5 | RabbitMQ Java client splits frame-reading IO thread from a separate consumer-dispatch pool | RabbitMQ Java client guide [S5], ~2015–2023 | fact / `verified 2026-07-14, https://www.rabbitmq.com/client-libraries/java-api-guide` | Adopted: Pattern 3 principle |
| SE-6 | Kafka producer: background `Sender` thread owns the socket; `close(timeout)` documented flush+join; too-short timeout loses buffer | Kafka producer internals [S6], ~2013–2016 | fact / `verified 2026-07-14, https://cwiki.apache.org/confluence/display/KAFKA/KIP-15+-+Add+a+close+method+with+a+timeout+in+the+producer` | Adopted: Pattern 4 principle |
| SE-7 | kombu `Hub`: single-threaded reactor loop, one thread for the whole lifecycle | kombu source [S7], ~2013–2016 | fact (this part) / `verified by file read` (installed kombu 5.6.2, this repository's own dependency) | Adopted: Pattern 2 counterexample (CE2) context |
| SE-8 | kombu `Hub` has a self-pipe-style cross-thread wakeup primitive | kombu source [S7] (Phase 1 claim) | **retired/falsified** — `verified by file read` (kombu 5.6.2) | NOT adopted — explicitly retired, cited only as the corrected CE2 |
| SE-9 | libuv: `uv_run` must run from one thread; `uv_async_send()` is the sole documented safe cross-thread call | libuv docs [S9], stable ~2013+ | fact / `verified 2026-07-14, https://docs.libuv.org/en/v1.x/design.html` | Adopted: Pattern 2 principle, ME2 |
| SE-10 | `asyncio`: loop must run on its owning thread; `loop.call_soon_threadsafe()` is the sanctioned cross-thread scheduling call; direct loop-API calls from another thread are a documented anti-pattern | Python `asyncio` docs [S10], stable ~3.4+ | fact / `verified 2026-07-14, https://docs.python.org/3/library/asyncio-dev.html` | Adopted: Pattern 2 principle, ME2 |
| SE-11 | Redis kept single-owner for keyspace mutation; `io-threads` (6.0) parallelizes only socket read/parse and write/serialize edges | Redis 6.0 docs + antirez rationale [S11], 2020 | fact (for 6.0-era design) / `verified 2026-07-14, https://github.com/redis/redis-doc/pull/1408/files` | Adopted: Pattern 3 principle, CE5 |
| SE-12 | Qt: GUI objects accessed only from their owning thread; cross-thread signal/slot calls are automatically queued onto the receiving object's thread | Qt docs [S12], stable Qt4/5/6 | fact / `verified 2026-07-14, https://doc.qt.io/qt-6/threads-qobject.html` | Adopted: Pattern 2 principle (non-networking instance) |
| SE-13 | Android: main-thread `Looper`/`MessageQueue`; other threads must post via `Handler`; touching UI off-thread is a runtime error class, not a style violation | Android Developers docs [S13], long-stable | fact / `verified 2026-07-14, https://developer.android.com/reference/android/os/Looper` | Adopted: Pattern 2 principle (non-networking instance) |
| SE-14 | Raw libpq (C API) requires the caller to serialize `PGconn` access; psycopg2 itself locks the shared connection internally — the Python-level caller does not need to supply an external mutex. What psycopg2 still lacks is a Pattern-2-shaped crossing-into-an-owner's-loop primitive, not locking as such (`references/web-verification-2026-07-14.md` §1 row S14) | psycopg2/libpq docs [S14] | fact / `verified 2026-07-14, https://www.postgresql.org/docs/current/libpq-threading.html` (libpq) + `https://github.com/psycopg/psycopg2/discussions/1652` (psycopg2 internal locking); parked as Tradition | Adopted: Pattern 5 counterexample (CE3) only |
| SE-15 | AI-F1–F5: missed wakeup / unsafe shutdown / GIL-fallacy / wrong primitive / non-idempotent reconnect are old bug classes that generated code plausibly reproduces at higher frequency and higher apparent plausibility | Synthesized pattern-matching, diffuse pretrain exposure [S15], ~2022–2024 | opinion/hypothesis, explicitly lower-confidence than SE-1–SE-14; not re-verified (not a fetchable document, see Section 11 refresh triggers) | Adopted: Pattern 6 entirely; typical errors #1–#5 |
| SE-16 | `asyncio` transports: `set_write_buffer_limits(high, low)` + `pause_writing()`/`resume_writing()` is a two-threshold write-backpressure mechanism | Python `asyncio` docs [S16] | fact / `verified 2026-07-14, https://docs.python.org/3/library/asyncio-protocol.html` | Adopted: Pattern 7 principle |
| SE-17 | libuv exposes `uv_stream_get_write_queue_size()` so the caller builds its own high/low-watermark backpressure loop; the policy itself is not embedded in the library | libuv docs + GH Discussion #3434 [S17] | fact / `verified 2026-07-14, https://docs.libuv.org/en/v1.x/stream.html` | Adopted: Pattern 7 principle |
| SE-18 | Netty `Channel.isWritable()` flips at `WriteBufferWaterMark` high/low marks (default 64KB/32KB), signalled via `channelWritabilityChanged()` | Netty 4.1 API docs [S18] | fact / `verified 2026-07-14, https://netty.io/4.1/api/io/netty/channel/WriteBufferWaterMark.html` | Adopted: Pattern 7 principle |
| SE-19 | pika `SelectConnection` requires an explicit, caller-visible `.ioloop.start()`; `BlockingConnection` activates its poller internally with no separate start step | pika docs [S19] | fact / `verified 2026-07-14, https://pika.readthedocs.io/en/stable/modules/adapters/select.html` | Adopted: Pattern 8 principle |
| SE-20 | `aio-pika` moved connection establishment out of `__init__` into an explicit awaited `connect()` factory | aio-pika source [S20] | fact / `verified 2026-07-14, https://github.com/mosquito/aio-pika/blob/master/aio_pika/connection.py` | Adopted: Pattern 8 principle |
| SE-21 | Kafka's Java producer starts its background `Sender` I/O thread as a side effect of `KafkaProducer` construction (eager, not lazy) | Kafka producer Javadoc [S21/S6] | fact / `verified 2026-07-14, https://kafka.apache.org/22/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html` | Adopted: Pattern 8 principle |
| SE-22 | `rabbitpy`'s `_connect()` explicitly creates and starts a daemonized IO thread as one named step | rabbitpy source [S22] | fact / `verified 2026-07-14, https://github.com/gmr/rabbitpy/blob/master/rabbitpy/connection.py` | Adopted: Pattern 8 principle |
| SE-23 | `confluent-kafka`'s Python producer defers delivery-report processing to explicit `poll()`/`flush()` calls even though its underlying `librdkafka` background thread is created eagerly at construction — a fourth, distinct start-timing position | confluent-kafka docs [S23] | fact / `verified 2026-07-14, https://docs.confluent.io/kafka-clients/python/current/overview.html` | Adopted: Pattern 8 principle |

---

## 8. Names — F.18 (CC-DPF.4)

> Candidates for `project/glossary.md` — **not migrated** here; this project has no `glossary.md` at the
> time of writing (confirmed absent, `source-pack.md` open provenance question #4). Source:
> `references/sota-research.md` G.2c Operator/Object Inventory.

| Term | Definition | Is not |
|------|------------|--------|
| **Loop-owner thread** | The thread that, for some window, is the sole entity allowed to drive the poll/drain/dispatch loop over the shared resource | A thread that merely holds a reference to the connection object |
| **Turn / single-flight ownership** | A weaker variant of loop-owner thread: ownership is per-call, not per-thread-lifetime; any thread may take a turn, one at a time | A permanently pinned owner thread |
| **Cross-thread wakeup/marshal primitive** | The single, narrow, documented-safe operation for a non-owner thread to inject work or a notification into the owner's loop | A lock wrapped around the shared object (serializes, does not wake) |
| **Work/request queue (mailbox)** | The structure a non-owner thread enqueues onto instead of touching owned state directly | Direct method calls on the owned object from another thread |
| **Backpressure** | What happens when producers enqueue faster than the owner thread can drain | An unbounded queue silently growing forever |
| **Graceful shutdown / bounded join** | The owner thread is stoppable with a bound on wait time | `daemon=True` used as the entire shutdown strategy |
| **Reconnect idempotency guard** | A check that a reconnect/re-ownership attempt is not already in flight before starting another | A plain lock with no "already in progress" flag |
| **Scoped IO-thread responsibility** | The owner's job kept deliberately narrow (framing/heartbeat/socket read-write), application work explicitly pushed off it | "Do everything on the IO thread because it's one thread anyway" |
| **Thread affinity without ownership (contrast term)** | A resource not handed to any owner thread/turn, with no library-provided reconnect-idempotency guard to reclaim — psycopg2 locks the shared connection internally, but that internal lock is not this kind of primitive; see Pattern 5 CE3 and `references/web-verification-2026-07-14.md` | This competency's subject — kept only as the CE3 boundary marker |

**Provisional (not settled):** "owner" vs. "turn" as the primary noun when the design is per-call
turn-taking rather than a pinned thread — both are used in this file depending on which family is
being discussed; not resolved into one canonical term here.

---

## 9. Relations (E.4.PFR)

| Relation | Target | Function | Note |
|----------|--------|----------|------|
| uses (method) | `DPF-AUTHORING` §4 (6-phase spine) | dependency | This assembly is that method's Phase 4–5 output for one competency |
| grounded_in | FPF `E.4.DPF` | meta | Canon skeleton, `CC-DPF.1–9`, publication order — grepped live 2026-07-14 (lines 66066–66434) |
| grounded_in | FPF `G.2` | meta | CorpusLedger/ClaimSheets/BridgeMatrix harvest method, applied in Phases 1–2 |
| grounded_in | FPF `E.4.PFR` | meta | Relation functions (compose/require/conflict/scope-dependent) used in Sections 4–5 |
| grounded_in | FPF `A.2.6` | meta | ClaimScope discipline — every thesis's scope line in `theses-antitheses.md` |
| grounded_in | FPF `B.5.2.1` | meta | NQD anti-thesis discipline behind each thesis (full form in `theses-antitheses.md`) |
| grounded_in | FPF `A.11` | meta | Sharp Boundary — every counterexample (CE1–CE5) in Section 4 |
| grounded_in | FPF `A.10` | meta | Evidence Graph — trust-cues, the CE2/T2-C4 falsification, Section 11 honesty |
| scope_boundary | `DPF-CONCURRENT-PROGRAMMING` (sibling package, this catalog) | peer | Owns general locking/synchronization-primitive choice; this package owns their IO-thread-shaped instantiation — overlap named in scope.md, not resolved here |
| instance_of | `kombu-pyamqp-threadsafe` (this repository) | dependency | Motivating and primary worked-slice source for Patterns 1–6 (verified by file read); Patterns 7–8's worked slices are honestly-absent checks against the same source (verified by file read that the mechanism does not yet exist) |
| contrast_case | `kombu.asynchronous.hub.Hub` | dependency | Secondary reference instance in the same bounded context — the "classical" single-thread reactor this repository deliberately did not reuse (CE2) |
| coordinates_with | `references/source-pack.md` | dependency | Full provenance ledger this Section 2 summarizes |
| coordinates_with | `references/theses-antitheses.md` | dependency | Full BridgeMatrix/theses/counterexamples/typical-errors this file's Sections 4/6 compress faithfully |
| evaluated_by | Phase 6 (`guardian`, `E.4.DPF.DA`) | dependency | See Section 11 for current status (`admissibleForDeclaredDPFUse`, round 2); this file's status line is updated only by the critic (Mode C), never self-assigned by the curator |

---

## 10. Heterogeneous acceptance cases (D8)

> Three cases unlike the motivating example (this repository's own `DrainGuard`/AMQP design), drawn from
> material already harvested in `references/` — no new research performed to produce them (A.11
> parsimony). Honestly marked: none of these were run or tested by this project; they are
> literature-grounded transfer probes, not executed evidence.

| # | Case | How it differs from the motivating example | How the patterns transfer | Status |
|---|------|----------------------------------------------|------------------------------|--------|
| **HC-1** | **Kafka Java producer client**, used from a multithreaded service | Different broker family entirely (Kafka, not AMQP); ownership is a **pinned** background `Sender` thread (Pattern 1 family #1), not a per-call turn like `DrainGuard` | P1 (pinned dedicated thread — the classic instantiation, contrasted with this repo's turn-taking choice) + P2 (`RecordAccumulator.append` as the mailbox a caller enqueues onto, not a direct socket touch) + P4 (`producer.close(timeout)` as the textbook bounded-join instance, including the documented "too-short timeout loses the buffer" failure) all transfer cleanly. P5 (idempotent reclaim) is **not** directly evidenced by [S6] — flagged, not assumed | literature-grounded ([S6]), **worked-evidence pending** — not executed by this project |
| **HC-2** | **Android background socket/serial-port read thread**, marshaling to the UI via `Looper`/`Handler`** | Not networking-as-primary-subject at all — the "owner" is a background worker thread and the "cross-thread crossing" (`Handler.post()`) runs in the *opposite* direction, from the IO thread *into* the UI-owning thread, not the reverse | Shows P2's "one named narrow crossing primitive" principle transposed clean out of the messaging/broker domain into mobile GUI — same shape (`Handler.post()`), same discipline (`CalledFromWrongThreadException` as a documented runtime-error class, not a style nit, [S13]), completely different reason the ownership boundary exists (UI-thread affinity, not socket safety) | literature-grounded ([S12], [S13]), **worked-evidence pending** |
| **HC-3** | **Redis server-side `io-threads`** (not a client library at all) | The pattern applies on the **server** side of a connection, and the entity being protected is an entire keyspace's mutation path, not one socket wrapper; also the one case in this set where "parallelize more" was the change being made, and the design explicitly did *not* parallelize the sensitive part | Central, not incidental, demonstration of Pattern 3: single-owner is kept for the mutation-sensitive part, and *only* the genuinely parallelizable socket edges are pulled out — directly falsifies the CE5 misreading ("Redis proves parallelize everything") by being the source of that very counterexample | literature-grounded ([S11]), **worked-evidence pending**; this repository is a *client*-side case, so HC-3 is a genuinely different locus for the same invariant, not a restatement |

**Selection rationale.** Each case closes a different axis of D8 risk: HC-1 exercises the *pinned*
ownership family this repository deliberately did not choose (contrast within Pattern 1's own scope);
HC-2 exercises transfer *out of networking entirely* (GUI/embedded, not messaging); HC-3 exercises a
*different locus* for the same invariant (server, not client) and is also the literal source of one of
Section 4's own counterexamples (CE5), so the pattern set is shown working both as design guidance and
as the origin of its own sharp-boundary correction.

---

## 11. Quality & refresh (E.4.DPF.DA, CC-DPF.7)

**Package status (independent Phase 6, `guardian`/critic, 2026-07-14, Mode C round 2):
`admissibleForDeclaredDPFUse`** — all eleven `E.4.DPF.DA` coordinates are at or above the floor-4 for
reliance-bearing `architect` use; round 1's single below-floor finding (`D5`, PFM7 process-residue in
this carrier) was repaired and independently re-verified. The full verdict, the PFM subpass, and the
D1–D11 table are in `references/critic-review-2026-07-14-r2.md`; averaging pattern quality does not
substitute for that pass (`CC-DPFDA.4`). Prior-round verdicts are in `references/critic-review.md`
(round 0) and `references/critic-review-2026-07-14-r1.md` (round 1); phase-by-phase history of what has
run for this package is in `references/quality-record-2026-07-14.md`, not narrated here.

**Known, explicit gaps (not silently smoothed):**
- Write-side backpressure and start-timing/lifecycle-ownership/naming — named in the bounded context
  (§1) — are operationalized as Patterns 7–8 (§4). Source-pack open question #1 (S1–S13
  web-verification) is **largely closed**: 11 of 13 confirmed as stated, one sharpened, one adjacent
  claim (S14) corrected — see `references/web-verification-2026-07-14.md`.
- The AI-in-domain slice (S15, Pattern 6, typical errors #1–#5 as an "AI-specific" framing) remains
  explicitly weaker evidence than T1–T4 — no single citable paper, not a fetchable document, therefore
  not re-verified; a targeted search for published empirical studies of LLM-generated concurrency bugs
  remains the named repair (source-pack open question #2).
- T5 (DB-driver tradition, psycopg2/libpq) remains parked, used only as CE3 (see §2 and Pattern 5);
  promotion to a full tradition remains open if a future thesis needs it (source-pack open question #3).
- All three heterogeneous acceptance cases (Section 10) are literature-grounded transfer probes, not
  executed evidence — `worked-evidence pending` on all three, honestly marked, not upgraded to fact.
- `project/domain.md`, `project/decisions/`, and `project/frameworks/competency-map.md` were confirmed
  absent from this repository by directory listing (2026-07-14) — this DPF-catalog is not yet
  cross-linked into a wider competency map or decision log; a facilitator/architect decision on
  whether/how to add those is out of this package's own scope (source-pack open question #4).
- Patterns 7–8's sources (S16–S23) have no formal Phase-1 `CorpusLedger` / Phase-2 `Thesis`/`NQD`
  backfill yet (curator-mandate boundary, `references/quality-record-2026-07-14.md` §5) — addressed to
  `architect`/`facilitator` for a future full pipeline pass, not resolved here.

**Refresh triggers (G.11):**
- The AI-in-domain slice (S15) gets a citable empirical source → re-ground Pattern 6/typical errors
  #1–#5 and raise its trust-cue above `opinion/hypothesis`.
- `DPF-CONCURRENT-PROGRAMMING` (sibling package, same catalog) reaches its own Phase 5 → re-check the
  `scope_boundary` relation in Section 9 for drift now that both sides of the boundary are drafted.
- This repository's reconnect/teardown code changes materially (`DrainGuard`, `_transport_lock`,
  `channel_thread_bindings`, `_teardown_lock`) → re-verify the five worked-slice line citations across
  Section 4 by file read, not by assuming this file's line numbers still hold. If a write-side watermark
  or an explicit `start()` is ever added to this repository, Patterns 7–8's worked slices move from
  "honestly absent" to a real instantiation — re-verify at that point.
- FPF-Spec changes `E.4.DPF`/`G.2`/`E.4.PFR`/`A.2.6`/`B.5.2.1`/`A.11` → re-ground this file's citations.
- Phase 6 re-runs (on any reopen condition or at `review_due`) → the critic, not the curator, updates the
  `E.4.DPF.DA` status line above; the current `admissibleForDeclaredDPFUse` is never self-assigned from
  within this file.
- `review_due`: 2026-09-29.

---

## Artifacts (references/ · assets/)

- [`references/scope.md`](references/scope.md) — Phase 0: bounded context, intended reader, first use,
  non-use boundary, owner+critic assignment.
- [`references/sota-research.md`](references/sota-research.md) — Phase 1: CorpusLedger S1–S15,
  ClaimSheets per tradition (T1–T4 + AI slice), MicroExamples ME1–ME3, Operator/Object inventory,
  freshness & repair register (dated 2026-07-14 web-verification addendum appended, S16–S23 not yet
  backfilled as formal CorpusLedger entries — see `quality-record-2026-07-14.md` §5).
- [`references/theses-antitheses.md`](references/theses-antitheses.md) — Phase 2: BridgeMatrix,
  Theses 1–6 with scope + NQD≥3 anti-theses, counterexamples CE1–CE5, typical-error catalog #1–10,
  repair register (2 file-read verifications, 1 falsification).
- [`references/source-pack.md`](references/source-pack.md) — Phase 3: provenance registry (S1–S23),
  retired premises (RP-1), 5 open provenance questions addressed to `architect`/`facilitator`.
- [`references/critic-review.md`](references/critic-review.md) — Phase 6: independent guardian
  completeness-critic + `E.4.DPF.DA` verdict (round 0, `repairBeforeDPFUse`, D11 below floor).
- [`references/critic-review-2026-07-14-r1.md`](references/critic-review-2026-07-14-r1.md) — Phase 6
  re-check after the first repair (`repairBeforeDPFUse`, D5 below floor).
- [`references/web-verification-2026-07-14.md`](references/web-verification-2026-07-14.md) — S1–S14
  web-verification ledger, S16–S23 new-source ledger.
- [`references/quality-record-2026-07-14.md`](references/quality-record-2026-07-14.md) — process-state
  moved out of `DPF.md` (PFM7), repair log.
- `assets/` — empty; no templates/checklists/code-snippets produced for this competency yet.

---

## Carrier note (CC-DPF.5)

Literature sources S1–S14 were originally admitted through recall (WebSearch/WebFetch were withheld by
explicit customer decision for the original Phase 1–5 authoring). A 2026-07-14 web-verification pass
checked S1–S14 against live sources (`references/web-verification-2026-07-14.md`);
per-claim trust-cues in Sections 4/6/7 above now read `verified 2026-07-14, <URL>` for the confirmed
claims, `verified by file read` for the two repository-internal facts (`DrainGuard`/`_transport_lock`/
`channel_thread_bindings`/`_teardown_lock`, and installed kombu 5.6.2), and `pretrain recall, не
верифицирован` only where a claim genuinely was not re-checked (S15's AI-in-domain slice — a synthesis,
not a fetchable document, held below T1–T4 in this competency's own evidence hierarchy by design, not by
gap). Distinguishing recall from a real fetch, and a real fetch from an unverified claim, is preserved
per `A.10` Evidence Graph discipline — see `references/web-verification-2026-07-14.md` for the one
material correction this pass produced (S14/CE3, psycopg2). FPF sections used here (`E.4.DPF`, `E.8`,
`F.18`) were grepped live against `~/.claude/knowledge/fpf/FPF-Spec.md` (lines 66066–66434, 67558,
89773); `A.2.6`, `B.5.2.1`, `A.11`, `E.4.PFR` line-anchors are inherited from the same-day Phase 2 live
grep recorded in `theses-antitheses.md`'s header, not re-verified here (curator mandate does not re-open
Phase 2's already role-separated grounding work).

---

## Conformance checklist (E.4.DPF:7)

- [x] CC-DPF.1 Context declared — bounded context, intended reader, first use, non-use boundary (§1).
- [x] CC-DPF.2 Source pack present — `references/source-pack.md` (S1–S23, adopted/rejected+reason,
      claim status, currentness), summarized §2.
- [x] CC-DPF.3 Architecture decision present — purpose/pattern-split/dependency-boundary/must-NOT-land
      covered by the structural report + §1 non-use boundary + §9 Relations (folded PFAD, no separate
      DRR file — proportional to a single-competency package per `E.4.DPF:4`).
- [x] CC-DPF.4 Names prepared — 9 terms §8 (F.18), explicitly **not** migrated to a `glossary.md` that
      does not exist in this repository yet (honestly flagged, not silently done).
- [x] CC-DPF.5 Carriers admitted — per-claim trust-cue stated for every claim; most of S1–S14
      web-verified 2026-07-14 (`references/web-verification-2026-07-14.md`); two repository facts
      distinguished as file-read, not recall; FPF grounding live-grepped for E.4.DPF/E.8/F.18.
- [x] CC-DPF.6 Patterns drafted through E.8 — 8 patterns (≥4 gate cleared with margin; two close the
      §0.2 coverage gap), each: recognition → SoTA principle → our instantiation → counterexample
      [A.11] → anti-pattern [E.8] → conformance → connections [E.4.PFR].
- [x] CC-DPF.7 Quality & refresh routes present — §11: package status, explicit gaps, refresh triggers,
      `review_due`.
- [x] CC-DPF.8 Structural report visible in the header — for whom, what is foregrounded, what is
      coarsened/omitted and where it returns, honest status.
- [x] CC-DPF.9 Problem-solving primacy — §4 names typical design questions each pattern answers, §6
      names 12 blocked failure modes, §7 names 23 source-grounded solution moves and their adoption;
      not a vocabulary/ontology catalog (§8 names are explicitly secondary, not migrated to a glossary).

**Phase 6 status:** the conformance line below now carries the independent `guardian`/critic Mode-C
round-2 verdict (`references/critic-review-2026-07-14-r2.md`), folded back into this carrier by the
critic (only the critic updates this line, Mode C). Per `CC-DPFDA.8`, this `admissibleForDeclaredDPFUse`
status was earned by an independent Phase 6 pass over the D1–D11 coordinates (D5 repaired 3→4, PFM7
process-residue removed), not by section-completeness alone — see `references/critic-review.md` (round 0),
`references/critic-review-2026-07-14-r1.md` (round 1), and `references/quality-record-2026-07-14.md` for
the repair history.

> conformance: CC-DPF.1–9 verified; E.4.DPF.DA: admissibleForDeclaredDPFUse (critic, guardian, 2026-07-14, после ремонта r2)
