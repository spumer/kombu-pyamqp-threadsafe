# ISSUE-007 — Отказ heartbeat-отправки на потоке дренера уходит в `collect()` → self-stop (self-join), нарушая инвариант «дренер не зовёт collect»

- **Серьёзность:** major (blocker для heartbeat-подфичи: heartbeat активен всегда, когда согласован)
- **Файлы:**
  - `src/kombu_pyamqp_threadsafe/drainer.py:505-524` (`_tick_heartbeat` — ловит ТОЛЬКО `ConnectionForced`)
  - `src/kombu_pyamqp_threadsafe/drainer.py:492-498` (`_loop` — heartbeat-тик ПОСЛЕ проверки `transport.connected`, до дренажа)
  - `src/kombu_pyamqp_threadsafe/__init__.py:655-659` (`frame_writer` wrapper — на `OSError/SSLError` зовёт `self.collect()`)
  - `src/kombu_pyamqp_threadsafe/__init__.py:669-683` (`collect()` → `self._drainer.stop()`)
  - `.venv/lib/python3.14/site-packages/amqp/connection.py:712-713` (`send_heartbeat` → `self.frame_writer(...)`)

## Класс ошибки

Реинтродукция self-collect / self-join — ровно того класса, который дизайн явно запрещает («The drainer never calls collect()/reconnect», drainer.py:19-21), но на СТОРОНЕ ЗАПИСИ, которую Gate A не покрывал. Плюс category error классификации: не-connection `RuntimeError` доходит до ожидающих вместо ошибки соединения.

## Описание

Единственная запись, которую делает поток дренера, — heartbeat. `_tick_heartbeat` (drainer.py:519-520) под `_transport_lock` зовёт `self._conn.heartbeat_tick(rate=2)`; при наступлении срока отправки `heartbeat_tick` вызывает `send_heartbeat()` → `self.frame_writer(8,0,None,None,None)` (amqp connection.py:712-713) — это наш обёрнутый frame_writer. Его wrapper на `OSError/SSLError` от записи вызывает `self.collect()` (`__init__.py:657-659`), а `collect()` в режиме дренера зовёт `self._drainer.stop()` (`__init__.py:683`).

Поскольку всё это исполняется НА ПОТОКЕ САМОГО ДРЕНЕРА, `stop()` попадает в guard `thread is threading.current_thread()` (drainer.py:369-370) и бросает `RuntimeError("stop() called from its own drainer thread")`. Итог:
- `super().collect()` не выполняется — teardown оборван на середине (транспорт не закрыт, каналы не обнулены);
- `RuntimeError` не ловится `_tick_heartbeat` (там только `ConnectionForced`), всплывает в `_run`'s `except Exception` → `_fail(RuntimeError)`;
- ожидающие в `drain_events` получают `RuntimeError`, а не ошибку соединения: `except recoverable_connection_errors`/`except OSError` его НЕ ловят.

Достижимость. `_loop` проверяет `transport.connected` только в начале итерации (drainer.py:457), но брокерский RST/EPIPE НЕ сбрасывает этот флаг amqp — он меняется только при нашем `close()`. Значит после разрыва флаг остаётся True, а сбой всплывает именно на записи heartbeat. При «тихом» разрыве (нет входящих) сторона чтения вообще не срабатывает, и heartbeat-отправка — единственный детектор; `heartbeat_tick` зовёт `send_heartbeat()` (строка 766) ДО проверки missed-heartbeat (строка 774), поэтому OSError-от-записи опережает `ConnectionForced`.

## Доказательство (evidence — end-to-end на реальном брокере)

Коннект с heartbeat=2; закрыт сырой сокет (флаг `connected` остаётся True); вызов совершён от имени потока дренера — ровно как в `_tick_heartbeat`:

```
transport.connected (флаг True после закрытия сокета): True
send_heartbeat raised: RuntimeError: ConnectionDrainer.stop() called from its own drainer thread
  caught by _tick_heartbeat (ConnectionForced)? False
  is a recoverable connection error? False
teardown finished (transport nulled)? False   <- collect() оборван
```

Существующий тест `test_missed_heartbeat_wakes_a_blocked_waiter_with_a_recoverable_error` покрывает только сторону ПРИЁМА (broker-silence → `ConnectionForced`), сторона ОТПРАВКИ не покрыта.

## Направление фикса (без кода)

Отказ heartbeat-отправки на потоке дренера должен трактоваться как фатальная ошибка дренажа и уходить в `_fail(exc)` НАПРЯМУЮ, минуя `collect()` (как это уже сделано для ошибок чтения). Варианты: (а) расширить `except` в `_tick_heartbeat` до `connection_errors` и маршрутизировать в `_fail`, одновременно не давая wrapper'у звать `collect()` с потока дренера; (б) отправлять heartbeat в обход collect()-вызывающего wrapper'а; (в) сделать `collect()`/`stop()` из потока дренера безопасным no-self-join (например, `stop()` с потока-владельца лишь помечает терминацию, не джойнит себя). Ключевой инвариант тот же, что для канала 0: путь записи дренера НЕ должен приводить к `collect()`.
