---
artifact: "Phase-2 Bridge / Theses-Antitheses (G.2d + E.4.DPF:3 + A.2.6 + E.4.PFR + B.5.2.1)"
dpf_id: "DPF-DEDICATED-IO-THREAD"
phase: 2
date: "2026-07-14"
role: "DPF-ADVERSARIAL-REVIEW @2026-07-06 (Mode A — Dialectical Inquiry, Bridge; owner: guardian)"
mode: "PRETRAIN-ONLY RESEARCH RUN — WebSearch/WebFetch withheld by explicit customer decision (2026-07-14). Cheap in-scope file-read repair (installed kombu source, in-repo source) WAS performed and is recorded, see Repair register."
input: "references/sota-research.md (Phase 1: 4 included traditions T1–T4 + parked T5 + AI slice, 14 CorpusLedger items)"
gate_target: "each thesis carries scope (A.2.6); conflicts not silently fused (no silent fusion); counterexamples present (A.11); typical-error catalog present incl. AI-specific (E.4.DPF:8)"
---

# DPF-DEDICATED-IO-THREAD — Phase 2: Bridge / Theses-Antitheses

> **Роль-разделение (Паттерн 1 DPF-ADVERSARIAL-REVIEW, DEC-003).** Этот артефакт пишет
> адверсарный проверяющий (guardian-функция) как ОТДЕЛЬНЫЙ проход от Phase-1 SoTA-харвеста (owner).
> Тот же агент research не делал → role-separation-gate удовлетворён, отказа по «role-separation
> violation» нет. Дисциплина применена к самому source-pack'у: каждый тезис получает ≥3
> содержательных контраргумента и явную scope-границу (фальсификатор), а НЕ подтверждение
> (митигация «AI-consensus = evidence», sota-research §Trust regime).
>
> **Структурная нота для читателя.** Это выход Фазы 2 метода `DPF-AUTHORING` для компетенции
> **DPF-DEDICATED-IO-THREAD**. На переднем плане: (1) **BridgeMatrix** согласий/расхождений 4
> включённых традиций (T1–T4) + AI-срез, с ЯВНЫМИ потерями при любом слиянии и scope каждой строки
> (no silent fusion); (2) **6 тезисов**, каждый со scope валидности (A.2.6 USM), анти-тезисом NQD ≥3
> (B.5.2.1) и типом связи (E.4.PFR); (3) **контрпримеры** (похоже-но-НЕ-применять, A.11 Sharp
> Boundary) — отдельной секцией, НЕ смешаны с анти-паттернами исполнения; (4) **каталог типовых
> ошибок** компетенции (симптом→почему→исправление→источник, вкл. 5 AI-специфичных); (5) **Repair
> register** — что проверено файловым чтением, что осталось web-repair-кандидатом. Полные ClaimSheets
> — в `sota-research.md`; собственный код репозитория — в `src/kombu_pyamqp_threadsafe/`, не здесь.
>
> **Форма сверена живьём с FPF** (Grep по `~/.claude/knowledge/fpf/FPF-Spec.md`, ред. ailev/FPF@f7c7e93f):
> E.4.DPF:3 Forces (стр. 66105) · E.4.PFR:4 relation functions (66830) · A.2.6 USM / ClaimScope (4185, лекс. §6 4291) · B.5.2.1 NQD Novelty–Quality–Diversity (37336) · A.11:2 четыре гейта + Sharp boundary (20739/20748).
>
> **Trust-cue всех claim'ов (наследуется из Фазы 1):** `pretrain recall, не верифицирован`, КРОМЕ явно
> помеченных `verified this run (file read)` в Repair register. Планка не смягчена: тезисы оценены
> честно, web-верификация зарегистрирована как явный repair-шаг, не заглажена.

---

## 1. BridgeMatrix — alignment / divergence 4 традиций (no silent fusion, E.4.DPF:3 + G.2d)

> Традиции из `sota-research.md` CorpusLedger: **[T1]** литература паттернов конкурентности
> (Reactor / Active Object / Half-Sync-Half-Async / Leader-Followers) [S1,S2]; **[T2]**
> messaging/broker client libraries (pika / RabbitMQ-Java / Kafka / kombu-Hub) [S4,S5,S6,S7];
> **[T3]** event-loop / async-runtime (libuv / asyncio / Redis io-threads) [S9,S10,S11]; **[T4]**
> GUI/UI-thread (Qt / Android Looper-Handler) [S12,S13]. **[AI]** срез LLM-generated-code failure
> modes [S15] — не полноценная традиция, held ниже T1–T4 (sota-research §AI slice). **T5** (DB-driver,
> psycopg2/libpq) — parked, вынесен в контрпримеры (CE3), не в матрицу.

| Ось | T1 Concurrency patterns | T2 Broker clients | T3 Async runtimes | T4 GUI-thread |
|---|---|---|---|---|
| **Где закреплено владение (ownership locus)** | В роли/протоколе: один поток — демультиплексор (Reactor), или scheduler Active Object; либо ротация лидера (Leader/Followers) | В выделенном IO-потоке соединения (pika/Kafka Sender/RabbitMQ frame-reader); kombu-Hub — единственный поток на весь lifecycle loop | В потоке, «владеющем» циклом: `uv_run`/loop должен крутиться из одного потока; Redis — единственный main-thread для мутации keyspace | В UI-потоке, крутящем event loop (`exec()`/`Looper`); GUI-объекты доступны только из него |
| **Что легитимирует single-owner** | Инвариант: handler в Reactor НЕ должен блокировать — иначе стопорит все handle; single-writer у Active Object убирает гонку без блокировки вызывающего | Документированный контракт: Connection/Channel НЕ thread-safe, драйвится ровно из одного потока (pika FAQ) | Документированный контракт: большинство loop-API небезопасны из другого потока при работающем loop (libuv/asyncio) | Runtime-ошибка класса `CalledFromWrongThreadException` (Android) — не стиль, а падение |
| **Именованный безопасный cross-thread crossing** | Request queue Active Object (единственный вход) | `add_callback_threadsafe` (pika); Kafka `RecordAccumulator.append`+future. **kombu-Hub: НЕТ такого примитива** (см. §Repair, CE2) | `uv_async_send` (libuv); `call_soon_threadsafe` (asyncio). Redis: cross-thread не применимо (single-main) | queued signal/slot (Qt); `Handler.post` на main `Looper` (Android) |
| **Явная потеря/риск при наивном переносе** | Reactor/HSHA пиннят один поток → может стать бутылочным горлышком (ровно то, что Leader/Followers лечит ротацией — но ценой сложного handoff-протокола) | «Делать всё на IO-потоке проще» ложно: медленный consumer-callback блокирует framing/heartbeat (RabbitMQ явно разделяет пулы, T2-C2). Kafka: слишком короткий `close(timeout)` → потеря буфера | Redis io-threads легко прочесть как «распараллелить всё» — НО Redis сознательно ОСТАВИЛ single-owner для мутации, распараллелил только socket-края (T3-C3) | GUI-примитив (post/queued-slot) переносим по ФОРМЕ, но lifecycle/heartbeat/reconnect/fork — сетевые заботы, у GUI их нет; копировать GUI-код буквально нельзя |
| **Scope строки (где НЕ держится)** | Leader/Followers применим при высокой пропускной, где один поток — bottleneck; для 1 не-thread-safe соединения ротация лидера часто избыточна | Контракт «1 поток на соединение» — про НЕ-thread-safe клиент; thread-safe клиенты (напр. сам этот репозиторий с DrainGuard) сознательно ослабляют «1 поток» до «1 turn» | «Single-owner для мутации» — про state-mutating часть; чистые IO-края (read/parse, write/serialize) законно распараллеливаются | Весь ряд T4 — про UI-state, НЕ про socket; включён показать, что идиома не сетевая-специфична, не как источник сетевых lifecycle-правил |

### Alignment (общее всем T1–T4, независимо сошлись)

Все четыре традиции независимо сходятся на **двусоставном инварианте**:

1. **Single-owner-of-the-resource-for-a-window:** доступ к не-thread-safe ресурсу (socket/connection
   или UI-state) для некоторого окна времени принадлежит РОВНО одному потоку/turn; «пусть любой
   поток трогает ресурс напрямую под общей блокировкой» ни в одной из четырёх традиций не считается
   надёжным.
2. **Единственный именованный cross-thread crossing:** не-владелец инжектирует работу через ОДИН
   узкий документированный примитив (`add_callback_threadsafe` / `uv_async_send` /
   `call_soon_threadsafe` / queued-slot / `Handler.post`), а не через «вызвать любой API из любого
   потока».

Это прямая опора будущих Паттернов 1–2 DPF и типовых ошибок №3/№6 ниже. Alignment — НЕ «все говорят
одно и то же»: они говорят одно про ФОРМУ (single-owner + narrow crossing), но закрепляют её в разных
локусах (следующий блок).

### Divergence (явно, НЕ слито — no silent fusion)

Четыре традиции закрепляют владение в **четырёх РАЗНЫХ локусах** (строка «ownership locus») и, что
важнее, расходятся по ДВУМ осям, которые нельзя усреднить:

- **Ось A — пиннинг vs ротация vs turn-taking.** T1 даёт минимум ТРИ несводимых варианта «owner»:
  (i) пиннить один поток на весь lifecycle (Reactor/HSHA); (ii) ротировать лидера
  (Leader/Followers); (iii) [инстанцирующий кейс репозитория, не традиция] per-call turn-ownership
  (`DrainGuard`: любой поток может стать драйвером на время одного `drain_events()`, остальные
  одновременные вызыватели ждут исхода). **Явная потеря при слиянии:** Leader/Followers ротирует
  «кто ЖДЁТ на сокете следующим»; DrainGuard же даёт turn «тому, кто УЖЕ хочет дренировать», не
  избирая преемника. Слить их в «ну это одно и то же turn-taking» = стереть, что у L/F есть
  handoff-протокол пре-выбора лидера, а у DrainGuard — нет (single-flight + condition-variable wait).
  Помечено в sota-research T1-C4 scope note; здесь фиксируется как конфликт, не резолвится.
- **Ось B — scope работы IO-владельца.** T2-C2 (RabbitMQ) и T3-C3 (Redis) сходятся, что владелец
  должен быть УЗКИМ (framing/heartbeat/socket-edges), а прикладную работу надо явно снимать с него —
  НО дают это РАЗНЫМИ конструкциями: RabbitMQ — второй пул диспетчеризации; Redis — оставляет
  single-thread для мутации и параллелит ТОЛЬКО socket-края. **Явная потеря при слиянии:** прочитать
  оба как «просто добавь ещё потоков» инвертирует урок Redis (там суть — что НЕ распараллеливать).
- **Контраст с инстанцирующим репозиторием (не традиция, но нельзя терять).** Классическая форма T1
  «1 OS-поток = 1 владелец на весь lifecycle соединения» и turn-taking репозитория
  (shared connection + `_transport_lock` + `DrainGuard` + `channel_thread_bindings`) — РАЗНЫЕ
  разрешения одной силы. Redis (T3-C3, «оставить single-owner для чувствительного, распараллелить
  края») — структурно БЛИЖАЙШИЙ внешний аналог выбора репозитория, но это аналогия, НЕ
  эквивалентность (Redis параллелит IO-края отдельными потоками; репозиторий сериализует доступ
  блокировкой и раздаёт turn — механизм иной). Помечено в sota-research T3-C3 relevance note;
  bridged как scope-dependent, не fused.

---

## 2. Тезисы: scope (A.2.6) + анти-тезис (NQD ≥3, B.5.2.1) + тип связи (E.4.PFR)

> Анти-тезисы построены как NQD (Novelty–Quality–Diversity, B.5.2.1): три РАЗНЫХ по вектору
> возражения (обычно: «отрицание нужды» / «claim-collapse, это одно и то же» / «неприменимо к этому
> контексту/LLM»), а не три переформулировки одного. Scope = фальсификатор тезиса (Popper-гейт в
> практической форме: «назови условие, при котором совет НЕ работает»).

### Тезис 1 — Single-owner-of-the-loop — инвариант; но «owner» имеет ТРИ неэквивалентные инстанциации, и выбор между ними — часть задачи, а не деталь
- **Формулировка.** Доступ к не-thread-safe socket/connection для окна времени должен принадлежать
  одному владельцу — но «владелец» инстанцируется как минимум тремя несводимыми способами:
  **пиннинг** одного потока на lifecycle (Reactor/HSHA, T1-C2/C3), **ротация лидера**
  (Leader/Followers, T1-C4) и **per-call turn** (DrainGuard репозитория). DPF обязан дать читателю
  распознать, какое семейство подходит его ограничениям, ДО того как он переоткроет провалы каждого
  инцидентом [S1 POSA2 ~2000; scope.md].
- **Scope (A.2.6 ClaimScope).** Держится для ОДНОГО не-thread-safe ресурса под многопоточным
  прикладным кодом. НЕ держится: (а) для пула взаимозаменяемых воркеров без персистентного
  эксклюзивного ресурса (`ThreadPoolExecutor` — CE4, non-use boundary scope.md); (б) когда клиент
  УЖЕ thread-safe нативно — тогда single-owner избыточен. Вне этого slice выбор инстанциации не
  является нагрузкой DPF.
- **Анти-тезис (NQD ≥3):**
  1. *(отрицание нужды)* «Пиннить один OS-поток на весь lifecycle — всегда правильно, зачем ещё
     turn-taking» — контраргумент: пиннинг делает поток бутылочным горлышком (ровно проблема, ради
     которой Leader/Followers и turn-taking существуют, T1-C4); а под reconnect/fork пиннутый поток
     может тихо осиротеть (scope.md, AI-F2). Один вариант оставляет класс провалов непокрытым.
  2. *(claim-collapse)* «Пиннинг, ротация лидера и turn-taking — одно и то же, просто ‘один поток за
     раз’» — контраргумент: это category error (A.7). L/F ротирует «кто ждёт следующим» с
     handoff-протоколом; DrainGuard даёт single-flight turn БЕЗ пре-выбора преемника; пиннинг вообще
     не меняет владельца. Разные контракты → разные провалы (см. Divergence Ось A).
  3. *(GIL-фолбэк, AI-специфичный)* «CPython GIL сериализует доступ, single-owner не нужен» —
     контраргумент: GIL сериализует отдельные байткод-операции, НЕ многошаговые протокольные
     переходы (open channel → send frame → await reply не атомарен даже под GIL, AI-F3). Именно этот
     класс бага `ThreadSafeChannel`/`ChannelCoordinator` репозитория и предотвращает.
- **Тип связи (E.4.PFR):** scope-dependent (какая из трёх инстанциаций верна — зависит от
  throughput/lifecycle-ограничений slice'а); conflict с «одна инстанциация покрывает всё».

### Тезис 2 — Безопасный cross-thread crossing — ЕДИНСТВЕННЫЙ именованный примитив, а не «блокировка вокруг любого API»
- **Формулировка.** Не-владелец инжектирует работу/уведомление в цикл владельца через один узкий
  документированный примитив (`add_callback_threadsafe` / `uv_async_send` / `call_soon_threadsafe` /
  queued-slot / `Handler.post`), который budит/маршалит; выставлять сам объект соединения с пометкой
  «be careful» или обкладывать произвольные вызовы блокировкой — НЕ эквивалент [S4 pika; S9 libuv;
  S10 asyncio; T4].
- **Scope (A.2.6).** Держится, когда не-владельцу нужно ДОСТАВИТЬ работу в цикл. НЕ держится как
  утверждение, что примитив делает безопасным произвольный доступ к state (он делает безопасной
  только доставку/wakeup); и НЕ применим к чисто-single-thread реактору, который такого примитива не
  имеет (kombu-Hub — CE2, у него его НЕТ, verified).
- **Анти-тезис (NQD ≥3):**
  1. *(claim-collapse)* «`threading.Lock` вокруг socket-доступа = тот же cross-thread crossing» —
     контраргумент: блокировка сериализует, но НЕ будит спящий в `poll()`/`epoll_wait` цикл; без
     wakeup-примитива не-владелец не может вырвать цикл из блокирующего ожидания (missed-wakeup,
     AI-F1). Блокировка и wakeup-примитив решают разные задачи; смешать = subtly-wrong loop.
  2. *(отрицание нужды, AI-специфичный)* «Голый `select(..., timeout=1.0)` заметит всё в пределах
     таймаута, отдельный wakeup не нужен» — контраргумент: «работает в демо» ≠ корректно; тихо
     деградирует latency/корректность (shutdown-флаг замечается через период таймаута, а не сразу).
     Именованный примитив — потому и именованный, что это единственная безопасная точка (ME2).
  3. *(неверный примитив под runtime, AI-специфичный)* «`asyncio.Queue`/`call_soon_threadsafe`
     годятся внутри plain-`threading` кода» (или наоборот) — контраргумент: примитив привязан к
     своему runtime; `call_soon_threadsafe` требует работающего asyncio-loop, в threading-коде это
     no-op/ошибка (AI-F4). Один natural-language промпт «сделай потокобезопасно» тянет оба идиома из
     одного распределения — надо выбрать под фактический runtime.
- **Тип связи:** composes с Тезисом 1 (crossing — как не-владелец достигает владельца); conflict с
  «lock = crossing» и с «expose the connection object».

### Тезис 3 — Работа IO-владельца держится УЗКОЙ; прикладная работа явно снимается с него
- **Формулировка.** Задача владеющего потока — framing/heartbeat/socket read-write; медленный или
  блокирующий прикладной callback НЕ должен исполняться на нём, иначе стопорит чтение кадров и
  heartbeat для всех (RabbitMQ разделяет пулы, T2-C2; Redis держит single-thread для мутации,
  распараллеливает только socket-края, T3-C3; Reactor-дисциплина «не блокируй handler», T1-C3).
- **Scope (A.2.6).** Матерьяльно, когда handler-работа может блокировать/долго исполняться. НЕ
  предписывает второй пул для крошечного клиента, где вся работа тривиальна (тогда отдельная
  диспетчеризация — избыточная сложность). НЕ означает «параллелить всё» (см. анти-тезис 3).
- **Анти-тезис (NQD ≥3):**
  1. *(отрицание нужды)* «Делать всё на IO-потоке проще, зачем разделять» — контраргумент: медленный
     consumer-callback на IO-потоке задерживает heartbeat → брокер рвёт соединение (RabbitMQ явно
     разнёс пулы именно поэтому, T2-C2). «Проще» покупается тихим reconnect-штормом.
  2. *(over-correction)* «Раз узко — всегда добавляй пул диспетчеризации» — контраргумент: для
     клиента, где handler тривиален, второй пул добавляет гонки и сложность без выгоды; Redis-урок
     обратный — параллелить ТОЛЬКО то, что реально параллелизуемо (socket-края), остальное оставить
     single-owner (T3-C3).
  3. *(мисчтение Redis, claim-collapse)* «Redis io-threads доказывает: распараллель IO-поток
     полностью» — контраргумент: Redis io-threads СОЗНАТЕЛЬНО ограничены read/parse и
     write/serialize краями; исполнение команд против keyspace осталось на одном main-thread. Прочесть
     как «многопоточь всё» = инвертировать решение (Divergence Ось B, ошибка №8 ниже).
- **Тип связи:** scope-dependent (нужен ли второй пул — зависит от веса handler-работы); composes с
  Тезисом 1 (узкий scope владельца — свойство роли владельца).

### Тезис 4 — Ограниченный shutdown/join обязателен; `daemon=True` без join — баг тихой потери данных
- **Формулировка.** Владеющий поток должен быть останавливаемым с ОГРАНИЧЕНИЕМ на время ожидания:
  `daemon=True` без `.join()` роняет in-flight работу при выходе процесса; `.join()` без таймаута
  может висеть вечно, если цикл не выходит сам (напр. поверх reconnect-логики). Kafka
  `producer.close()` документированно flush+join фонового Sender, опционально с таймаутом, и слишком
  короткий таймаут — документированный способ потерять буфер [S6 Kafka; AI-F2].
- **Scope (A.2.6).** Применим к любому владеющему потоку с возможной in-flight работой. НЕ про
  happy-path без буфера; и слишком КОРОТКИЙ таймаут — сам по себе способ потери (баланс, не
  «побольше=лучше»).
- **Анти-тезис (NQD ≥3):**
  1. *(отрицание нужды, AI-специфичный)* «`daemon=True` достаточно, поток умрёт с процессом» —
     контраргумент: демон-поток убивается на выходе БЕЗ flush → in-flight publish/ack тихо теряются
     (AI-F2). «Умрёт сам» = «потеряет данные молча».
  2. *(over-correction)* «Тогда `join()` без таймаута — безопаснее всего» — контраргумент: без
     таймаута `close()` виснет навсегда, как только цикл перестаёт надёжно выходить сам (ровно после
     наложения reconnect-логики репозитория). Небезопасно в другую сторону — теперь зависает
     shutdown.
  3. *(неприменимость, claim-collapse)* «`close()` вызывается редко, join можно не делать» —
     контраргумент: редкость вызова не устраняет потерю при том единственном вызове; а под fork/
     reconnect «редкий» путь становится частым. Граница join — про КАЖДЫЙ реальный shutdown, не про
     частоту.
- **Тип связи:** requires Тезис 1 (есть владелец, которого надо join'ить); conflict с
  «daemon=True as shutdown strategy».

### Тезис 5 — Reconnect / повторное овладение должно быть идемпотентным (single-flight-guarded)
- **Формулировка.** Reconnect/retry-код обязан проверить, не идёт ли reconnect УЖЕ, прежде чем
  запускать новый; иначе под всплеском ошибок он переоткрывает сокет и/или плодит новые фоновые
  потоки на каждую ошибку — N гонящихся reconnect'ов за один объект соединения [AI-F5; ME3; репозиторий
  `_teardown_lock` / `marked_for_teardown` / `ensure()`-fork guard, verified].
- **Scope (A.2.6).** Применим под БУРСТ ошибок (несколько потоков видят разрыв одновременно). НЕ про
  happy-path одиночного reconnect, где гонки нет; и это про идемпотентность ОВЛАДЕНИЯ, не про
  retry-backoff-политику как таковую (та — соседняя забота).
- **Анти-тезис (NQD ≥3):**
  1. *(наивная генерация, AI-специфичный)* «На ошибку — просто подними reconnect-поток» — контраргумент:
     без in-flight-проверки бурст ошибок плодит N потоков, гонящихся заменить одно соединение (AI-F5,
     анти-shape ME3). Плодовитость = гонка.
  2. *(over-correction, claim-collapse)* «Одна глобальная блокировка вокруг всего — и никакой
     in-flight-проверки не надо» — контраргумент: блокировка сериализует, но без флага «уже идёт»
     каждый ждавший поток по очереди выполнит ЕЩЁ ОДИН reconnect (N последовательных вместо N
     параллельных — та же потеря, растянутая во времени). Нужен именно single-flight-guard
     (`marked_for_teardown` + non-blocking `acquire`), а не просто mutex.
  3. *(отрицание, неприменимость)* «Reconnect редок, гонки не случатся» — контраргумент: разрыв
     брокера по определению виден СРАЗУ нескольким потокам (все они дренировали одно соединение) —
     бурст встроен в сценарий, а не экзотика.
- **Тип связи:** composes с Тезисом 4 (idempotent teardown — часть ограниченного shutdown); requires
  Тезис 1 (есть владение, которое переустанавливается); conflict с «reconnect-поток на каждую ошибку».

### Тезис 6 (AI) — Сгенерированный код IO-потока ВЫГЛЯДИТ полным, но систематически опускает ровно эти инварианты; ревью должно проверять их явным чек-листом
- **Формулировка.** AI-F1…F5 — не новые баги, а СТАРЫЕ классы (missed wakeup / unjoined thread /
  false-safety / wrong primitive / non-idempotent retry), которые литература T1 предупреждала
  десятилетиями. Что плаузибельно ново — ЧАСТОТА и ПРАВДОПОДОБНОСТЬ: генерированный код выглядит
  завершённым и идиоматичным, ровно эти инварианты опуская. Значит усилие ревью сдвигается с «это
  компилируется / выглядит верно» на явный чек-лист «есть ли у цикла wakeup-путь, ограниченный
  shutdown и idempotency-guard» [S15 AI slice, sota-research; синтез diffuse pretrain-наблюдений
  2022–2024].
- **Scope (A.2.6).** Применим к ревью LLM-сгенерированного concurrency/socket-кода. НЕ утверждает, что
  эти баги специфичны для LLM (они пред-LLM) и НЕ равновесен по силе доказательства с T1–T4:
  явно СЛАБЕЕ (нет одной цитируемой статьи, синтез diffuse-наблюдений — sota-research помечает S15
  low-confidence). Это направление-факт, не количественный claim.
- **Анти-тезис (NQD ≥3):**
  1. *(отрицание значимости)* «Это старые баги, LLM ничего не меняет, отдельный чек-лист не нужен» —
     контраргумент: меняется частота+правдоподобность — код проходит «выглядит верно» БЕЗ инвариантов,
     поэтому «выглядит верно» перестаёт быть фильтром; нужен explicit invariant-чек-лист, что и есть
     полезная выдача DPF (sota-research §Read on tooling impact).
  2. *(fluency-as-authority, self-applied)* «Раздел про AI звучит уверенно и по делу — можно принять
     как T1-класс evidence» — контраргумент: сам этот тезис — синтез без цитируемого носителя;
     принять его беглость за проверенность = ровно ошибка №9 (over-attribution), которую компетенция
     ловит. Помечен low-confidence, web-repair-кандидат (Repair register).
  3. *(over-generalization)* «Значит любой LLM-код по IO-потокам надо переписывать вручную» —
     контраргумент: не следует — чек-лист (wakeup? bounded join? idempotency-guard? правильный
     primitive под runtime? узкий scope владельца?) точечно проверяет 5 мест, а не отвергает генерацию
     целиком; DPF раздаёт границу, а не запрет.
- **Тип связи:** composes с Тезисами 2/4/5 (чек-лист = операционализация их инвариантов); conflict с
  «выглядит идиоматично = корректно».

---

## 3. Контрпримеры (похоже, но НЕ применять) — A.11 Sharp Boundary

> ОТДЕЛЬНО от анти-паттернов исполнения (§каталог ошибок): контрпример = «структура выглядит как эта
> компетенция, но лежит ЗА её границей». Тест каждого — одна фраза inclusion/exclusion (A.11:2 Sharp
> boundary gate).

- **CE1 — Leader/Followers как «тот же turn-taking, что DrainGuard».** Похоже: любой из пула потоков
  становится драйвером по очереди. НЕ применять как drop-in: L/F ротирует «кто ЖДЁТ на источнике
  событий следующим» и промоутит фолловера в лидеры ДО обработки события (handoff-протокол);
  DrainGuard даёт single-flight turn «тому, кто уже хочет дренировать», без пре-выбора преемника, и
  усыпляет прочих на condition variable. **Граница:** L/F про «не оставить слот ожидания пустым»;
  DrainGuard про «не пустить двоих в socket-read разом» — разные цели. [T1-C4 scope note]
- **CE2 — kombu `asynchronous.hub.Hub` как «готовый dedicated-IO-thread реактор для переиспользования
  из многих потоков».** Похоже: single-thread event-loop над сокетом, ровно «классический» dedicated
  IO-thread. НЕ применять из нескольких потоков: **прямое чтение установленного kombu 5.6.2 (Repair
  register) показывает, что у Hub НЕТ cross-thread wakeup-примитива** — есть `call_soon`/`call_later`
  (не threadsafe) и `poll(timeout)`, но нет `os.pipe`/self-pipe, нет `*_threadsafe`, нет `wakeup`.
  **Граница:** single-thread реактор ≠ multithread-safe владелец; отсутствие безопасной точки входа —
  ровно ПРИЧИНА, по которой репозиторий не переиспользовал Hub, а построил `DrainGuard` +
  `_transport_lock`. (Это ещё и коррекция over-claim'а sota-research T2-C4 — см. Repair register.)
- **CE3 — psycopg2/libpq thread-affinity как эта компетенция.** Похоже: то же ограничение «одно
  соединение нельзя из конкурентных потоков без внешней блокировки». НЕ то же семейство разрешения:
  libpq требует, чтобы ВЫЗЫВАЮЩИЙ поставил внешний mutex сам — НЕТ выделенного потока/turn и НЕТ
  собственного cross-thread примитива. **Граница:** «caller-supplied external lock, no owning thread»
  vs «owning thread/turn + marshal primitive» — adjacent-but-different, non-use boundary scope.md.
  [T5/S14, parked]
- **CE4 — `ThreadPoolExecutor` fan-out как «потоки, делающие IO».** Похоже: несколько потоков ведут
  сетевую работу. НЕ эта компетенция: пул взаимозаменяемых воркеров НЕ владеет персистентным
  эксклюзивным ресурсом между вызовами; здесь предмет — поток/turn, который ЕСТЬ точка доступа
  ресурса на отрезок времени. **Граница:** «stateless-worker owns nothing across calls» vs
  «owner-of-a-resource-for-a-window». [scope.md non-use boundary]
- **CE5 — Redis io-threads как «пример распараллеливания IO-потока».** Похоже: Redis добавил
  io-threads, значит IO-поток надо параллелить. НЕ тот урок: Redis сознательно ОСТАВИЛ single-owner
  для мутации keyspace и распараллелил ТОЛЬКО read/parse и write/serialize края. **Граница:**
  «parallelize the socket edges, keep the mutation single-owner» — цитировать Redis за «многопоточь
  всё» инвертирует его решение. [T3-C3]

---

## 4. Каталог типовых ошибок компетенции (E.4.DPF:8)

> Симптом → почему → исправление → источник. «Типовые» = и новичковые, И ошибки опытных из
> устаревшей/наивной практики. 5 из 10 — AI-специфичные. Полные ClaimSheets — `sota-research.md`.

| № | Симптом | Почему происходит | Исправление | Источник |
|---|---------|--------------------|--------------|----------|
| 1 (AI) | Цикл опрашивает голым `select(..., timeout=1.0)` как ЕДИНСТВЕННЫМ способом заметить внешнее (shutdown-флаг, новую работу) | Missed/weak wakeup: генератор выдаёт правдоподобный цикл без wakeup-примитива, «работает в демо» | Добавить именованный wakeup (self-pipe/`eventfd`/`uv_async_send`-эквивалент/condition var); таймаут — страховка, не механизм | AI-F1; ME2; T3-C1/C2 |
| 2 (AI) | `daemon=True` и `.join()` не вызывается (или join без таймаута) | Небезопасная shutdown-семантика: демон роняет in-flight работу; join без таймаута виснет | Ограниченный shutdown: явный `.join(timeout)`; на выходе — flush перед завершением | AI-F2; T2-C3 (Kafka `close(timeout)`); Тезис 4 |
| 3 (AI) | Комментарий/код обосновывает потокобезопасность общего соединения «CPython GIL всё сериализует» | Fluency-as-safety: GIL сериализует байткод-операции, не многошаговые протокольные переходы | Явно сериализовать протокольные шаги (`_transport_lock` + turn-owner), не полагаться на GIL | AI-F3; репозиторий `ThreadSafeChannel`/`ChannelCoordinator`; Тезис 1 анти-тезис 3 |
| 4 (AI) | `asyncio.Lock`/`asyncio.Queue` внутри plain-`threading` кода (или `threading.Lock` в корутине) | Wrong primitive under runtime: оба идиома отвечают одному NL-промпту «сделай потокобезопасно» | Выбрать примитив под ФАКТИЧЕСКИЙ runtime; не смешивать asyncio- и threading-примитивы | AI-F4; Тезис 2 анти-тезис 3 |
| 5 (AI) | Reconnect-код переоткрывает сокет / плодит поток на КАЖДУЮ ошибку без проверки «уже идёт» | Non-idempotent retry: под бурстом N потоков гонятся заменить одно соединение | Single-flight-guard: non-blocking `acquire` + флаг `marked_for_teardown` перед reconnect | AI-F5; ME3; репозиторий `_teardown_lock`; Тезис 5 |
| 6 | Медленный/блокирующий прикладной callback исполняется на IO-владельце → стопорит framing/heartbeat для всех | Reactor-дисциплина «не блокируй handler» нарушена; «всё на одном потоке проще» | Снять прикладную работу с владельца (второй пул) КОГДА handler может блокировать; иначе heartbeat рвётся | T1-C3; T2-C2 (RabbitMQ пулы); Тезис 3 |
| 7 | Переиспользуют single-thread реактор (kombu Hub) из нескольких потоков, полагая его «готовым потокобезопасным IO-потоком» | Single-thread реактор принят за multithread-safe владельца; у Hub НЕТ cross-thread примитива | Проверить наличие именованной safe-crossing точки ПЕРЕД многопоточным использованием; нет — строить turn/lock-слой (как DrainGuard) | CE2; verified (kombu 5.6.2 source read) |
| 8 | «Redis io-threads → распараллель IO-поток полностью» / или обратное: пиннят один поток там, где хватило бы turn-taking | Мисчтение scope: смешаны «параллелить socket-края» и «параллелить мутацию»; либо over-engineering владения | Держать single-owner для чувствительной части, параллелить только реально-параллелизуемые края (Redis-урок); выбирать инстанциацию владения под throughput | T3-C3; T1-C4; Тезис 1/3, Divergence Ось B |
| 9 (research/AI) | Источник цитируется как имеющий «cross-thread wakeup primitive» / нужное свойство БЕЗ проверки, что он реально его имеет | Over-attribution / fluency-as-authority: правдоподобная атрибуция принята за проверенную (ровно случай T2-C4 kombu Hub в этом же харвесте) | Проверять несущий claim прямым чтением источника (даже file-read дёшев); битая атрибуция = стоп-находка, коррекция в bridge | Repair register (T2-C4 falsified); Popper-гейт; метод DPF-AUTHORING error №6 |
| 10 | `fork()` при живом socket-owning потоке; ребёнок наследует fd, но не поток-владелец | Поток НЕ переживает fork (в ребёнке только вызвавший поток); осиротевший fd + отсутствующий владелец | Пере-инициализировать соединение/владение в child после fork (`ensure()`-подобный fork-guard); не делить живой сокет через fork | scope.md (survival across fork); AI-F2 (unjoined thread родственен); Тезис 5 |

---

## 5. Repair register (честные пробелы, не заглажены — A.10)

> Правило прогона: web-верификация claim'ов withheld (customer 2026-07-14), НО дешёвый in-scope
> file-read repair допустим и выполнен. Фиксируется как repair-шаг, а не как «уже verified всё».

- **VERIFIED this run (in-repo file read, `src/kombu_pyamqp_threadsafe/__init__.py`):** `DrainGuard`
  (класс, стр. 353), `_transport_lock` (RLock, стр. 549, оборачивает socket-доступ), `DrainGuard()`
  инстанс (553), `channel_thread_bindings` (defaultdict[int,set], 555; фреймы диспетчеризуются в поток
  по владению каналом), `marked_for_teardown` (455/467/496), `_teardown_lock` (827,
  single-flight teardown). → Инстанцирующие claim'ы репозитория (DrainGuard turn-taking,
  serialized transport, per-thread channel binding, idempotent teardown) — **факт, не recall.**
- **FALSIFIED / скорректировано this run (installed kombu 5.6.2 source read,
  `kombu/asynchronous/hub.py`):** sota-research **T2-C4** утверждал, что cross-thread/signal-handler
  wakeup в kombu Hub «handled by a self-pipe-style primitive». Прямое чтение: у Hub **нет**
  `os.pipe`/self-pipe, **нет** `*_threadsafe`-метода, **нет** `wakeup`; есть `call_soon`/`call_later`
  (не threadsafe) и `poll(timeout)`. → Под-claim «self-pipe primitive» — **over-attribution,
  falsified.** Основная часть T2-C4 (single-threaded reactor loop, один поток на lifecycle) — держится.
  Bridge использует коррекцию: kombu Hub НЕ член семейства «named cross-thread wakeup primitive»
  (CE2, ошибка №9), что УСИЛИВАет объяснение, почему репозиторий построил DrainGuard, а не переиспользовал Hub.
  Sota-research сам пометил T2-C4 lower-confidence и рекомендовал этот file-read — repair выполнен.
- **STILL PENDING (web-repair-кандидаты для Фазы 6 / D11 currentness):** веб-верификация S1–S13
  (POSA2, pika/RabbitMQ/Kafka docs, libuv/asyncio/Redis docs, Qt/Android docs) против живых
  документов — не выполнена (web withheld). Каждый несущий claim остаётся `pretrain recall`, кроме
  двух выше. AI-срез (S15/AI-F1…F5) — слабее T1–T4, web-repair: искать эмпирические исследования
  LLM-generated concurrency bugs. **Фаза 6 (E.4.DPF.DA) обязана взвесить этот режим в D11; ни один
  claim здесь не promotes до `admissibleForDeclaredDPFUse`-grade без web-repair-прохода.**
- **T5 (DB-driver, psycopg2/libpq)** остался parked; в Bridge понадобился только как контрпример
  (CE3), не как несущая традиция — promotion из parked не потребовался.

---

## 6. Гейт самопроверки Фазы 2 (apply-prompt Mode A, шаг «Гейт»)

- [x] **Каждый тезис со scope** (A.2.6 ClaimScope = фальсификатор): Тезисы 1–6, у каждого явная строка
  «Scope … НЕ держится: …».
- [x] **Конфликты не слиты молча** (no silent fusion): BridgeMatrix Divergence фиксирует 2 неусредняемые
  оси (пиннинг/ротация/turn; scope IO-владельца) + контраст с репозиторием как scope-dependent, не
  fused; T1-C4/DrainGuard и T3-C3/shared-connection contrasts проведены явно.
- [x] **Анти-тезис NQD ≥3** на каждый тезис (B.5.2.1): по 3 РАЗНОВЕКТОРНЫХ возражения (отрицание нужды /
  claim-collapse / неприменимость-к-runtime-или-LLM), не переформулировки.
- [x] **Контрпримеры присутствуют, ОТДЕЛЬНО от анти-паттернов** (A.11 Sharp Boundary): §3, CE1–CE5,
  каждый с одной фразой границы; каталог ошибок исполнения — отдельно в §4.
- [x] **Каталог типовых ошибок** (E.4.DPF:8): §4, 10 ошибок (симптом→почему→исправление→источник), 5
  AI-специфичных.
- [x] **Claim без источника+даты и фальсификатора → не пущен в несущие**: все тезисы с источником+scope;
  T2-C4 over-claim пойман и понижен (Repair register), не оставлен несущим.
- [x] **Role-separation-gate (Паттерн 1)**: bridge писан отдельным адверсарным проходом, не тем же
  агентом, что research.

> Статус Фазы 2: **complete.** Выход готов как вход Фазы 3 (source-pack decision) и Фазы 5 (assembly).
> Несущее предупреждение вниз по конвейеру: **T2-C4 sub-claim falsified — при сборке DPF цитировать
> kombu Hub как КОНТРаст (single-thread реактор БЕЗ safe crossing), НЕ как пример cross-thread
> primitive.**
