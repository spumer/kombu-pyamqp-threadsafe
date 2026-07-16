# ISSUE-007 — solved: отказ heartbeat-отправки на потоке дренера уходит в `_fail`, минуя `collect()`

**Статус:** closed (major). Последний блокер перед коммитом.

## Корень
Единственная запись дренера — heartbeat. `_tick_heartbeat` под `_transport_lock` зовёт `heartbeat_tick` → при сроке отправки `send_heartbeat` → наш `frame_writer`. Его error-path на `OSError/SSLError` зовёт `self.collect()` → `self._drainer.stop()`. Так как это НА ПОТОКЕ ДРЕНЕРА, `stop()` попадает в self-stop guard → `RuntimeError`. Итог: teardown оборван (super().collect() не выполнен, транспорт не обнулён); `RuntimeError` (не-connection) доходит до ожидающих вместо recoverable-ошибки; реинтродукция «дренер зовёт collect» на стороне записи. Достижимо: брокерский RST не сбрасывает `transport.connected`, а `send_heartbeat` идёт ДО проверки missed-счётчика, поэтому OSError-записи опережает ConnectionForced.

## Фикс (направление (а) из находки — как именно нейтрализован collect-путь)
Две точечные правки:

1. **`frame_writer` пропускает `collect()` для записи с потока дренера** (`__init__.py`). Добавлен `ConnectionDrainer.owns_current_thread()` (`threading.current_thread() is self._thread`). В wrapper'е: `writer_is_drainer = drainer is not None and drainer.owns_current_thread()`; оба collect()-вызова (ветка `not transport.connected` и `except OSError/SSLError`) выполняются только `if not writer_is_drainer`. Для записи дренера — collect() пропускается, ошибка ПРОБРАСЫВАЕТСЯ.

2. **`_tick_heartbeat` ловит OSError** (`drainer.py`): `except (ConnectionForced, OSError) as exc: self._fail(exc)`. Проброшенная из frame_writer OSError маршрутизируется в `_fail` (exc сохранён, `mark_for_teardown`, ожидающие получают recoverable; OSError ∈ recoverable_connection_errors → ensure() реконнектит).

Почему `owns_current_thread` — надёжный маркер: единственная запись через frame_writer на потоке дренера — heartbeat (чтения идут не через frame_writer). Значит «текущий поток == поток дренера» ⟺ «это heartbeat-запись».

## Безопасность для прикладных потоков (требование 2)
Для прикладного потока `owns_current_thread()` False → `writer_is_drainer` False → collect() зовётся как раньше. Для опции off `self._drainer is None` → `writer_is_drainer` False → путь не меняется. Поведение heartbeat/frame_writer для app-потоков и option off — байт-в-байт. Подтверждено control-тестом (`test_application_thread_write_failure_still_collects` — collect вызван).

## Требование 4 (заблокированный sendall) — не ухудшено
Фикс меняет ТОЛЬКО error-path (пропуск collect + маршрут в _fail). Сам `sendall` в heartbeat по-прежнему пишет под `_transport_lock`; если пир не читает и sendall блокируется, дренер блокируется с локом, self-pipe его не прерывает — как и до фикса. Мой фикс этого не касается и не ухудшает (узкая отдельная тема, не чинил).

## Требование 5 (мелочь) — уточнён докстринг
`ConnectionClosedIntentionally`: «remains an amqp.exceptions.ConnectionError, so existing `except amqp ...ConnectionError` blocks still catch it (note: NOT the builtin ConnectionError — amqp's is an AMQPError, not an OSError)».

## Тесты (RED→GREEN)
RED воспроизведён детерминированно: `test_drainer_thread_write_failure_reraises_without_collect` без фикса дал ровно `RuntimeError: ConnectionDrainer.stop() called from its own drainer thread` (evidence ревьюера).
- `TestFrameWriterDrainerThreadDoesNotCollect::test_drainer_thread_write_failure_reraises_without_collect` — запись с потока дренера падает OSError → пробрасывается OSError (не RuntimeError), collect не зовётся.
- `..._application_thread_write_failure_still_collects` — control: прикладной поток по-прежнему зовёт collect().
- `TestHeartbeatWriteFailure::test_tick_heartbeat_routes_write_oserror_to_fail` — `_tick_heartbeat` при OSError → `_fail`, `_exc` OSError (не RuntimeError), return False, mark_for_teardown.
- `..._heartbeat_write_failure_wakes_waiter_recoverable` — ожидающий получает OSError (recoverable), не RuntimeError.

Интеграционный тест НЕ добавлен (обосновано, требование 3): при реальном разрыве сторона ЧТЕНИЯ (`_has_input`/select видит RST как readable → read → `_fail`) недетерминированно опережает heartbeat-запись, поэтому end-to-end write-path нестабилен. Ревьюер воспроизводил вручную вызовом send_heartbeat с потока дренера — это и зеркалит детерминированный юнит (Test B получил ровно тот RuntimeError). Юниты — точная регрессия.

## Прогоны
- `pytest test_connection_drainer.py test_drainer_integration.py test_drainer_reconnect.py` — 87 passed.
- `uv run poe test` — **182 passed**, 35 deselected (baseline 178 + 4 новых).
- `mypy` — Success. `ruff` drainer.py — clean; `__init__.py` — правки (комментарий + guard) новых категорий не добавили; формат чист. FEAT/ISSUE-коды в коде/тестах отсутствуют.
