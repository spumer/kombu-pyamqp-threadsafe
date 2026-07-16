# ISSUE-004 — solved: busy-spin фрагментированного чтения снят

**Статус:** closed (major). Решение владельца: busy-spin убираем.

## Корень (из ISSUE-004, подтверждено замером)

`_drain_into_buffers(timeout=0)` под `_transport_lock`. При timeout=0 сокет неблокирующий; `TCPTransport._read` (и `SSLTransport._read`) для продолжения тела кадра (`initial=False`) на EAGAIN делает `continue` — busy-spin в Python-цикле, пока не приедет остаток, всё это время держа `_transport_lock`. Замер (frame_max ~128КБ через slicer 512Б/16КБ/с): непрерывное удержание лока **8.30с при busy_ratio=0.972** (~97% CPU ядра).

## Дизайн-выбор

Contingency §8 «read-timeout первого drain». Реализовано три части (`drainer.py`):

1. **Малый ненулевой read-timeout вместо 0** (`_DEFAULT_READ_TIMEOUT_S = 0.1`, параметр конструктора `read_timeout_s`). `_drain_into_buffers(timeout=0.1)` → `having_timeout(0.1)` переводит сокет в blocking-with-timeout; продолжение тела **блокируется на recv** (CPU idle), а не спинится. `socket.timeout` посреди тела уходит в `read_frame`'s `except socket.timeout: self._read_buffer = read_frame_buffer + self._read_buffer` — **частичные байты сохраняются, полукадр не теряется** (проверено по исходникам py-amqp 5.3.1 и тестом).

2. **Неблокирующая dry-проверка `_has_input()` вместо блокирующего чтения** — чтобы не заменить busy-spin на удержание лока в пустом сокете (starvation писателей, ровно то, что фича устраняет). `_has_input` проверяет: `transport._read_buffer` (остаток, вычитанный recv за границу кадра — целый следующий кадр может лежать тут при пустом сокете), `sock.pending()` (SSL буферизует расшифрованные записи ниже fd, невидимо для select), и неблокирующий `select(0)` за свежими байтами + опрос stop-пайпа. Возвращает `"stop"` / `True` / `False`. Дренер берёт `_transport_lock` и читает ТОЛЬКО когда вход реально есть; сухой сокет определяется без блокирующего чтения.

3. **stop-флаг проверяется между кадрами** — `_has_input` опрашивает self-pipe в том же `select(0)`, так что длинная фрагментированная доставка прерывается между кадрами.

Почему не «блокирующая dry-проверка с малым таймаутом» (проще): она держала бы `_transport_lock` на `read_timeout_s` в конце каждого drain-цикла → бамп publish p99. `_has_input` этого избегает (см. числа p99 ниже — деградации нет).

Отвергнутая альтернатива «дробить лок посреди steady-trickle кадра»: `read_frame` атомарен (читает кадр целиком), recv при устойчивом трикле (данные каждые 2мс < таймаута) не таймаутится, так что лок держится до конца кадра. Прервать чтение посреди тела без переписывания py-amqp нельзя. Принято (требование 3): цель задачи — снять CPU-burn, не удержание лока сетевой длительности.

## Числа фрагментации (bench, `test_drainer_fragmentation.py`, frame_max @ 16КБ/с)

| | busy_ratio | lock max hold | delivered / body match |
|---|---|---|---|
| ДО | **0.972** | 8302 ms | True / True |
| ПОСЛЕ run1 | **0.002** | 8257 ms | True / True |
| ПОСЛЕ run2 | **0.003** | 3458 ms | True / True |

busy_ratio упал ~0.97 → ~0.002 (>300x), CPU больше не жжётся. Lock max hold остаётся сетевой длительности кадра (иногда дробится read-timeout'ом, run2 — 3.4с: когда межслайсовый зазор превышает 0.1с, recv таймаутится посреди кадра, лок отдаётся, чтение возобновляется). Доставка корректна.

## Числа p99 (bench, `test_drainer_benchmarks.py`, быстрая сеть)

| | dedicated_drainer p99 | legacy p99 |
|---|---|---|
| ДО task9 (timeout=0) | 2.33 ms | 1951 ms |
| ПОСЛЕ task9 | 2.32 ms | 1954 ms |

Быстрый путь (кадр целиком в буфере ОС) **не деградировал** (2.33 → 2.32 ms). `_has_input` добавляет `select(0)` дренер-потоком, но НЕ держит `_transport_lock`, поэтому паблишеров не тормозит.

## Разбор stop() во время длинного фрагментированного чтения (требование 3)

- **Между кадрами / на простое**: дренер в `_loop`'s `select` или в `_has_input`'s `select(0)` → stop-байт виден мгновенно → `_run` выходит → join < select_timeout. Отзывчиво.
- **Посреди одного кадра** (recv блокирован, лок держится): stop-байт recv не прерывает. Задержка ограничена: (i) `read_timeout_s` если пир замолчал (тогда socket.timeout → `_drain_until_dry` вернул True → `_loop` видит stop) — ≤0.1с; (ii) завершением кадра при устойчивом трикле — до frame_max/bandwidth.
- **join_timeout=2.0 при steady-trickle кадре >2с**: join истекает → `logger.warning` (существующий путь Phase 1) → поток оставлен daemon'ом, продолжает читать. `collect()` вызывает `stop()` (истёк, warning), затем `with _transport_lock: super().collect()` → **блокируется на `_transport_lock`**, который держит дренер, до конца чтения кадра (не дедлок — дренер гарантированно завершит кадр или получит ошибку сокета). После завершения кадра дренер отдаёт лок, видит stop, выходит; collect() берёт лок и рвёт транспорт. **Безопасно**, но teardown в этом патологическом случае задержан на остаток чтения кадра. Практически смягчается тем, что TCP отдаёт кадры быстро; фрагментация frame_max на 16КБ/с — искусственный нагрузочный сценарий.

## Тесты (RED доказан замером ДО; регрессия закреплена)

Юнит (`tests/test_connection_drainer.py`):
- `TestDrainUntilDry::test_reads_use_a_nonzero_timeout_not_busy_spin` — все чтения с ненулевым таймаутом.
- `TestDrainUntilDry::test_mid_frame_stall_yields_without_failing` — socket.timeout посреди кадра = yield, не fail.
- `TestHasInput` (5) — вход виден из `_read_buffer`, SSL `pending()`, сокета; stop; сухость.
- `TestPartialFramePreservedAcrossTimeout` — реальный socketpair + amqp `read_frame`: кадр, разрезанный socket.timeout'ом, пересобирается без потерь (пин контракта py-amqp).

Бенчмарк (`tests/benchmarks/test_drainer_fragmentation.py`) — доставка + body match под реальной фрагментацией; busy_ratio печатается (0.002).

## Прогоны
- `pytest test_connection_drainer.py test_drainer_integration.py test_drainer_reconnect.py` — 76 passed.
- `pytest tests/ --ignore=tests/benchmarks` — 158 passed, 0 failed (было 150 + 8 новых).
- `pytest -m benchmark test_drainer_fragmentation.py` (×2) — passed, busy_ratio 0.002/0.003.
- `pytest -m benchmark test_drainer_benchmarks.py` — passed, dedicated p99 2.32ms.
- `mypy` — Success. `ruff` drainer.py — clean. Формат чист. FEAT-коды в коде отсутствуют.
