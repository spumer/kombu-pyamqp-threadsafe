# ISSUE-005 — solved: `_nodispatch`-путь ветки дренера диспетчит канал 0

**Статус:** closed (major).

## Фикс

`ThreadSafeConnection.drain_events` (`__init__.py`), только ветка дренера. На пути `_nodispatch=True` теперь вызывается `self._dispatch_connection_events()` (диспетч ТОЛЬКО канала 0) ДО и ПОСЛЕ `wait_activity`:

```
since = drainer.generation
if _nodispatch:
    self._dispatch_connection_events()      # channel 0 control frames only
else:
    dispatched = self._dispatch_pending_events()
    if self._should_skip_drain_with_pending_events(dispatched, timeout):
        return
drainer.wait_activity(timeout, since_generation=since)
if _nodispatch:
    self._dispatch_connection_events()
else:
    self._dispatch_pending_events()
```

Точная зеркалка легаси: `_execute_and_finish_drain` диспетчит канал 0 независимо от `_nodispatch`. `_nodispatch` подавляет доставку ТОЛЬКО прикладных каналов; control-кадры канала 0 (Close/Blocked/CloseOk) диспетчатся всегда. Буферизованный брокерский Close → `_dispatch_connection_events` → `_on_close` → `raise ConnectionForced` в ПРИКЛАДНОМ потоке (Rule 2, не в дренере → self-join не возникает). Диспетч под существующим `_connection_dispatch_lock` (non-blocking) внутри `_dispatch_connection_events`.

## Границы соблюдены

- Дренер не диспетчит (self-join не introduced): диспетч в прикладном потоке.
- `wait_activity` НЕ менялась → Gate A-тест `test_wait_prefers_buffered_activity_over_stored_exc` зелёный.
- Опция off — путь `drainer is None` не тронут (байт-в-байт).
- Легаси-ветка (`drainer is None or not should_own_reads`) не тронута.

## Evidence (RED→GREEN, реальный брокер)

Repro `DELETE /api/connections/<name>` (Close 320), поллинг `connected` 5с:
```
ДО фикса:  [dedicated=True] connected->False after None  (никогда)
ПОСЛЕ:     [dedicated=True] connected->False after 0.055s  (паритет с легаси 0.057s)
```

## Тесты

- Юнит `tests/test_connection_drainer.py::TestNodispatchDispatchesConnectionEvents` (2, без RabbitMQ, стаб-дренер): `_nodispatch=True` диспетчит канал 0 и НЕ трогает прикладные; `_nodispatch=False` путь не изменился.
- Интеграция `tests/test_drainer_integration.py::TestGracefulBrokerCloseDetection::test_connected_detects_management_kill`: реальный Close через management API (`client_properties.connection_name` + `DELETE /api/connections`), `connected→False` ≤5с; skip-guard если management API недоступен.

## Прогоны

- `pytest tests/test_connection_drainer.py tests/test_drainer_integration.py tests/test_drainer_reconnect.py` — 68 passed.
- `pytest tests/ --ignore=tests/benchmarks` — 150 passed, 0 failed (baseline до фикса 147 + 3 новых).
- `mypy src/kombu_pyamqp_threadsafe/` — Success. `ruff` drainer.py clean, формат чист.
