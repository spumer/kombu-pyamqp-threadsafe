# ISSUE-006 — Утечка 2 fd за реконнект: старый дренер осиротевает без `stop()` на пути `_connection_factory`

- **Серьёзность:** major
- **Файлы:**
  - `src/kombu_pyamqp_threadsafe/__init__.py:1247-1250` (`KombuConnection._connection_factory` — переприсваивает `_connection`, старый дренер не останавливает)
  - `src/kombu_pyamqp_threadsafe/drainer.py:316-327` (`_close_wakeup_pipe` — зовётся ТОЛЬКО из `stop()`)
  - `src/kombu_pyamqp_threadsafe/drainer.py:329-349` (`_run`/`finally` — закрывает `sel`, но НЕ self-pipe fd)
  - `.venv/lib/python3.14/site-packages/kombu/connection.py:938-943` (kombu `_connection_factory` — `self._connection = self._establish_connection()`, без collect старого)

## Класс ошибки

Resource lifecycle leak на пути восстановления. Осиротевший при реконнекте старый `ConnectionDrainer` самозавершается корректно (поток исчезает), но его self-pipe (2 fd) освобождается исключительно через `stop()`, а часть путей реконнекта `stop()`/`collect()` для старого соединения не вызывает.

## Описание

kombu реконнектит через `Connection._connection_factory` (`kombu/connection.py:938-943`), который просто переприсваивает `self._connection = self._establish_connection()` и НЕ зовёт `collect()`/`close()` на заменяемом объекте. Наш override (`__init__.py:1247-1250`) добавляет только `_transport_lock`, старый дренер тоже не останавливает.

Старый дренер осиротевает и самозавершается сам (`_loop` видит `transport.connected == False` или `OSError` в `select`) — поток исчезает в пределах poll tick. Но его self-pipe fd (`_wakeup_r`, `_wakeup_w`) закрывает только `_close_wakeup_pipe` (`drainer.py:316-327`), а его единственный вызыватель — `stop()`. На пути `_connection_factory`-без-collect `stop()` не зовётся; `_run`/`finally` (`drainer.py:343-349`) закрывает лишь `selectors`-объект, но не сам пайп. Итог: каждый такой реконнект теряет 2 fd.

Затронутые пути (реконнект без нашего `collect()`): `KombuConnection.ensure_connection()` → kombu `_ensure_connection` → `_connection_factory`; ленивое восстановление в property `default_channel`/`default_channel_pool`/`connection`. НЕ затронут форк `ensure()` (`__init__.py:1163-1180`): его условный `self.collect()` доходит до `ThreadSafeConnection.collect()` → `drainer.stop()` → `_close_wakeup_pipe`, поэтому этот путь не течёт.

Это НЕ фоновое поведение kombu, а регресс, привнесённый дренером: в легаси-режиме тот же путь освобождает ресурсы штатно (замер ниже: 0 fd против +2/цикл).

## Доказательство (evidence — прогон на реальном брокере)

8 циклов `close_transport` + `ensure_connection`, tick 1.0 с, живой дренер всегда один (самозавершение работает):

```
dedicated_drainer=True:   cycle 0..7 -> delta 2,4,6,8,10,12,14,16;  FINAL +16 fd; live drainers=1
legacy (no drainer):      cycle 0..7 -> delta 0 каждый;             FINAL  +0 fd
```

Ровно +2 fd за цикл = self-pipe (`_wakeup_r` + `_wakeup_w`) осиротевшего дренера; старый сокет закрывается штатно (в легаси delta 0). При частом реконнекте (сетевая нестабильность) — неограниченный рост до исчерпания fd.

## Направление фикса (без кода)

Останавливать старый дренер в переопределённом `_connection_factory` (`__init__.py:1247-1250`): под уже взятым `_transport_lock` снять снимок `old = self._connection` ДО `super()._connection_factory()`, и если у него есть дренер — вызвать `old._drainer.stop()` (идемпотентно; вызов из прикладного потока-реконнектора — не self-join). Это закрывает self-pipe и сокращает окно сосуществования старого/нового дренера с ~poll_tick до нуля. Корректности это не меняет (гонка benign — старый дренер не может закрыть новое соединение, доказано изоляцией состояния), только устраняет утечку и приводит поведение к легаси-паритету.
