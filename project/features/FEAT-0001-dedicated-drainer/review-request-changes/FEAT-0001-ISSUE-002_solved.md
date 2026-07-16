# ISSUE-002 — solved: неожиданное исключение в `_run` маршрутизируется в `_fail`

**Статус:** closed (major).

## Что было

`_fail` вызывался только из `_drain_until_dry` (широкий `except Exception`). Остальное тело `_run` под `_fail` не заведено: `sel.register(conn_sock)` (TOCTOU — сокет закрыт racing-teardown, `ValueError: fd == -1`), любой сбой `selectors`. Такое исключение улетало из `target`, поток умирал молча (только `threading.excepthook`), `_exc` пуст, ожидающие не разбужены, причина потеряна (Rule 2).

## Фикс

`_run` переструктурирован (`drainer.py`):
- Тело цикла вынесено в `_loop(sel)`; `_run` оборачивает `sel.register(wakeup_r)` + `_loop` в `try/except Exception → logger.exception + self._fail(exc)`.
- `finally`: `self._terminate()` (общий с ISSUE-001 корень — будит ожидающих на любом выходе) + `sel.close()`.
- Регистрация `conn_sock` теперь внутри `_loop` → под тем же зонтиком `except` → сбой уходит в `_fail`.
- `OSError` в `sel.select` остаётся отдельной штатной веткой (чистый `return`, локальный teardown) — ожидающих будит `finally`/`_terminate`.

`BaseException` (SystemExit/KeyboardInterrupt) НЕ перехватывается — только `Exception`, fail-fast для управляющих сигналов.

## Тесты (RED → GREEN)

Юнит (`tests/test_connection_drainer.py::TestRunErrorRouting`):
- `test_sel_register_failure_routed_to_fail` — закрытый сокет до регистрации → `sel.register` бросает `ValueError` → `_exc` установлен, `mark_for_teardown` вызван.
- `test_run_error_wakes_blocked_waiter` — ожидающий, припаркованный до старта, просыпается при краше `_run`.

RED до фикса (`_exc is None` / waiter висел), GREEN после.
