# ISSUE-001 — Ожидающий в `wait_activity` не пробуждается при штатной остановке дренера (вечное зависание)

- **Серьёзность:** blocker
- **Файлы:**
  - `src/kombu_pyamqp_threadsafe/drainer.py:230-262` (`stop()` — не будит `_activity_cond`)
  - `src/kombu_pyamqp_threadsafe/drainer.py:271-313` (`_run` — все «чистые» выходы: `:284-285`, `:296-301`, `:303-306` — без notify)
  - `src/kombu_pyamqp_threadsafe/drainer.py:164-197` (`wait_activity` — предикат не учитывает «дренер остановлен»)
  - `src/kombu_pyamqp_threadsafe/__init__.py:669-679` (`collect()` в режиме дренера → `stop()`)

## Класс гонки / типовая ошибка

Lost-wakeup / **пробуждение доходит не по всем путям завершения** (DPF-CONCURRENT П4 «Guarded Suspension»: предикат ожидания не покрывает одно из состояний, в которое система реально может перейти). README Rule 2: «ошибки соединения доходят до КАЖДОГО ожидающего; повторный вызов после fatal — снова исключение, не зависание» — нарушено.

## Описание

`wait_activity` крутит предикат `while self._generation == since_generation and self._exc is None`. Проснуться и выйти ожидающий может только если (а) `_notify_activity` сдвинул `_generation`, либо (б) `_fail` выставил `_exc`. Оба зовут `notify_all`.

Но у дренера есть ещё три пути завершения, которые НЕ трогают `_activity_cond` и НЕ выставляют `_exc`:
1. `stop()` (`:248-249`) — пишет байт в self-pipe и джойнит поток; `_activity_cond` не уведомляется.
2. Чистое самозавершение `_run` при мёртвом транспорте (`:284-285` `transport is None or not transport.connected` → `return`).
3. `sel.select` бросил `OSError` (`:296-301`) — сокет закрыт локальным teardown → `return` без notify.

Во всех трёх случаях поток тихо умирает, `_generation` не двигается, `_exc` остаётся `None`. Прикладной поток, уже припаркованный в `wait_activity(timeout=None, ...)`, **зависает навсегда** — предикат не изменится, будить некому.

`should_own_reads` (`:109-125`) после смерти потока становится `False` и корректно возвращает НОВЫЕ вызовы `drain_events` на легаси-путь — но поток, который УЖЕ прошёл проверку `should_own_reads` и вошёл в `wait_activity`, никакой перепроверки не делает. Спасения нет.

### Боевой триггер (сводится к «stop() во время ожидания»)

- Поток C (консьюмер): `connection.drain_events(timeout=None)` → припаркован в `wait_activity`.
- Поток P (паблишер): публикация → обёртка `frame_writer` видит `not transport.connected` или ловит `OSError` (`__init__.py:648-659`) → зовёт `self.collect()`.
- `collect()` в режиме дренера (`__init__.py:670-676`) → `self._drainer.stop()` → дренер выходит чисто (без `_exc`) → `super().collect()` обнуляет транспорт.
- Поток C навсегда висит в `wait_activity`. В легаси-режиме тот же консьюмер держал бы drain сам и получил бы ошибку сокета → `RecoverableConnectionError`. **Режим дренера регрессирует Rule 2.**

## Доказательство (evidence, FPF A.10 — прогон, не чтение)

Юнит-проба на фейковом соединении (`socketpair`), два сценария; в обоих ожидающий с `timeout=None` не проснулся ни разу:

```
[stop-during-wait]              waiter woke: False; outcome: None
[clean-termination-during-wait] waiter woke: False; outcome: None
EXPECTED (if healthy): both True (waiter always wakes)
ACTUAL: stop=False, clean_termination=False
```

Существующий интеграционный тест `test_blocked_waiter_gets_recoverable_error_on_break` покрывает ТОЛЬКО путь `_fail` (удалённый RST → чтение дренера падает → `_fail` → пробуждение работает). Путь `stop()`/`collect()`-во-время-ожидания не покрыт ни одним тестом.

## Направление фикса (без кода)

Ввести у дренера терминальный признак «остановлен/оторван» (например, флаг, выставляемый в `stop()` и во ВСЕХ выходах `_run`), и:
1. При выставлении признака — `notify_all` на `_activity_cond` (обязательно под его локом).
2. Включить признак в предикат `wait_activity`: при пробуждении по нему либо вернуть управление (чтобы вызывающий ушёл на легаси-путь и там честно получил состояние сокета), либо бросить recoverable-ошибку соединения. Просто `notify` без правки предиката недостаточно — цикл `while` снова уснёт.
3. Гарантировать вызов через `finally` в `_run`, чтобы любой выход (в т.ч. неожиданный — см. ISSUE-002) освобождал ожидающих.

Проверять предпочтение «настоящий кадр важнее терминального сигнала» так же, как сейчас `_exc` уступает сдвигу `_generation` (`:189-194`), чтобы буферизованный graceful Close не потерялся.
