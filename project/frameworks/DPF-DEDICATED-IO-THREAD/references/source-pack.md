---
artifact: "Phase-3 Source Pack (G.2)"
dpf_id: "DPF-DEDICATED-IO-THREAD"
phase: 3
date: "2026-07-14"
role: "DPF-KNOWLEDGE-CURATION, Режим A — Провенанс (owner: keeper; mandate: format/provenance, NOT domain content)"
mode: "PRETRAIN-ONLY RESEARCH RUN — WebSearch/WebFetch withheld by explicit customer decision (2026-07-14). Two cheap in-scope file-reads (this repo's own source, installed kombu 5.6.2) WERE performed in Phase 2 and are carried into this ledger as their own rows, not silently merged into the pretrain-recall rows they helped verify/falsify."
input: "references/scope.md (Phase 0); references/sota-research.md (Phase 1, G.2a CorpusLedger S1–S15); references/theses-antitheses.md (Phase 2, BridgeMatrix + Тезисы 1–6 + CE1–CE5 + Repair register)"
gate_target: "every source has a decision (adopted/rejected+reason); retired-premises section present even if empty; open provenance questions listed and addressed to an owner"
---

# DPF-DEDICATED-IO-THREAD — Source Pack (G.2)

> Реестр provenance: по каждому источнику из `references/` — что **взято** в предстоящую сборку
> `DPF.md`, что **намеренно отброшено** (и почему), статус claim'а (fact/hypothesis/opinion) и
> актуальность (currentness). Контент источников — в `scope.md`/`sota-research.md`/
> `theses-antitheses.md`; здесь — **решения** по ним (Паттерн 1 DPF-KNOWLEDGE-CURATION: реестр копится
> в момент решения, не переписывается постфактум под готовый носитель).
>
> **Роль-граница (мандат куратора).** Это провенанс-реестр по ФОРМАТУ источников (что принято/
> отклонено как материал для DPF), НЕ повторная адверсарная критика содержания — та уже выполнена в
> Фазе 2 (`theses-antitheses.md`, role-separated guardian-pass) и здесь не переоткрывается. Содержательные
> вопросы, всплывшие при провенансе (см. «Открытые provenance-вопросы» ниже), зафиксированы как
> адресованные owner-роли (architect), не решены куратором единолично.
>
> **Trust-cue regime (наследован из Фаз 1–2):** каждая строка ниже несёт статус claim'а. Изначально
> подавляющее большинство источников было `pretrain recall, не верифицирован` (customer-mandated
> pretrain-only run, 2026-07-14); две строки были помечены `verified this run (file read)` — прямое
> чтение файлов, выполненное в Фазе 2. Различие намеренно не сглажено (A.10 Evidence Graph): «мнение о
> содержании файла» и «файл реально прочитан» — разные веса доказательства.
>
> **Обновление 2026-07-14 (repair round, DPF-KNOWLEDGE-CURATION curator, Mode C круг 1):** веб-
> верификация S1–S14 выполнена (`references/web-verification-2026-07-14.md`) — 11 из 13 (S1–S13)
> подтверждены как заявлено, S6 уточнён (KIP-15), S14 частично исправлен (см. строку S14 ниже и
> `DPF.md` Pattern 5 CE3). Currentness-поля строк S1–S6, S9–S14 обновлены ниже дописыванием
> («было: … → verified …»), исходный текст не удалён (Паттерн 1 DPF-KNOWLEDGE-CURATION). Семь новых
> строк (S16–S23) добавлены в конец реестра для источников новых Паттернов 7–8 (`DPF.md`); их формальный
> Phase-1 CorpusLedger-бэкфилл в `sota-research.md` остаётся открытым follow-up (см.
> `quality-record-2026-07-14.md` §5 в каталоге DPF).

---

## Реестр provenance

| Источник | Adopted (взято) | Rejected (намеренно отброшено) + причина | Claim status | Currentness |
|----------|------------------|--------------------------------------------|---------------|-------------|
| `references/scope.md` (Phase 0, весь файл) | Bounded context (owner thread/turn over one non-thread-safe socket; start/service/stop/reconnect-fork lifecycle), intended reader (architect prime, dev/guardian/cto secondary), first-use trigger, non-use boundary (не asyncio-primer, не thread-pool-of-workers, не broker-comparison, не web-verified claim set) — вошло целиком как рамка для последующих фаз | — (весь файл принят; ничего не отклонено на уровне Phase-0 рамки) | opinion (scope-декларация — решение авторов, не эмпирический факт) | 2026-07-14 |
| `references/sota-research.md` (Phase 1, весь файл как артефакт) | CorpusLedger (S1–S15) + ClaimSheets (T1-C1…T4-C2) + AI-срез (AI-F1–F5) + MicroExamples (ME1–ME3) + Operator/Object inventory + Freshness register — используются построчно ниже (см. отдельные строки S1–S15) | Тяжёлая G.2-механика (BridgeMatrix, UTSProposals, SoSIndicatorFamilies, full PRISMA) явно НЕ включена авторами Phase 1 (сама sota-research.md декларирует это как сознательный пропуск, не пробел куратора) — не переоткрывается здесь | mixed (см. построчные claim'ы ниже) | 2026-07-14 |
| `references/theses-antitheses.md` (Phase 2, весь файл как артефакт) | BridgeMatrix (alignment 2 пункта + divergence 2 оси), Тезисы 1–6 (каждый со scope + NQD≥3 анти-тезисом), контрпримеры CE1–CE5, каталог типовых ошибок №1–10 (5 AI-специфичных), Repair register (2 верификации + falsification T2-C4) — вся структура принята как вход Фазы 5 (Assemble) | — (файл принят целиком; это уже role-separated адверсарный проход, не подлежит повторной критике куратором — мандат куратора: формат, не содержание) | mixed (см. отдельные тезисы/контрпримеры ниже, где применимо) | 2026-07-14 |
| S1 — Buschmann et al., *POSA Vol.2* (Reactor/Active Object/Half-Sync-Half-Async/Leader-Followers), ~2000 | Все 4 паттерна как T1's backbone-вокабуляр; T1-C1…T1-C4 построены на нём | — (include, не rejected) | fact (durable literature consensus per sota-research) — **обновлено 2026-07-14: verified, https://www.wiley.com/en-us/shop/general-introductory-computer-science/pattern-oriented-software-architecture-volume-2-patterns-for-concurrent-and-networked-objects-p-9781118725177** | было: web-verification pending → **verified 2026-07-14** (repair round, `web-verification-2026-07-14.md` row S1) |
| S2 — Schmidt, "Reactor" paper, ~1995 | T1-C3 (handler must-not-block invariant), origin-attribution для S1's Reactor chapter | — (include) | fact | было: pretrain recall, web-verification pending → **verified 2026-07-14, https://www.dre.vanderbilt.edu/~schmidt/PDF/reactor-siemens.pdf** (repair round) |
| S3 — Lea, *Concurrent Programming in Java* 2nd ed., ~1999 | Не использован ни в одном claim'е ниже по цепочке (Phase 1 сознательно не построила на нём ClaimSheet) | **Rejected: park.** Причина (унаследована из sota-research S3): пересекается с S1/S2 под Java-углом; включение раздуло бы harvest без нового содержания (A.11 Parsimony) — оставлен как cross-check кандидат для будущего web-repair, не как несущий источник | n/a (не процитирован как claim-носитель) | parked, 2026-07-14 — **обновлено 2026-07-14: существование+охват книги подтверждён (light-check), https://books.google.com/books/about/Concurrent_Programming_in_Java.html?id=pWgPBQAAQBAJ; park-решение не изменилось** |
| S4 — pika official docs, threading FAQ, ~2019–2023 | T2-C1 (single-thread-per-connection rule, `add_callback_threadsafe` marshal-in primitive) — ближайший документированный аналог задачи этого репозитория | — (include) | fact | было: pretrain recall, web-verification pending → **verified 2026-07-14, https://pika.readthedocs.io/en/stable/faq.html** (repair round; also confirms heartbeat-timeout consequence) |
| S5 — RabbitMQ Java client guide, connection thread-safety + consumer-pool, ~2015–2023 | T2-C2 (IO-поток узко scoped на framing/heartbeat, прикладная работа явно снята в отдельный пул) | — (include) | fact | было: pretrain recall, web-verification pending → **verified 2026-07-14, https://www.rabbitmq.com/client-libraries/java-api-guide** (repair round) |
| S6 — Kafka Java Producer internals (`Sender`/`RecordAccumulator`), ~2013–2016 | T2-C3 (background IO thread, `producer.close(timeout)` flush+join semantics, короткий таймаут = документированный способ потери буфера) | — (include) | fact | было: pretrain recall, web-verification pending → **verified 2026-07-14, https://cwiki.apache.org/confluence/display/KAFKA/KIP-15+-+Add+a+close+method+with+a+timeout+in+the+producer** (repair round; KIP-15 gives exact historical origin) |
| S7 — kombu `asynchronous.hub.Hub` (source + Celery docs/comments), ~2013–2016 origin | T2-C4 ЧАСТИЧНО: single-threaded reactor loop, один поток на весь lifecycle — держится как факт после верификации Фазы 2 | **Частично rejected (falsified this run).** Под-claim «cross-thread/signal wakeup handled by a self-pipe-style primitive» — прямое чтение установленного kombu 5.6.2 (`kombu/asynchronous/hub.py`, Фаза 2) показало: НЕТ `os.pipe`/self-pipe, НЕТ `*_threadsafe`-метода, НЕТ `wakeup`; есть только `call_soon`/`call_later` (не threadsafe) и `poll(timeout)`. См. `theses-antitheses.md` §5 Repair register и CE2. Эта под-claim перенесена в «Retired premises» ниже, не молча исправлена без следа | fact (частично, после коррекции) / **retired sub-claim** (self-pipe часть) | verified this run (file read) — installed kombu 5.6.2, 2026-07-14; остальная часть T2-C4 — pretrain recall |
| S8 — этот репозиторий, `README.md`, цитирующий `github.com/celery/py-amqp/issues/420` | Принят как **provenance/corpus-запись**, НЕ как независимый внешний SoTA-авторитет: называет origin-проблему («py-amqp Connection не thread-safe»), которую весь пакет решает | Rejected как независимая Tradition-claim (сама sota-research S8 маркирует это явно: "not adopted as independent Tradition claim") — это self-referential framing целевого проекта, а не внешняя литература | README.md-цитата: fact (прочитан напрямую this run); содержимое внешнего GitHub issue №420: **не верифицировано** | README-часть — verified this run (direct read); issue-часть — pretrain recall, не верифицирован |
| S9 — libuv "Design overview" docs, `uv_async_send`, docs stable ~2013+ | T3-C1 (one-thread-owns-loop invariant + единственный документированный safe cross-thread call); ME2 | — (include) | fact | было: pretrain recall, web-verification pending → **verified 2026-07-14, https://docs.libuv.org/en/v1.x/design.html** (repair round) |
| S10 — Python `asyncio` docs, `loop.call_soon_threadsafe()`, stable ~3.4+ | T3-C2 (loop must run from owning thread; documented anti-patterns: calling loop-API from another thread, blocking work inside callback); ME2 | — (include) | fact | было: pretrain recall, web-verification pending → **verified 2026-07-14, https://docs.python.org/3/library/asyncio-dev.html** (repair round) |
| S11 — Redis `io-threads` docs (6.0, 2020) + antirez design-rationale posts | T3-C3 (single-owner ОСТАВЛЕН для мутации keyspace, распараллелены ТОЛЬКО socket-края) — ключевой nuance-claim для CE5 и Тезиса 3 | — (include) | fact (для 6.0-эры дизайна) | было: pretrain recall; freshness explicitly scoped to 6.0-era → **verified 2026-07-14, https://github.com/redis/redis-doc/pull/1408/files** (repair round); 6.0-era scoping caveat unchanged, later-major defaults still not re-checked |
| S12 — Qt docs, "Threads and QObjects", queued signal/slot | T4-C1 (single owner thread + queued cross-thread marshal, применённый к UI-state, не сокету) — показывает, что паттерн не сетевой-специфичен | — (include) | fact | было: pretrain recall, web-verification pending → **verified 2026-07-14, https://doc.qt.io/qt-6/threads-qobject.html** (repair round) |
| S13 — Android Developers docs, `Looper`/`Handler`/`MessageQueue` | T4-C2 (main-thread discipline как runtime-error класс, не стиль; `Handler.post` как marshal primitive) | — (include) | fact | было: pretrain recall, web-verification pending → **verified 2026-07-14, https://developer.android.com/reference/android/os/Looper** (repair round) |
| S14 — psycopg2/libpq docs, connection thread-affinity warnings | Использован ТОЛЬКО как контрпример CE3 (adjacent-but-different resolution family, no owning thread/turn — **исправлено по верификации 2026-07-14**: было "caller-supplied external lock, без выделенного потока/turn"; libpq (C API) confirmed to require caller-side serialization, но psycopg2 confirmed to lock the shared connection internally — caller does NOT need an external lock at the psycopg2 level; см. `web-verification-2026-07-14.md` §1 row S14 и `DPF.md` Pattern 5 CE3) | **Rejected as Tradition (park в Phase 1, подтверждено в Phase 2).** Причина: другое семейство разрешения той же проблемы (нет owning-thread/turn и нет library-provided reconnect-idempotency guard) — не даёт независимого ClaimSheet-уровня материала сверх контрпримера; полный харвест не оправдан (Forces §3, cost vs richness) | n/a как Tradition-claim; opinion/fact как contrast-описание в CE3 (corrected) | было: parked, 2026-07-14 → **verified (частично опровергнут) 2026-07-14: libpq https://www.postgresql.org/docs/current/libpq-threading.html; psycopg2 internal locking https://github.com/psycopg/psycopg2/discussions/1652** (repair round); park-решение не изменилось |
| S15 — синтезированный pattern-matching по diffuse pretrain-наблюдениям LLM-code-gen failure modes, ~2022–2024 | AI-F1…F5 (missing wakeup / unsafe shutdown / GIL-fallacy / wrong primitive / non-idempotent reconnect) — обязательный AI-срез; ME3; Тезис 6 целиком построен на этом источнике | Не rejected целиком, но **явно понижен весом**: нет единого цитируемого источника, held ниже T1–T4 в собственной иерархии Фазы 1/2 (sota-research §AI slice, theses-antitheses Тезис 6 scope-строка) — куратор не повышает этот статус | **opinion/hypothesis, явно flagged low-confidence** (не fact, в отличие от S1–S13) | pretrain recall / synthesized pattern-matching, не верифицирован — web-repair-кандидат: искать published empirical studies LLM-generated concurrency bugs |
| Инстанцирующий репозиторий — `src/kombu_pyamqp_threadsafe/__init__.py` (прямое чтение, Фаза 2) | `DrainGuard` (класс, стр. 353), `_transport_lock` (RLock, стр. 549), `channel_thread_bindings` (defaultdict, стр. 555), `marked_for_teardown` (стр. 455/467/496), `_teardown_lock` (стр. 827) — все пять инстанцирующих claim'ов репозитория (per-call turn-ownership, serialized transport, per-thread channel binding, idempotent teardown) подтверждены прямым чтением; независимо перепроверено этим прогоном (`grep` на те же имена/строки при курировании, 2026-07-14, совпадает) | — (весь набор принят; ничего не отклонено) | **fact, verified this run (file read)** — не recall | verified this run (file read), 2026-07-14 (Phase 2 + повторная проверка курированием в тот же день) |
| Installed kombu 5.6.2 — `kombu/asynchronous/hub.py` (прямое чтение, Фаза 2) | Falsification под-claim'а T2-C4 (см. строку S7 выше); подтверждение отсутствия self-pipe/`*_threadsafe`/`wakeup`, наличия `call_soon`/`call_later`/`poll(timeout)` | — (само чтение принято целиком как evidence) | **fact, verified this run (file read)** | verified this run (file read), 2026-07-14 |
| FPF-Spec.md (live grep, `~/.claude/knowledge/fpf/FPF-Spec.md`, ред. ailev/FPF@f7c7e93f) — E.4.DPF:3 Forces, E.4.PFR:4 relation functions, A.2.6 USM/ClaimScope, B.5.2.1 NQD, A.11:2 Sharp Boundary | Скелет и терминология Фазы 2 (`theses-antitheses.md` шапка цитирует конкретные строки: 66105/66830/4185/37336/20739-20748) — метод сверен живьём, не по памяти (A.10) | — (метод-грaунд принят целиком; куратор не переоткрывает эту сверку — она уже выполнена role-separated проходом в Фазе 2) | fact (метод-канон, не доменный claim) | live-verified 2026-07-14 (Phase 2, Grep+Read this run) |
| `~/.claude/skills/dpf-authoring/references/method.md` (канон метода, скилл) | Скелет источник-пака (это самый файл), структура секций CC-DPF.2 | — (принят целиком как формальный канон, не доменный источник) | fact (метод-канон) | наследуется от скилла; не датирован отдельно в этом прогоне |
| `project/domain.md` (упомянут в задании как контекстный путь) | **НЕ ADOPTED — файл не существует в этом репозитории на момент прогона** (проверено `ls`, 2026-07-14): в `kombu-pyamqp-threadsafe` нет `project/domain.md` | Rejected: отсутствие файла, не содержательное отклонение. Не подменяется молчанием — зафиксировано явно как открытый provenance-вопрос ниже, адресован owner (architect), не решён куратором | n/a (файла нет — claim невозможен) | 2026-07-14 (проверено этим прогоном) |
| `project/decisions/` (упомянут в задании как контекстный путь) | **НЕ ADOPTED — каталог не существует в этом репозитории на момент прогона** (проверено `ls`, 2026-07-14) | Rejected: отсутствие каталога, не содержательное отклонение. Зафиксировано как открытый provenance-вопрос | n/a | 2026-07-14 (проверено этим прогоном) |
| `project/frameworks/competency-map.md` (упомянут в задании как контекстный путь) | **НЕ ADOPTED — файл не существует в этом репозитории на момент прогона** (проверено `ls`, 2026-07-14) | Rejected: отсутствие файла, не содержательное отклонение. Зафиксировано как открытый provenance-вопрос | n/a | 2026-07-14 (проверено этим прогоном) |

**Новые строки, добавлены 2026-07-14 (repair round) — источники Паттернов 7–8 (`DPF.md`, добавлены тем же
прогоном, closing critic-review.md §0.2):**

| S16 — Python `asyncio` docs, "Transports and Protocols", `set_write_buffer_limits`/`pause_writing`/`resume_writing` | Pattern 7 principle (write-side two-threshold backpressure) | — (include) | fact | verified 2026-07-14, https://docs.python.org/3/library/asyncio-protocol.html |
| S17 — libuv docs, `uv_stream_get_write_queue_size`, + libuv GitHub Discussion #3434 "how to back pressure correctly?" | Pattern 7 principle (policy-in-caller contrast to S16/S18) | — (include) | fact | verified 2026-07-14, https://docs.libuv.org/en/v1.x/stream.html |
| S18 — Netty 4.1 API docs, `WriteBufferWaterMark`, `Channel.isWritable()` | Pattern 7 principle (third independent runtime, same watermark shape) | — (include) | fact | verified 2026-07-14, https://netty.io/4.1/api/io/netty/channel/WriteBufferWaterMark.html |
| S19 — pika docs, `SelectConnection`/`BlockingConnection` adapters | Pattern 8 principle (explicit vs. internal start, same library family) | — (include) | fact | verified 2026-07-14, https://pika.readthedocs.io/en/stable/modules/adapters/select.html |
| S20 — aio-pika source, `aio_pika/connection.py`, `connect()` moved out of `__init__` | Pattern 8 principle (explicit awaited start) | — (include) | fact | verified 2026-07-14, https://github.com/mosquito/aio-pika/blob/master/aio_pika/connection.py |
| S21 — Kafka producer Javadoc (same family as S6, new angle: eager background-thread start) | Pattern 8 principle (eager-pinned-start counterexample position) | — (include) | fact | verified 2026-07-14, https://kafka.apache.org/22/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html |
| S22 — rabbitpy source, `rabbitpy/connection.py`, `_connect()` creates+starts daemonized IO thread | Pattern 8 principle (explicit named create+start step) | — (include) | fact | verified 2026-07-14, https://github.com/gmr/rabbitpy/blob/master/rabbitpy/connection.py |
| S23 — confluent-kafka Python docs/source, `poll()`/`flush()`-deferred delivery processing vs. eager `librdkafka` background-thread construction | Pattern 8 principle (fourth position: thread exists eagerly, but work-processing is deferred until an explicit call — distinct from both S19's two positions and S21's fully eager one) | — (include) | fact | verified 2026-07-14, https://docs.confluent.io/kafka-clients/python/current/overview.html |

> S16–S23 are **new additions**, not corrections to S1–S15. Formal Phase-1 `CorpusLedger` promotion in
> `sota-research.md` (owned by the research role, not this curator) is an explicit open follow-up —
> see `quality-record-2026-07-14.md` §5 in the `DPF-DEDICATED-IO-THREAD` catalog. Curator mandate
> (Pattern 5, Steward Bounded to Format) permits recording these as source-pack decisions (this file IS
> the curator's Phase-3 mandate); it does not extend to writing new Phase-1/2 artifacts on another
> role's behalf.

---

## Retired premises

> Паттерн 1 (DPF-KNOWLEDGE-CURATION): устаревшее выносится управляемо в отдельную секцию, не
> переписывается «начисто» и не смешивается с обычными rejected-строками (те — сознательный выбор при
> отборе; retired — то, что было ПРИНЯТО, затем опровергнуто evidence в ходе того же конвейера).

- **RP-1 — «kombu `Hub` предоставляет self-pipe-style cross-thread wakeup primitive».** Изначально
  внесено в `sota-research.md` (Phase 1) как часть T2-C4, с пометкой самого автора Phase 1 «medium
  confidence, repair-candidate». В Фазе 2 прямое чтение установленного kombu 5.6.2
  (`kombu/asynchronous/hub.py`) показало обратное: такого примитива нет (`os.pipe`/self-pipe/
  `*_threadsafe`/`wakeup` — отсутствуют; есть только `call_soon`/`call_later` не-threadsafe и
  `poll(timeout)`). Статус: **retired, заменено на CE2** (kombu Hub — контрпример «single-thread
  реактор ≠ multithread-safe владелец», а не пример готового примитива). Остальная часть T2-C4
  (single-threaded reactor loop, один поток на lifecycle) НЕ retired — держится как подтверждённый
  факт. Явно зафиксировано в строке S7 выше и в `theses-antitheses.md` §5, не удалено оттуда, а
  процитировано сюда дословно (faithful compression, DPF-KNOWLEDGE-CURATION Паттерн 3).

Помимо RP-1 — **ноль** дополнительных retired premises в этом прогоне: остальные Phase 1/2 claim'ы,
включая T5 (parked, не retired — паркинг ≠ опровержение) и AI-срез (низкая уверенность, но не
опровергнут — просто не проверен), остаются в статусе, присвоенном исходными фазами, без изменений
этим прогоном курирования.

---

## Открытые provenance-вопросы

> Адресованы owner-роли (architect) и/или facilitator — куратор фиксирует, не решает содержательно
> (Паттерн 5 DPF-KNOWLEDGE-CURATION: steward мандата на формат, не на домен).

1. **Web-verification S1–S13 не выполнена.** Весь литературный/документационный корпус (POSA2, pika,
   RabbitMQ, Kafka, libuv, asyncio, Redis, Qt, Android) держится на pretrain recall this run
   (customer-mandated pretrain-only mode, 2026-07-14). Ни один из этих claim'ов не должен считаться
   `admissibleForDeclaredDPFUse`-grade evidence в Фазе 6 без явного web-repair прохода — это уже
   зафиксировано в `sota-research.md` и `theses-antitheses.md`, куратор не переоткрывает, а переносит
   предупреждение дословно вперёд, во входы Фазы 5.
   **Обновление 2026-07-14 (repair round):** выполнена — 11 из 13 (S1–S13) подтверждены как заявлено,
   один (S6) уточнён, и смежный S14 частично исправлен (см. строку S14 выше и `references/
   web-verification-2026-07-14.md`). Является ли это достаточным, чтобы поднять D11 (E.4.DPF.DA) выше
   пола 4, — решает независимый guardian в круге 2 повторной проверки (Mode C), не куратор
   единолично (Паттерн 5).
2. **AI-срез (S15/AI-F1–F5, Тезис 6) — слабее T1–T4 по конструкции.** Нет единого цитируемого
   источника; синтез diffuse pretrain-наблюдений. Repair-кандидат: целевой web-поиск опубликованных
   эмпирических исследований LLM-generated concurrency bugs, если/когда веб-доступ вернётся в scope.
   Не решается куратором — адресовано будущей Фазе 6/architect.
3. **T5 (DB-driver традиция, psycopg2/libpq) осталась parked.** Промоушен из parked в full Tradition не
   потребовался для Bridge (Фаза 2) — использован только как CE3. Если будущая ревизия найдёт его
   несущим для какого-то нового тезиса, это точечный follow-up, не переоткрытие всего харвеста
   (унаследовано из `sota-research.md` Freshness register).
4. **Три пути, названные в задании курирования, не существуют в этом репозитории на момент прогона**
   (`project/domain.md`, `project/decisions/`, `project/frameworks/competency-map.md`) — проверено
   `ls` этим прогоном, 2026-07-14. Это не содержательный provenance-вопрос о качестве какого-то
   источника, а вопрос о состоянии самого репозитория: либо эти артефакты ещё не заведены для этого
   DPF-каталога (`kombu-pyamqp-threadsafe/project/`), либо задание ссылалось на путь по шаблону другого
   проекта. Адресовано facilitator/architect — куратор не создаёт эти файлы и не выдумывает их
   содержимое задним числом (A.10 Weightless claims guard).
5. **Механизм автодетекта расхождения между `sota-research.md`/`theses-antitheses.md` и будущим
   `DPF.md` при последующих правках метода** не выбран (унаследовано как открытый provenance-вопрос из
   родственной компетенции DPF-KNOWLEDGE-CURATION, применимо и здесь по аналогии Canon-Mirror Discipline
   — но НЕ переоткрывается как самостоятельный research здесь, только упомянуто как forward-looking
   зависимость для Фазы 5/6).

---

## Гейт самопроверки (DPF-KNOWLEDGE-CURATION, Режим A)

- [x] У каждого источника (S1–S23, три phase-артефакта, два verified-this-run file-read, FPF-Spec live
      grep, method.md канон, три отсутствующих контекстных пути) — явное решение adopted/rejected.
- [x] Retired-секция присутствует, не пустая молча: RP-1 (T2-C4 self-pipe под-claim, falsified this
      run) + явная строка «ноль дополнительных» с обоснованием (парковка ≠ retirement).
- [x] Открытые provenance-вопросы перечислены (5 пунктов) и адресованы конкретной роли
      (architect/facilitator), не решены куратором единолично; пункт 1 обновлён с результатом
      web-verification 2026-07-14 (репарация), не закрыт молча.
- [x] Провенанс зафиксирован в момент решения об источнике (этот файл пишется по итогам Фаз 0–2,
      непосредственно перед Фазой 5 Assemble — не постфактум под готовый DPF.md, который в этом
      каталоге ещё не существует).
- [x] Реестр не переписывает существующие Phase 1/2 решения «начисто» — цитирует их дословно
      (self-pipe falsification, S3/S14 park-причины) вместо пересказа своими словами.

**Repair round 2026-07-14 (Mode C, круг 1):** дописаны verification-поля S1–S6/S9–S14 (были
`pretrain recall`/`pending`, дописано `verified <дата>, <URL>`, старый текст сохранён — Паттерн 1); S14
частично исправлен с явной пометкой (не переписан молча); 8 новых строк S16–S23 добавлены для
источников новых Паттернов 7–8 в `DPF.md`. Adoption-решения S1–S15 не изменены. Подробности —
`quality-record-2026-07-14.md` и `web-verification-2026-07-14.md` в каталоге `DPF-DEDICATED-IO-THREAD`.
