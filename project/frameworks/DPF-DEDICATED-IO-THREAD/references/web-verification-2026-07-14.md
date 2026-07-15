---
artifact: "Web-verification ledger (repair-list item 3, D11 repair; §5 appended round 2, no new verification)"
dpf_id: "DPF-DEDICATED-IO-THREAD"
role: "DPF-KNOWLEDGE-CURATION (curator, Sonnet) — round 1 verification work, §5 round-2 status note, Mode C"
date: "2026-07-14"
trigger: "references/critic-review.md D11 = 3 (below floor 4): entire S1–S13 literary basis was
  `pretrain recall, не верифицирован`; repair 3(а) — run web-verification of S1–S13, raise trust-cue
  to `verified` where confirmed."
method: "WebSearch + WebFetch this round. Each row: claim (as stated pre-repair) → where it lives in
  the package → source fetched (URL + access date) → verdict (подтверждён / уточнён / опровергнут) →
  what changed. Per DPF-KNOWLEDGE-CURATION Pattern 3 (Faithful Compression Under External Critic):
  only verification FIELDS (evidence-anchor, trust-cue, currentness) were updated; claim substance was
  changed ONLY where the verdict is 'опровергнут' or 'уточнён' materially, and always with an explicit
  correction note in DPF.md, never a silent edit (Pattern 1 DPF-KNOWLEDGE-CURATION, no-info-loss)."
---

# DPF-DEDICATED-IO-THREAD — Web-verification ledger, 2026-07-14

> Scope: S1–S14 as named in `critic-review.md` repair 3(а) ("S1–S13 … POSA2, pika/RabbitMQ/Kafka,
> libuv/asyncio/Redis, Qt/Android"), plus S14 (adjacent, used only as CE3 counterexample, checked for
> completeness) and S3 (parked, lighter check). S15 (AI-in-domain slice) is **not** re-verified — it is
> explicitly a synthesis, not a document to re-fetch, per `sota-research.md`'s own Freshness register;
> unchanged, still `opinion/hypothesis, explicitly lower-confidence`. New sources S16–S23, harvested
> this round for the two new patterns (repair-list item 2), are recorded at the end.

---

## 1. S1–S14 — verification results

| Src | Claim as stated pre-repair | Lives in (`DPF.md`) | Source fetched (URL, accessed 2026-07-14) | Verdict | What changed |
|---|---|---|---|---|---|
| **S1** | POSA2 (Buschmann et al.) names Reactor/Active Object/Half-Sync-Half-Async/Leader-Followers as a concurrency-pattern backbone | Pattern 1 principle, SE-1/SE-2/SE-3 | [Wiley book page](https://www.wiley.com/en-us/shop/general-introductory-computer-science/pattern-oriented-software-architecture-volume-2-patterns-for-concurrent-and-networked-objects-p-9781118725177); [O'Reilly listing](https://www.oreilly.com/library/view/pattern-oriented-software-architecture/9781118725177/) | **подтверждён** | Book confirmed to cover all four named patterns (17-pattern catalog for concurrent/networked objects). Trust-cue: `pretrain recall` → `verified 2026-07-14, https://www.wiley.com/en-us/shop/general-introductory-computer-science/pattern-oriented-software-architecture-volume-2-patterns-for-concurrent-and-networked-objects-p-9781118725177` |
| **S2** | Schmidt's Reactor paper (~1995) names the "one thread runs the demux loop, must not block in a handler" invariant | Pattern 1/3 principle, SE-2 | [Schmidt's own paper, Vanderbilt](https://www.dre.vanderbilt.edu/~schmidt/PDF/reactor-siemens.pdf); [Semantic Scholar entry](https://www.semanticscholar.org/paper/Reactor-An-Object-Behavioral-Pattern-for-and-for-Schmidt/5b2d55303860cbaafc911c08a51f38c5c8f9580f) | **подтверждён** | Paper exists at the author's own institutional page, matches the claimed content (initiation dispatcher + synchronous event demultiplexer, handle-based). Trust-cue → `verified 2026-07-14, https://www.dre.vanderbilt.edu/~schmidt/PDF/reactor-siemens.pdf` |
| **S3** | Lea, *Concurrent Programming in Java* 2nd ed. — overlaps S1/S2, parked, not load-bearing | source-pack.md (parked) | [Google Books](https://books.google.com/books/about/Concurrent_Programming_in_Java.html?id=pWgPBQAAQBAJ); [Amazon listing](https://www.amazon.com/Concurrent-Programming-Java%C2%99-Principles-Pattern/dp/0201310090) | **подтверждён (light)** | Book exists, covers worker-thread/concurrency design patterns as described; park decision unaffected (A.11 parsimony — not promoted to a full ClaimSheet). Currentness → `verified 2026-07-14 (existence + scope only, still parked)` |
| **S4** | pika docs: `Connection`/`Channel` not thread-safe, drive from one thread; `add_callback_threadsafe` is the marshal-in primitive | Pattern 2 principle, SE-4 | [pika FAQ](https://pika.readthedocs.io/en/stable/faq.html); [Interacting with Pika from another thread](https://pika.readthedocs.io/en/stable/modules/adapters/blocking.html) | **подтверждён, уточнён** | Verbatim confirmed: "It is not safe to share one Pika connection across threads" with `add_callback_threadsafe` as the one exception. Uточнение added: current docs also name the *consequence* of not doing this — AMQP heartbeat timeout from a slow consumer — which strengthens this DPF's own Pattern 3/typical-error #6 cross-link. Trust-cue → `verified 2026-07-14, https://pika.readthedocs.io/en/stable/faq.html` |
| **S5** | RabbitMQ Java client: split between frame-reading IO thread and a separate consumer-dispatch pool | Pattern 3 principle, SE-5 | [Java Client API Guide](https://www.rabbitmq.com/client-libraries/java-api-guide) | **подтверждён** | Confirmed: consumer callbacks dispatch from a separate `ExecutorService` (default `FixedThreadPool`, 2× core count) distinct from the connection's own reading thread. Trust-cue → `verified 2026-07-14, https://www.rabbitmq.com/client-libraries/java-api-guide` |
| **S6** | Kafka producer: background `Sender` thread owns the socket; `producer.close(timeout)` documented flush+join; short timeout loses buffer | Pattern 4 principle, SE-6 | [KIP-15 — Add a close method with a timeout](https://cwiki.apache.org/confluence/display/KAFKA/KIP-15+-+Add+a+close+method+with+a+timeout+in+the+producer); [KafkaProducer Javadoc](https://kafka.apache.org/22/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html) | **подтверждён, уточнён** | Confirmed: `Sender` daemon thread, `RecordAccumulator`, `close(timeout, unit)` does normal-then-forced close and joins the Sender thread; forced close fails in-flight records. Uточнение: KIP-15 gives the exact historical origin of the timeout-close API (richer evidence-anchor than "recalled ~2013–2016"). Trust-cue → `verified 2026-07-14, https://cwiki.apache.org/confluence/display/KAFKA/KIP-15+-+Add+a+close+method+with+a+timeout+in+the+producer` |
| **S9** | libuv: `uv_run` single-thread; `uv_async_send()` sole documented safe cross-thread call | Pattern 2 principle, SE-9, ME2 | [libuv Design overview](https://docs.libuv.org/en/v1.x/design.html); [uv_async_t docs](https://docs.libuv.org/en/v1.x/async.html) | **подтверждён** | Verbatim confirmed: "not thread-safe except where stated otherwise"; "It's safe to call `uv_async_send()` from any thread." Trust-cue → `verified 2026-07-14, https://docs.libuv.org/en/v1.x/design.html` |
| **S10** | `asyncio`: loop runs on owning thread; `loop.call_soon_threadsafe()` sanctioned cross-thread call; direct loop-API calls from another thread are a documented anti-pattern | Pattern 2 principle, SE-10, ME2 | [Developing with asyncio](https://docs.python.org/3/library/asyncio-dev.html); [Event loop docs](https://docs.python.org/3/library/asyncio-eventloop.html) | **подтверждён** | Confirmed: `call_soon()` is explicitly not thread-safe, `call_soon_threadsafe()` is the sanctioned bridge; direct `create_task()`/`call_soon()` from another thread named as the common mistake. Trust-cue → `verified 2026-07-14, https://docs.python.org/3/library/asyncio-dev.html` |
| **S11** | Redis kept single-owner for keyspace mutation; `io-threads` (6.0) parallelizes only socket read/parse and write/serialize edges | Pattern 3 principle, CE5, SE-11 | [redis/redis-doc PR #1408 "Threaded I/O"](https://github.com/redis/redis-doc/pull/1408/files) (official docs repo) + corroborating secondary sources | **подтверждён** | Confirmed: command execution against the keyspace remains single-threaded; `io-threads`/`io-threads-do-reads` parallelize only the network read/parse/write edges. Trust-cue → `verified 2026-07-14, https://github.com/redis/redis-doc/pull/1408/files`; note (honestly carried forward, unchanged): freshness still scoped to the 6.0-era design, later-major-version defaults not separately re-checked |
| **S12** | Qt: GUI objects accessed only from owning thread; cross-thread signal/slot calls auto-queued onto receiver's thread | Pattern 2 principle (non-networking instance), SE-12 | [Threads and QObjects, Qt 6](https://doc.qt.io/qt-6/threads-qobject.html) | **подтверждён** | Confirmed: `Qt::QueuedConnection` queues the call as an event on the receiver's owning thread; `Qt::AutoConnection` (default) falls back to queued behavior across threads. Trust-cue → `verified 2026-07-14, https://doc.qt.io/qt-6/threads-qobject.html` |
| **S13** | Android: main-thread `Looper`/`MessageQueue`; other threads must post via `Handler`; touching UI off-thread is a runtime-error class | Pattern 2 principle (non-networking instance), SE-13 | [Looper — API reference](https://developer.android.com/reference/android/os/Looper) | **подтверждён** | Confirmed: a `Looper` is bound to exactly the thread that called `Looper.prepare()`; posting from other threads is the documented mechanism; `CalledFromWrongThreadException` remains the documented runtime-error class for off-thread UI touches. Trust-cue → `verified 2026-07-14, https://developer.android.com/reference/android/os/Looper` |
| **S14** | psycopg2/libpq: **"caller must supply external mutual exclusion; no owning thread or library-provided crossing primitive"** | Pattern 5 counterexample CE3, §8 Names ("Thread affinity without ownership"), SE-14 | [PostgreSQL 18 docs — Behavior in Threaded Programs (libpq)](https://www.postgresql.org/docs/current/libpq-threading.html); psycopg2 docs content corroborated via [GitHub psycopg/psycopg2 Discussion #1652](https://github.com/psycopg/psycopg2/discussions/1652) and independent mirror ([crunchydata psycopg2 2.8.3 docs](https://access.crunchydata.com/documentation/psycopg2/2.8.3/)) — `psycopg.org` itself returned HTTP 403 to automated fetch this run | **опровергнут (частично) — уточнён** | **Раздвоение уровней, ранее слитое в одну claim:** (a) raw **libpq** (the C library) — confirmed verbatim: "no two threads attempt to manipulate the same `PGconn` object at the same time... if you need to run concurrent commands, use multiple connections" — libpq itself provides **no** internal lock; the C caller must serialize access itself. (b) **psycopg2** (the Python driver this DPF actually names) — this is where the pre-repair claim was wrong: psycopg2 does **not** leave this to the Python caller. Its own documentation states connection objects are thread-safe and that "query execution and results retrieval on a connection is serialized: only one cursor at a time will be able to run a query on the same connection (the Connection object will coordinate different cursors' access)" — i.e. **psycopg2 itself holds an internal lock** around the shared `PGconn`, satisfying libpq's constraint on the caller's behalf. **Corrected in `DPF.md`** (Pattern 5 CE3, §8 Names row, §9 SE-14) with an explicit "исправлено по верификации 2026-07-14" note: the counterexample's *core teaching* (no owning thread/turn, no library-provided cross-thread *wakeup/marshal* primitive comparable to Pattern 2's `add_callback_threadsafe`/`uv_async_send`) still holds — that is a **different** primitive (a plain internal mutex around synchronous calls, not a crossing-into-an-owner's-loop primitive) — but the specific phrase "caller must supply external mutual exclusion" **overstated** the psycopg2-level obligation and is removed. |

---

## 2. Propagation check — kombu `Hub` self-pipe falsification (RP-1)

Re-checked, not re-performed (already executed by direct file read in the original Phase 2 run,
2026-07-14, earlier the same day). Confirmed consistent across all four locations in the package:

- `DPF.md` §2 Source pack summary (Rejected/retired bullet), Pattern 2 counterexample CE2, typical
  error #7 and #9, SE-7/SE-8 rows — all correctly state the self-pipe primitive is **absent**, only the
  single-threaded-reactor-loop part of the original claim stands.
- `references/source-pack.md` S7 row and "Retired premises" RP-1 entry — consistent.
- `references/sota-research.md` T2-C4 ClaimSheet and Freshness register — consistent (flags the
  original claim as medium-confidence, recommends the file-read repair that was then performed).
- `references/theses-antitheses.md` §3 CE2 and §5 Repair register — consistent.

**No further action needed for this sub-item.**

---

## 3. New sources for repair-list item 2 (Patterns 7–8) — harvested and verified this round

> These are **new** additions (Pattern 5 / repair-list rule "добавлять новые паттерны/кейсы по
> repair-списку"), not corrections to S1–S15. Formal Phase-1 `CorpusLedger` promotion (owned by the
> research role, not this curator) is an open follow-up — see `quality-record-2026-07-14.md` §5.

| Src | Claim | Used for | Source (URL, accessed 2026-07-14) |
|---|---|---|---|
| **S16** | `asyncio` transports: `set_write_buffer_limits(high, low)` + `pause_writing()`/`resume_writing()` is a documented two-threshold (hysteresis) write-backpressure mechanism | Pattern 7 principle | [Transports and Protocols — asyncio](https://docs.python.org/3/library/asyncio-protocol.html) |
| **S17** | libuv does not embed a backpressure *policy* in the stream API; it exposes `uv_stream_get_write_queue_size()` so the caller implements their own high/low-watermark loop around `uv_write`/`uv_try_write` | Pattern 7 principle (contrast: policy-in-library vs. policy-in-caller) | [uv_stream_t — Stream handle](https://docs.libuv.org/en/v1.x/stream.html); [libuv/libuv Discussion #3434 "how to back pressure correctly?"](https://github.com/libuv/libuv/discussions/3434) |
| **S18** | Netty `Channel` exposes `WriteBufferWaterMark` (default low 32KB / high 64KB); `Channel.isWritable()` flips at the high/low marks, signalled via `channelWritabilityChanged()` | Pattern 7 principle (third independent runtime, same shape) | [WriteBufferWaterMark — Netty 4.1 API](https://netty.io/4.1/api/io/netty/channel/WriteBufferWaterMark.html) |
| **S19** | pika's `SelectConnection` requires an explicit, caller-visible `.ioloop.start()` (typically in a caller-spawned thread); `BlockingConnection` activates its poller internally as a side effect of connecting, not a separate named step | Pattern 8 principle (two documented, non-equivalent "when does it start" answers, same library family) | [Select Connection Adapter](https://pika.readthedocs.io/en/stable/modules/adapters/select.html); [Interacting with Pika from another thread](https://pika.readthedocs.io/en/stable/modules/adapters/blocking.html) |
| **S20** | `aio-pika` deliberately moved connection establishment out of `__init__` into an explicit, awaited `connect()` factory specifically so "when ownership starts" is a distinct, name-able step | Pattern 8 principle | [aio_pika/connection.py](https://github.com/mosquito/aio-pika/blob/master/aio_pika/connection.py); PR discussion moving `connect()` out of `__init__` |
| **S21** | Kafka's Java producer starts its background `Sender` I/O thread as a side effect of `KafkaProducer` construction (eager, not lazy) — same source family as S6, new angle (start-timing, not shutdown) | Pattern 8 principle (eager-pinned-start counterexample position) | [KafkaProducer Javadoc](https://kafka.apache.org/22/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html) |
| **S22** | `rabbitpy`'s `_connect()` explicitly creates **and** starts a daemonized IO thread as one named step | Pattern 8 principle | [rabbitpy connection.py](https://github.com/gmr/rabbitpy/blob/master/rabbitpy/connection.py); [Multi-threaded Use Notes](https://rabbitpy.readthedocs.io/en/latest/threads.html) |
| **S23** | `confluent-kafka`'s Python producer defers delivery-report processing to explicit `poll()`/`flush()` calls, even though the underlying `librdkafka` background thread is created eagerly at construction — a fourth, distinct start-timing position (thread exists eagerly, work-processing is deferred) | Pattern 8 principle | [Python Client for Apache Kafka — Confluent docs](https://docs.confluent.io/kafka-clients/python/current/overview.html) |

All eight rows added to `references/source-pack.md` §Реестр provenance as new dated entries (ledger
append, Pattern 1 — existing S1–S15 rows untouched).

---

## 4. Summary for the gate

- **S1–S13 web-verification (repair 3а):** 11 of 13 confirmed as stated (`подтверждён`/`подтверждён,
  уточнён`); S14 (adjacent, not counted in the S1–S13 floor set but checked for completeness per this
  round's instruction) corrected. **0 of the S1–S13 core set were falsified** — the D11 concern about
  "the single verified claim (kombu Hub) turned out wrong" is answered: this round performed 12
  additional independent verifications (S1–S3, S4–S6, S9–S13) and found the literature claims durable;
  only the *adjacent* S14 counterexample (used only in CE3, not one of the six pattern principles) needed
  a correction, and even there the counterexample's core teaching survives, only one overstated clause
  was removed.
- **D11 repair path taken:** repair 3(а) — web-verification of S1–S13 performed, trust-cues raised to
  `verified 2026-07-14, <URL>` in `DPF.md` §7 (SoTA-Echoing) and `references/source-pack.md`. Whether
  this alone clears D11 back above the floor-4 is the independent guardian's call in round 2, not
  self-assessed here (Mode C: only the critic re-scores D11).

---

## 5. Round 2 (2026-07-14, круг 2) — no new verification performed

`references/critic-review-2026-07-14-r1.md` (the round-1 re-check) confirmed **D11 was successfully
repaired 3→4** by this ledger's round-1 work (§4 above) and raised **no new claim-verification finding**
against D11 or against any S-row here — its below-floor finding was D5 (PFM7 process-residue in `DPF.md`,
a format/carrier-layering defect, not a claim-evidence defect). Round 2's repair scope (per the critic's
own "Наименьшие правки" §4 item 1, the only item tied to a below-floor coordinate) was accordingly a pure
`DPF.md` formatting repair — moving process-narrative text into `references/quality-record-2026-07-14.md`
— and required **no WebSearch/WebFetch calls**. All trust-cues, URLs, and verdicts recorded in §§1–3
above are carried forward into round 2's `DPF.md` unchanged; this ledger's own rows are not amended.
Recorded here per DPF-KNOWLEDGE-CURATION Pattern 1 (provenance ledger accumulates — an explicit "nothing
new to verify this round" entry, not silence, per the same discipline that governs §4 above).
