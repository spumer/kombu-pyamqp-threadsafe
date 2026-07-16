# Сигнал «закрыто намеренно» для ждущих консьюмеров (решение владельца)

**Статус:** done. Отдельный дифф от #11 (утечка fd).

## Проблема (заметка Gate A)
До этого ЛЮБОЙ терминальный выход дренера (включая намеренный `close()`/`collect()`) будил ожидающего в `drain_events` через `RecoverableConnectionError`. Обёрнутый в kombu `ensure()`/Consumer код уходил в реконнект и «воскрешал» намеренно закрытое приложением соединение.

## Выбор типа исключения
`ConnectionClosedIntentionally(amqp.exceptions.IrrecoverableConnectionError)` — новый класс в `drainer.py`, ре-экспортирован как `kombu_pyamqp_threadsafe.ConnectionClosedIntentionally`.

Почему `IrrecoverableConnectionError` как база (проверено по иерархии):
- **НЕ** входит в `connection.recoverable_connection_errors` → kombu `ensure()`/`_reraise_as_library_errors` его НЕ ретраит и НЕ реконнектит, пробрасывает наружу (подтверждено интеграционным тестом: `_connection_factory` не вызывается).
- Является `amqp.exceptions.ConnectionError` → существующие `except ConnectionError`-блоки ловят его, `connected` классифицирует как «не подключено».
- Отдельный подкласс (а не голый `IrrecoverableConnectionError`) — суть задачи: программно и в логах отличить намеренное закрытие от настоящего irrecoverable-сбоя. Не изобретал свой базовый — переиспользовал существующий amqp-класс.

## Механизм
- Флаг `ConnectionDrainer._intentional_stop`, выставляется в `stop()` ТОЛЬКО когда стоп реально терминирует ЖИВОЙ поток (перед записью wakeup-байта, под `_activity_cond`). Ранний выход `stop()` (поток уже мёртв) НЕ помечает — сбой, умерший сам, остаётся recoverable.
- `wait_activity` терминальная ветка расщеплена: `_intentional_stop` → `ConnectionClosedIntentionally`; иначе (чистое самозавершение по мёртвому транспорту) → `RecoverableConnectionError`.
- Приоритеты сохранены: буферизованная активность (generation) > `_exc` от `_fail` > терминал. Намеренный сигнал появляется только там, где раньше был «терминал без exc» → recoverable.

## Инварианты, которые НЕ сломаны
- Реальный сбой сокета: дренер `_fail`-ит ПЕРВЫМ (`_exc`), ожидающие получают recoverable — `_fail` outranks терминал/intentional (тест `test_fail_error_survives_a_later_intentional_stop`, интеграционный `test_blocked_waiter_gets_recoverable_error_on_break`).
- Самозавершение по мёртвому транспорту (не через stop): recoverable (требование 5, тест `test_clean_self_termination_wakes_blocked_waiter_recoverable`).
- Heartbeat-miss (ConnectionForced через `_fail`): recoverable (не тронут).
- Опция off и легаси-путь: байт-в-байт.

## Для README (Phase 6), 2-3 фразы
В режиме `dedicated_drainer` намеренное `connection.close()`/`collect()` будит потоки, висящие в `drain_events`, исключением `ConnectionClosedIntentionally` (подкласс amqp `IrrecoverableConnectionError`). Оно НЕ recoverable — обёртки `ensure()`/`Consumer` его пробрасывают, а не реконнектят, чтобы намеренно закрытое приложением соединение не воскресало. Настоящие сбои соединения (разрыв сокета, пропуск heartbeat) по-прежнему дают recoverable-ошибку и штатно реконнектят.

## Изменённые тесты (осознанно, по требованию 4)
- `TestTerminalWakeup::test_stop_wakes_blocked_waiter_with_intentional_close_error` (был `_with_recoverable_error`) — stop → ConnectionClosedIntentionally.
- `TestTerminalWakeup::test_wait_raises_intentional_after_stop_on_repeat` (был recoverable) — повтор → intentional.
- `test_clean_self_termination_wakes_blocked_waiter_recoverable` — оставлен recoverable (требование 5, усилен assert not intentional).
- `test_blocked_waiter_wakes_when_collect_stops_the_drainer` — collect() на живом соединении = намеренный teardown → intentional (докстринг/коммент обновлён).
Новые: `TestIntentionalCloseExceptionType` (иерархия), `test_fail_error_survives_a_later_intentional_stop` (приоритет), интеграционный `test_intentional_close_is_not_resurrected_by_ensure` (owner-сценарий).

## Прогоны
- `pytest test_connection_drainer.py test_drainer_integration.py test_drainer_reconnect.py` — 80 passed.
- `pytest tests/ --ignore=tests/benchmarks` — 162 passed, 0 failed (baseline 158 + 4 нетто).
- `mypy` — Success. `ruff` drainer.py — clean, формат чист. FEAT/ISSUE-коды в коде отсутствуют.
