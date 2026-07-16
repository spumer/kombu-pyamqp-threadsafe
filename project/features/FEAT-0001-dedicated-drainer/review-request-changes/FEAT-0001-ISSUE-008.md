# ISSUE-008 — Аннотация `_resolve_write_timeout(heartbeat_interval: float)` уже фактического типа `conn.heartbeat` (`int | None`)

- **Серьёзность:** minor / cosmetic (НЕ blocker; рантайм-падения нет, mypy чист, только Pyright-неточность)
- **Файлы:**
  - `src/kombu_pyamqp_threadsafe/drainer.py:541` (`def _resolve_write_timeout(self, heartbeat_interval: float)`)
  - `src/kombu_pyamqp_threadsafe/drainer.py:483` (вызов `self._resolve_write_timeout(heartbeat_interval)` с `heartbeat_interval = self._conn.heartbeat`)

## Класс

Type-imprecision, не рантайм-дефект. Параметр объявлен `float`, но реально приходит значение типа `int | None` (так его видит Pyright по стабам amqp `Connection.heartbeat`). Category: MethodDescription (аннотация) расходится с фактическим доменом значений, но capability и occurrence корректны.

## Почему это НЕ рантайм-находка (evidence)

`amqp/connection.py` присваивает `self.heartbeat` только целые: согласованный `max/min(server, client)` или `self.heartbeat = 0` (строки 434/436/440) — `None` не присваивается никогда. Значит фактически всегда `int` (0 или согласованный).

Даже если бы пришёл `None`, ветка `if not heartbeat_interval: return None` (drainer.py:552) обрабатывает `None`, `0` и `0.0` одинаково — падения нет. А `_tick_heartbeat` при `heartbeat_interval` falsy вообще не вызывается (`next_hb_at is None` → в `_loop` тик пропускается). Таким образом None-путь безопасен на всех уровнях.

`uv run mypy src/kombu_pyamqp_threadsafe/` — Success (mypy не видит проблемы, т.к. `conn.heartbeat` для него не Optional); диагностика только у Pyright.

## Направление правки (опционально, без кода)

Привести аннотацию к фактическому домену: `heartbeat_interval: "float | None"` (либо `int | None`), что снимает Pyright-диагностику и делает уже присутствующий guard `if not heartbeat_interval` самодокументируемым. Правка косметическая, коммит не блокирует.
