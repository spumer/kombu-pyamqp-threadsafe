# ISSUE-002 — Исключение в `_run` вне `_drain_into_buffers` убивает поток молча, минуя `_fail`

- **Серьёзность:** major
- **Файлы:**
  - `src/kombu_pyamqp_threadsafe/drainer.py:271-313` (`_run` — единственный catch-all это `finally: sel.close()`, без маршрута в `_fail`)
  - `src/kombu_pyamqp_threadsafe/drainer.py:291-292` (`sel.register(conn_sock)` — вне какого-либо `except`)
  - `src/kombu_pyamqp_threadsafe/drainer.py:294-301` (`except OSError` на `sel.select` — `return` без notify/`_fail`)
  - `src/kombu_pyamqp_threadsafe/drainer.py:315-343` (`_drain_until_dry` — ЕДИНСТВЕННОЕ место, где ошибка уходит в `_fail`)

## Класс гонки / типовая ошибка

Unhandled exception on the owner thread + **источник ошибки теряется** (DPF-DEDICATED-IO-THREAD Pattern 6, режим отказа «unjoined/dying thread»; DPF-CONCURRENT А.10 «collapsed scopes»: ошибка происходит в run-time, но не доходит до ожидающих). Родственно ISSUE-001 по последствию (ожидающие остаются висеть), но по другому триггеру — не штатный выход, а необработанное исключение.

## Описание

В `_fail` (запись `_exc` + `mark_for_teardown` + `notify_all`) ошибка попадает только из `_drain_until_dry` (`:333-335`, широкий `except Exception`). Всё остальное тело `_run` под `_fail` не заведено:

- `sel.register(conn_sock, ...)` (`:292`) — не в `try`. TOCTOU: между проверкой `transport.connected` (`:284`) и регистрацией сокета конкурентный локальный teardown может закрыть сокет; `sel.register` тогда бросит (`ValueError: Invalid file descriptor` на `fileno()==-1` закрытого сокета, либо `OSError`). Исключение улетает из `_run` → поток умирает с необработанным исключением (его залогирует только `threading.excepthook`), `_fail` НЕ вызван, `_exc` пуст, `notify_all` не сделан.
- `except OSError` на `sel.select` (`:296-301`) сознательно делает `return` без notify — это подпадает под ISSUE-001, но перечислено и здесь как один из «немых» выходов.
- Любая иная неожиданная ошибка в цикле (например, в `selectors`), не являющаяся тем, что ловит `_drain_until_dry`.

Последствие во всех случаях: поток мёртв, `should_own_reads` со временем станет `False` (для новых вызовов ок), но ожидающие в `wait_activity` уже припаркованы и не разбужены (см. ISSUE-001), а сама ошибка потеряна (Rule 2: до ожидающих не дошла).

## Доказательство (evidence)

Структурное (чтение): единственный вызов `self._fail(...)` в файле — `drainer.py:334`, внутри `_drain_until_dry`. Тело `_run` его не вызывает ни на одном пути. `sel.register(conn_sock)` (`:292`) лежит вне `try/except`, ближайший обработчик — `finally: sel.close()` (`:312-313`), который исключение не гасит и не маршрутизирует. Значит: любое исключение вне `_drain_into_buffers` = тихая смерть потока без пробуждения ожидающих.

## Направление фикса (без кода)

Общий с ISSUE-001 корень: гарантировать, что ЛЮБОЙ выход `_run` освобождает ожидающих. Обернуть тело `_run` так, чтобы необработанное исключение уходило в `_fail(exc)` (запись + `notify_all`), а не всплывало из `target`. Регистрацию `conn_sock` внести под тот же зонтик. `finally` должен и закрывать selector, и (через терминальный сигнал ISSUE-001) будить ожидающих независимо от причины выхода.
