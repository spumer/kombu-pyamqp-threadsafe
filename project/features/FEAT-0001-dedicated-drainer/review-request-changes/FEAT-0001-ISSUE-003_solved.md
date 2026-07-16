# ISSUE-003 — solved: self-pipe выделяется в `start()`, не в `__init__`

**Статус:** closed (major).

## Что было

`ConnectionDrainer.__init__` немедленно делал `os.pipe()` (2 fd), закрываемые только через `stop()` (единственный вызыватель `_close_wakeup_pipe`), а `stop()` в бою — только из `collect()`. Любой `ThreadSafeConnection(dedicated_drainer=True)`, построенный без `collect()` (исключение в `super().__init__`, короткоживущий/спекулятивный объект, `test_option_true_enables_drainer`), утекал 2 fd. При частых реконнектах — неограниченная утечка в пределе до исчерпания fd. Замер: 20 конструирований без `collect` = +40 fd, GC не освобождает.

## Фикс

Владение пайпом сдвинуто в пару `start()`/`stop()` (Pattern 8 start-timing), `drainer.py`:
- `__init__`: `self._wakeup_r = self._wakeup_w = None` (никаких fd на конструировании).
- `start()`: под `_lifecycle_lock` (single-flight) `if self._wakeup_r is None: os.pipe() + set_blocking`. Аллокация ровно один раз.
- `_close_wakeup_pipe()`: при `None`-пайпе (никогда не стартовали) — no-op, `_closed` НЕ жжётся (bare `stop()` до `start()` не портит дренер).
- `_run`/`stop()`: `assert wakeup is not None` (инвариант «живой поток ⇒ пайп выделен») + локальные переменные для сужения типа.

Несостоявшийся дренер (в т.ч. при исключении в `super().__init__`, которое идёт ПОСЛЕ конструирования дренера) больше не держит fd — конструктивно, а не через финализатор.

## Тесты (RED → GREEN)

Юнит (`tests/test_connection_drainer.py::TestWakeupPipeLifecycle`):
- `test_no_pipe_allocated_until_start` — `_wakeup_r/_wakeup_w is None` до `start()`.
- `test_pipe_created_on_start_and_closed_on_stop` — пайп появляется на `start()`, `_closed` на `stop()`.
- `test_constructing_without_start_leaks_no_fds` — 20 конструирований без `start()` → прирост fd `< 20` (был +40).

RED до фикса (`_wakeup_r` — int, прирост +40 fd), GREEN после (None, прирост ~0).
