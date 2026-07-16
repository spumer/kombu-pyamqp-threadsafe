# ISSUE-005 — `connected`/`ensure_connection` не детектируют вежливый брокерский Close в drainer-режиме

- **Серьёзность:** major (регрессия против легаси)
- **Откуда:** Phase 4 (тестировщик phase4-reconnect), воспроизводится стабильно.
- **Файлы:**
  - `src/kombu_pyamqp_threadsafe/__init__.py` — ветка дренера в `ThreadSafeConnection.drain_events` (путь `_nodispatch=True`)
  - `src/kombu_pyamqp_threadsafe/__init__.py` — `KombuConnection.connected` (зовёт `drain_events(timeout=0, _nodispatch=True)`)
  - `src/kombu_pyamqp_threadsafe/drainer.py` — `wait_activity` (видит только сдвиг generation)

## Класс ошибки

Category collapse на прикладном пути ожидания: буферизованный control-кадр канала 0 (Connection.Close) обрабатывается как «обычная активность» (generation += 1), а не как «соединение закрывается». Health-check `_nodispatch` не инспектирует канал 0 → состояние «мертво» невидимо. Регрессия README-паритета с легаси.

## Описание

Дренер по дизайну НЕ диспетчит кадры сам (иначе `CloseOk`→`_on_close_ok`→`collect`→`stop` = self-join, доказанный дедлок Gate A); он только пампит кадры в `channel_frame_buff` и двигает generation. Диспетч — прикладными потоками.

`KombuConnection.connected` проверяет живость через `self._connection.drain_events(timeout=0, _nodispatch=True)`. В drainer-режиме эта ветка `drain_events`:
1. захватывает `since = drainer.generation`;
2. при `_nodispatch=True` НЕ диспетчит ничего (ни канал 0, ни прикладные);
3. зовёт `wait_activity(0, since)` → generation уже сдвинут прочитанным Close-кадром → но `since` захвачен ПОСЛЕ, поэтому предикат «generation == since» истинен → `socket.timeout` → `connected` трактует как «жив».

Вежливый брокерский `Connection.Close` (reply-code 320, напр. `DELETE /api/connections/<name>`) лежит в `channel_frame_buff[0]` и НИКЕМ не диспетчится: дренер не диспетчит по дизайну, а прикладной `_nodispatch`-путь его пропускает. `_on_close` (который поднимает `ConnectionForced`) не вызывается. `connected` навсегда True, `ensure_connection()` ноуопит.

В легаси-режиме `connected`→`drain_events(0, _nodispatch=True)`→`_execute_and_finish_drain` диспетчит канал 0 ВСЕГДА (документированный SIDE EFFECT), поэтому Close всплывает и `connected`→False за ~0.1с.

## Доказательство (evidence — прогон на реальном брокере)

`DELETE /api/connections/<name>` (Close 320), поллинг `connected` 5с:

```
[dedicated=False] connected->False after 0.003s
[dedicated=True]  connected->False after None  (никогда за 5с)
```

Контроль: прямой `drain_events(timeout=3)` (без `_nodispatch`) в drainer-режиме Close ловит корректно (там прикладной путь диспетчит канал 0).

## Направление фикса

Чинить на ПРИКЛАДНОМ пути (дренер трогать нельзя — self-join). Ветка дренера в `drain_events` при `_nodispatch=True` должна диспетчить connection-events канала 0 прикладным потоком (существующий `_dispatch_connection_events` под `_connection_dispatch_lock`), как это делает легаси. `_nodispatch` подавляет только доставку прикладных каналов, не control канала 0. Rule 2: исключение поднимается в прикладном потоке. Не ломать Gate A-сценарий «буферизованный graceful Close важнее сырого EOF» (`wait_activity` не трогать). Опция off — байт-в-байт.
