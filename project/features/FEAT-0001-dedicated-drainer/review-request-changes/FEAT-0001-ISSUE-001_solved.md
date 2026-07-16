# ISSUE-001 — solved: терминальный сигнал будит ожидающих на ВСЕХ выходах дренера

**Статус:** closed (blocker).

## Что было

`wait_activity` просыпался только по сдвигу `_generation` (`_notify_activity`) или по `_exc` (`_fail`). Три штатных выхода дренера — `stop()`, чистое самозавершение при мёртвом транспорте, `OSError` в `sel.select` — не трогали `_activity_cond`. Поток, уже припаркованный в `wait_activity(timeout=None)`, зависал навсегда. Боевой триггер: консьюмер в `drain_events(None)` + паблишер, чей `frame_writer` зовёт `collect()` → `stop()` → тихий выход дренера → консьюмер висит. Регрессия README Rule 2 (в легаси консьюмер получил бы ошибку сокета).

## Фикс

Введён терминальный признак `ConnectionDrainer._terminated` и метод `_terminate()`:
- `_terminate()` (`drainer.py`) под `_activity_cond` ставит `_terminated = True` и делает `notify_all`.
- Вызывается из `finally` в `_run` → срабатывает на ЛЮБОМ выходе (штатный, `OSError`, краш).
- Предикат `wait_activity` расширен на `and not self._terminated`; при пробуждении по терминалу (нет нового кадра, нет `_exc`) бросается `RecoverableConnectionError("dedicated drainer stopped; connection is gone")` — паритет с легаси-путём (консьюмер, сам друнящий мёртвый сокет, получил бы recoverable-ошибку), kombu реконнектит.
- Приоритет сохранён: сдвиг `_generation` важнее и `_exc`, и `_terminated` — буферизованный graceful Close не теряется.
- `should_own_reads` теперь `is_running or _exc is not None or _terminated`: новые вызовы `drain_events` после смерти дренера маршрутизируются в ветку дренера и детерминированно получают тот же recoverable-terminal, а не читают разрушенный сокет по легаси.

## Тесты (RED → GREEN)

Юнит (`tests/test_connection_drainer.py::TestTerminalWakeup`):
- `test_stop_wakes_blocked_waiter_with_recoverable_error` — waiter в `wait_activity(None)` + `stop()` → `RecoverableConnectionError`.
- `test_clean_self_termination_wakes_blocked_waiter` — waiter + сброс `transport.connected=False` → recoverable.
- `test_wait_raises_recoverable_after_terminated_on_repeat` — повторные вызовы снова кидают (не зависают).
- `test_buffered_frame_wins_over_terminal_signal` — кадр важнее терминала.
- Обновлён `TestShouldOwnReads::test_true_after_clean_self_termination` (семантика изменилась осознанно).

Интеграция (`tests/test_drainer_integration.py`):
- `TestRule2ErrorPropagation::test_blocked_waiter_wakes_when_collect_stops_the_drainer` — боевой триггер: консьюмер в `drain_events(None)` + `collect()` → recoverable-ошибка, не зависание.

Все RED до фикса (waiter не просыпался / главный поток висел), GREEN после.
