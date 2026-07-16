# ISSUE-006 — solved: явный stop старого дренера в `_connection_factory`

**Статус:** closed (major). Отдельный дифф от #10.

## Корень
На путях реконнекта БЕЗ нашего `collect()` (`ensure_connection()`, ленивое восстановление property `default_channel`/`default_channel_pool`/`connection`) kombu `_connection_factory` переприсваивает `self._connection = self._establish_connection()` и НЕ зовёт collect()/close() на заменяемом объекте. Старый дренер осиротевает, самозавершается по мёртвому транспорту, но self-pipe (2 fd) закрывает только `_close_wakeup_pipe`, а его зовёт только `stop()`. Итог: **+2 fd за каждый такой реконнект** (замер: 8 циклов → +16; легаси → 0).

## Фикс
`KombuConnection._connection_factory` (`__init__.py`): под уже взятым `_transport_lock` снимок `old = self._connection` ДО `super()._connection_factory()`, и `old._drainer.stop(intentional=False)`.
- `old` может быть None (первый connect) или без дренера (опция off) — `getattr(old, "_drainer", None)` покрывает оба, поведение не меняется.
- **stop ДО super()**: схлопывает окно сосуществования старого/нового дренеров до нуля (обосновано: старый останавливается до создания нового; новый дренер стартует внутри `super()._connection_factory()` → `_establish_connection()` → `connect()`).

## Взаимодействие с #10 (пункт 2 — ключевое)
`stop()` получил параметр `intentional: bool = True`. Фабрика зовёт `stop(intentional=False)`: реконнект — это failure-driven ЗАМЕНА, не пользовательский close(). Поэтому осиротевший в `wait_activity` старого соединения консьюмер получает **recoverable**-ошибку (ensure() реконнектит), НЕ `ConnectionClosedIntentionally`.
Разбор путей:
- Старый дренер уже самозавершился чисто (transport умер тихо, без `_fail`): terminal без exc, `_intentional_stop` False → recoverable. Фабричный `stop()` находит поток мёртвым → early-return (не помечает) → закрывает пайп.
- Старый дренер ещё жив при вызове фабрики: `stop(intentional=False)` не ставит `_intentional_stop` → terminal-recoverable.
- Старый дренер `_fail`-нул (сокет-ошибка): `_exc` outranks terminal → recoverable.
Во всех случаях осиротевший ожидающий → recoverable. Проверено тестом.

## Порядок локов (пункт 4, П3)
Фабрика держит `KombuConnection._transport_lock`, затем `stop()` берёт дренеров `_lifecycle_lock` (и кратко `_activity_cond`) и джойнит старый дренер-поток. Тот поток НИКОГДА не берёт `KombuConnection._transport_lock` (использует `_transport_lock` СТАРОГО `ThreadSafeConnection` — другой объект). Инверсии нет. Джойн не держит `old._transport_lock` — только ждёт выхода потока (ограничено read_timeout_s/завершением кадра). Порядок: `KombuConnection._transport_lock → drainer._lifecycle_lock → _activity_cond`. Задокументировано в коде.

## Замер fd до/после (реальный брокер, 8 циклов close_transport + ensure_connection)
- ДО фикса (временно отключён): **delta 16** (17 → 33) = +2 fd/цикл (self-pipe осиротевшего дренера). RED воспроизведён.
- ПОСЛЕ: **delta < 8** (порог теста; net ≈0 — self-pipe освобождается, сокет меняется 1:1). GREEN.

## Тесты (RED→GREEN, `tests/test_drainer_reconnect.py`)
- `TestNoFdLeakAcrossReconnectCycles::test_ensure_connection_reconnects_do_not_leak_fds[8]` — 8 циклов ensure_connection, delta fd < cycles (RED без фикса: 16).
- `test_factory_stops_the_old_connections_drainer` — новое соединение ≠ старое, новый дренер ≠ старый, `old_drainer._closed is True` (пайп закрыт фабрикой).
- `TestOrphanedWaiterStaysRecoverable::test_reconnect_wakes_orphaned_waiter_recoverable` — консьюмер в `drain_events(None)` старого соединения + reconnect → recoverable, НЕ ConnectionClosedIntentionally.
Обновлён устаревший модульный комментарий (реконнект теперь ЯВНО стопает старый дренер).

## Прогоны
- `pytest test_connection_drainer.py test_drainer_integration.py test_drainer_reconnect.py` — 83 passed.
- `pytest tests/ --ignore=tests/benchmarks` — 165 passed, 0 failed (baseline 162 + 3 новых).
- `mypy` — Success. `ruff` drainer.py — clean; `__init__.py` — мой edit (комментарий + if) новых категорий не добавил; формат чист. FEAT-коды в коде отсутствуют.
