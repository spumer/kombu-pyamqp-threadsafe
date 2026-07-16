# План: гибридный шаг вместо миграции на Hub — выделенный поток-дренер

## Контекст

**Откуда задача.** Исследование 2026-07-14 (`project/research/kombu-hub-research-2026-07-14.md`,
16 агентов, все ключевые утверждения проверены по исходникам kombu 5.6.2 / py-amqp 5.3.1) дало вердикт:
полная миграция thread-safe слоя на kombu Hub **отклонена** — Hub покрывает только чтение (poller +
таймеры + `call_soon`), write-path и RPC через него не проходят, wakeup-механизма из чужого потока нет
(задержка `call_soon` до 1 с), компонент в maintenance mode, прецедентов многопоточной публикации через
Hub в экосистеме нет.

**Главная боль текущего дизайна** (отчёт §7): дренер держит `_transport_lock` на всё время
**блокирующего** чтения (`__init__.py:684-685` против обёртки `frame_writer` `:607-631`) — паблишеры
стоят до прихода кадра (при `timeout=None` — неограниченно). Выбор дренера — DrainGuard
(`__init__.py:353-436`).

**Рекомендация отчёта (§8), принятая заказчиком:**
- **Шаг 1** — выделенный поток-дренер вместо DrainGuard-выборов: `poll()` без лока; при готовности
  сокета лок берётся только на `drain_events(timeout=0)` — микросекунды на готовый кадр вместо секунд
  блокирующего чтения. Кадры ложатся в существующий `channel_frame_buff` (`__init__.py:591-596`),
  диспетчеризация потоками-владельцами не меняется (`__init__.py:658-666`).
  Контрольный нюанс: под `timeout=0` частичное тело кадра busy-spin'ится в `_read`
  (`amqp/transport.py:630-637`, таймаут поднимается только на initial-чтении 7-байтного заголовка) —
  проверить нагрузочным тестом с фрагментированными кадрами (toxiproxy).
- **Шаг 2** — `heartbeat_check` на таймер IO-потока: перестаёт зависеть от каденса дрейна app-потоков.
- Шаг 3 (маршрутизация записи через IO-поток) — **вне объёма**, только по итогам бенчмарков после 1–2.

**Решения заказчика (2026-07-14):**
- Объём: шаги 1+2.
- Совместимость: новое поведение — **опция соединения, выключенная по умолчанию**; текущее поведение
  (DrainGuard) не меняется; переключение дефолта — после обкатки и бенчмарков.

**Опорные знания** (E.4.DPF.DA `admissibleForDeclaredDPFUse`, критик 2026-07-14):
- `project/frameworks/DPF-DEDICATED-IO-THREAD/DPF.md` — старт/владение/обслуживание/останов IO-потока;
  особенно Pattern 8 (Start-Timing & Lifecycle Ownership) и Pattern 7 (Bounded Write Backpressure — для
  шага 3, вне объёма); прайор-арт: pika SelectConnection, aio-pika, rabbitpy (демонический IO-поток +
  Queue + socketpair), Kafka-клиенты.
- `project/frameworks/DPF-CONCURRENT-PROGRAMMING/DPF.md` — классификация гонок, дисциплина локов,
  guarded suspension (DrainGuard — инстанциация), thread confinement, ревью-по-инварианту.
- Карта: `project/frameworks/competency-map.md`. Коммит базы: e5862b7
  (ветка `docs/dpf-competency-frameworks`).

**Ограничения проекта:** TDD обязателен (RED→GREEN→REFACTOR, скилл tdd-master); Code-Change Discipline
(не менять контракты без обсуждения, README Rule 2 — ошибки канала поднимаются в потоке-владельце);
fail-fast, без глушения исключений.

## Разведка кода (2026-07-14, все ссылки — `src/kombu_pyamqp_threadsafe/__init__.py`)

- **DrainGuard** `:353-437`: дренером становится первый захвативший `_drain_check_lock` (non-blocking,
  `start_drain` `:372-396`); остальные ждут `_drain_cond.wait` (`wait_drain_finished` `:410-436`, на
  таймаут TimeoutError НЕ бросает); исключение дренера пробрасывается ждущим через `_drain_exc`.
- **Боль**: дренер держит `_transport_lock` на весь `super().drain_events(timeout)`
  (`_execute_and_finish_drain` `:684-685`); запись каждого кадра конкурирует за тот же лок
  (обёртка `frame_writer` `:613`).
- **Буфер/диспетч** (переиспользуются без изменений): `on_inbound_method` `:591-596` складывает кадры в
  `channel_frame_buff`; доставка — только потоком-владельцем (`_dispatch_pending_events` `:658-666`,
  `channel_thread_bindings`); канал 0 — `_dispatch_connection_events` `:649` под
  `_connection_dispatch_lock`.
- **Примитивы** (8): `ThreadSafeConnection._transport_lock` `:549` (весь socket I/O),
  `_connection_dispatch_lock` `:550`, `_create_channel_lock` `:552`, DrainGuard (cond+check-lock),
  `_teardown_event` `:554`, `ChannelCoordinator._cond` `:453`, `KombuConnection._transport_lock` `:826`
  (lifecycle), `_teardown_lock` `:827`.
- **Реконнект**: наш слой сокет не кэширует (`self._transport` читается каждый раз под локом); форк
  `ensure` `:1011-1097` с условным collect по snapshot (фикс ping-pong); transport лениво в property
  `:907-913`. IO-поток обязан после реконнекта заново брать fd живого транспорта и снимать старый с
  poll — иначе класс гонок фикса 2e2cf64.
- **Heartbeat**: в нашем слое НЕ реализован вовсе; наследуется от `amqp.Connection` и тикает только
  когда кто-то дренит. Запись heartbeat-кадра пойдёт через тот же `frame_writer` → `_transport_lock`.
- **Публичный API** (не ломать): `KombuConnection` `:812` — drop-in замена `kombu.Connection`;
  `default_channel_pool`, `Producer`, `SimpleQueue/Buffer`, `add_shared_amqp_transport()`;
  README Rules 1–2 (канал не шарится; кадры диспетчатся только в потоке-владельце).
- **Тесты**: `tests/test_drain_guard.py` (многопоточные гонки), `test_drain_guard_exceptions.py`,
  `test_integration_reconnect.py` (реальный RabbitMQ, 8-поточный анти-ping-pong),
  `test_publish_collect_race.py`, `tests/benchmarks/` + toxiproxy (`docker-compose.test.yml`,
  `src/toxiproxy_client.py`). Прогон: `uv run poe test`; бенчи: `poe benchmark`.
  Busy-spin на фрагментированных кадрах при `timeout=0` (`amqp/transport.py:630-637`) тестом НЕ покрыт —
  нужен новый (toxiproxy bandwidth/latency).

## Требования из компетенций (ground-применение 2026-07-14, оба пакета admissible)

Из `DPF-DEDICATED-IO-THREAD` (паттерны P1–P8, conformance-критерии):

1. **P1 (семейство владения)** — назвать явно: read-side переходит от per-call-turn (DrainGuard) к
   **pinned owner** (выделенный поток читает всегда); write-side остаётся per-call под
   `_transport_lock`. Обоснование — устранение удержания лока поперёк блокирующего чтения.
2. **P2 (именованное пересечение)** — голый `poll(timeout=1.0)` как единственный способ заметить
   shutdown/реконнект — **типовая ошибка №1** свода: лок сериализует, но не будит поток внутри
   `poll()`. Обязателен именованный wakeup-примитив (self-pipe: `os.pipe()`/`socketpair`,
   зарегистрированный в selector) для stop() и смены транспорта. Таймаут poll — страховка, не механизм.
3. **P3 (узкая зона владельца)** — IO-поток делает только poll + `drain_events(timeout=0)` в буферы +
   heartbeat-тик; никакой прикладной работы; диспетчеризация кадров остаётся в потоках-владельцах
   (README Rule 2 сохраняется by construction).
4. **P4 (ограниченный останов)** — каждый путь остановки вызывает `.join(timeout=...)` с ненулевым
   конечным таймаутом и обработкой его истечения; `daemon=True` допустим только как страховка, не как
   стратегия останова.
5. **P5 (идемпотентное восстановление)** — пере-регистрация fd после реконнекта под single-flight
   guard (non-blocking acquire + флаг «уже в процессе»); буря ошибок → ровно одна пере-регистрация.
   Fork: поток не переживает `fork()` — в потомке владение переустанавливается явно (проверка pid /
   `os.register_at_fork`), не наследуется молча.
6. **P6 (чек-лист ревью)** — прогнать по пяти пунктам перед merge: wakeup есть; join ограничен;
   безопасность не обоснована GIL'ом; примитивы соответствуют runtime (threading, не asyncio);
   реконнект под guard.
7. **P7 (backpressure)** — вне объёма (шаг 3), но план не вводит ни одной неограниченной очереди.
8. **P8 (момент старта)** — назвать одним предложением, когда владение начинается (явный триггер),
   задокументировать и спарить с явным stop. Невидимый старт как побочный эффект несвязанного вызова —
   анти-паттерн.

Из `DPF-CONCURRENT-PROGRAMMING` (паттерны П1–П7):

9. **П1** — для каждого нового механизма назвать класс гонки, который он закрывает (order violation:
   старт потока до готовности транспорта; TOCTOU: смена транспорта между проверкой и использованием fd).
10. **П2/П7** — составные операции (снять старый fd → взять новый → зарегистрировать) под явным локом;
    shared-ссылку на transport копировать в локальную переменную перед использованием; новых
    double-checked-locking мест не вводить.
11. **П3** — при ≥2 локах документировать порядок захвата; IO-поток не держит `_transport_lock` дольше
    одного `drain_events(timeout=0)`.
12. **П4** — ожидания произвольных предикатов (прикладной `drain_events(timeout)` в новом режиме) —
    `while not predicate(): cond.wait()`, если нет документированной single-writer гарантии.
13. **П6** — каждый новый лок/условие сопровождается комментарием-инвариантом («что сломается»), в
    стиле существующих комментариев DrainGuard.

## План реализации (финал, сверен с требованиями 1–13)

**Архитектура.** Новый класс `ConnectionDrainer` в новом файле `src/kombu_pyamqp_threadsafe/drainer.py`
(в `__init__.py` — точечный diff ~80 строк). Дренер привязан **1:1 к экземпляру `ThreadSafeConnection`**:
стартует в конце `connect()`, останавливается в `collect()`/`close()`. Реконнект в kombu создаёт новый
`ThreadSafeConnection` — старый дренер умирает со старым соединением, новый рождается с новым; проблема
«заметить смену fd» растворяется конструктивно (требование 5/P5 закрыто lifecycle-ом 1:1).
Семейство владения (P1): read-side — pinned owner (дренер), write-side — per-call под `_transport_lock`
как сейчас. Rule 2 сохраняется by construction: дренер только пампит кадры в `channel_frame_buff`,
диспетчеризация — потоками-владельцами.

**Опция**: `transport_options={"dedicated_drainer": True}` (default False); доезжает до
`ThreadSafeConnection.__init__` через `establish_connection` → `kwargs.pop("dedicated_drainer", False)`.
Константа `DEDICATED_DRAINER_OPTION` в `drainer.py`.

**Жизненный цикл (P8/P4)**: старт eager-on-connect (позиция rabbitpy; publisher-only приложения
получают heartbeat, lazy-старт оставил бы их без него); `start()` идемпотентен (single-flight);
`daemon=True` как страховка + `stop(join_timeout=2.0)`: `request_stop()` под `_transport_lock`,
`join` — ПОСЛЕ выхода из with-блока; провал join → `logger.warning`; guard от self-join (дренер сам
инициировал collect из error-path `frame_writer`). Имя потока `kombu-pyamqp-drainer-<id>`.
Fork: `is_running = thread.is_alive() and self._pid == os.getpid()`.

**Механизм ожидания**: `selectors.DefaultSelector`, `EVENT_READ` на `conn.sock` **плюс self-pipe**
(`os.pipe()`, read-конец в том же selector'е; `stop()` пишет байт) — поправка к дизайну проектировщика
по требованию 2/P2 (голый tick-poll как единственный способ заметить stop — типовая ошибка №1 свода;
цена ~15 строк, выигрыш — мгновенный join в тестах и остановке). Tick цикла = `min(1.0, heartbeat/4)` —
теперь только для heartbeat-каденса и проверки живости транспорта.

**Цикл дренера**: каждый тик копирует `conn._transport` в локальную переменную (требование 10/П7);
`transport is None or not connected` → самозавершение. По readable: drain-until-dry —
`start_drain()` (DrainGuard переиспользуется как инвариант-страж «ровно один читатель», uncontended) →
`_execute_and_finish_drain(timeout=0)` (переиспользование `:679-701`: классификация исключений,
диспетч канала 0, `_drain_exc` для легаси достаются бесплатно) → `socket.timeout` = сухо;
`connection_errors`/иное → `_fail(exc)`: сохранить exc, `mark_for_teardown()`, `notify_all`, выход.
Дренер НИКОГДА не вызывает `collect()`/реконнект — субъекты teardown не множатся (гонки 2e2cf64
не воспроизводятся). После каждого удачного дренажа — `_notify_activity()` (generation += 1).

**`drain_events(timeout)` прикладного потока** — единственная новая ветка: если дренер активен →
`wait_activity(timeout)` (Condition + счётчик поколений, ожидание в while — требование 12/П4);
`_exc` дренера пробрасывается ожидающему (Rule 2); дедлайн → `socket.timeout` (сознательное отличие от
`wait_drain_finished` — здесь состояние сокета известно). Иначе — существующий путь нетронут.

**`close()`**: в drainer-режиме `super().close()` БЕЗ внешнего `_transport_lock` (иначе дедлок:
владелец лока ждёт CloseOk, читатель-дренер ждёт лок); записи сериализованы per-frame в `frame_writer`.

**Heartbeat (шаг 2)**: interval = негоциированный `conn.heartbeat` (0 → тикер выключен); на тике
`monotonic() >= _next_hb_at` → `with conn._transport_lock: conn.heartbeat_tick(rate=2)`;
`ConnectionForced` → тот же `_fail`-маршрут. README-нота: при опции свой `heartbeat_check` не нужен.

**TDD-последовательность** (каждая итерация RED→GREEN→REFACTOR; unit — фейковый conn на `socketpair`,
интеграция — реальный RabbitMQ по образцу `conftest.py`, нагрузка — toxiproxy):
1. Опция: default False, доезжает до соединения, переживает `from_kombu_connection`.
2. Lifecycle unit: старт/имя/идемпотентность/стоп/двойной стоп/pid-guard/мгновенный wakeup при stop.
3. Интеграция старт/стоп: ровно один поток после connect, ноль после close/collect (join ≤ 2 c).
4. Доставка кадров: SimpleQueue-консьюмер получает сообщение через `drain_events(timeout=5)`;
   прикладной поток никогда не избирается дренером (шпион на `start_drain`).
5. Семантика timeout: 0.3 c → `socket.timeout`; `timeout=0` мгновенно; `connected` жив на тихом
   соединении, False после разрыва.
6. Проброс исключений (Rule 2/fail-fast): разрыв при висящем `drain_events(timeout=None)` →
   recoverable error, паблишер получает `RecoverableConnectionError`, повторный вызов — снова exc.
7. Heartbeat без дрейна: heartbeat=1, никто не дренит и не публикует 4–5 c → соединение живо;
   контроль без опции → брокер убивает; heartbeat-miss через toxiproxy timeout → `ConnectionForced`.
8. Бенчмарк «публикация не ждёт дренера»: консьюмер в `drain_events(None)`, p99 publish << порога;
   сравнение со старым режимом.
9. Реконнект с дренером: `ensure()` + toxiproxy разрыв → восстановление; после M циклов живых
   дренеров ровно 1; сценарий 2e2cf64 с опцией.
10. Фрагментированные кадры (toxiproxy bandwidth, сообщение ~frame_max): доставка ок, лок удерживается
    ограниченно (busy-spin `_read` — риск из отчёта §8).
11. Регрессия: полный `uv run poe test` (опция off — весь свод нетронут); параметризация 3–4 ключевых
    интеграционных тестов обоими режимами.
12. Документация: README (опция, lifecycle-фраза P8, heartbeat, fork), CHANGELOG.

**Файлы**: `src/kombu_pyamqp_threadsafe/drainer.py` (новый), `__init__.py` (5 точек:
`__init__`/`connect`/`drain_events`/`close`/`collect`), `tests/test_connection_drainer.py`,
`tests/test_drainer_integration.py`, `tests/benchmarks/test_drainer_benchmarks.py`,
`tests/conftest.py` (фикстура/параметризация).

**Верификация**: `uv run poe test` (юнит+интеграция, RabbitMQ из docker-compose), `poe benchmark`
для №8/№10 (toxiproxy), ручной прогон examples/ с опцией.
