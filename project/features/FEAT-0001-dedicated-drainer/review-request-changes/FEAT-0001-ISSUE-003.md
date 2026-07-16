# ISSUE-003 — Утечка fd self-pipe: пайп открывается в конструкторе, закрывается только в `stop()`

- **Серьёзность:** major
- **Файлы:**
  - `src/kombu_pyamqp_threadsafe/drainer.py:80-81` (`os.pipe()` в `__init__` — жадное выделение)
  - `src/kombu_pyamqp_threadsafe/drainer.py:264-269` (`_close_wakeup_pipe` — единственное место закрытия)
  - `src/kombu_pyamqp_threadsafe/drainer.py:230-262` (`stop()` — единственный вызыватель `_close_wakeup_pipe`)
  - `src/kombu_pyamqp_threadsafe/__init__.py:571-575` (дренер строится в `__init__` ДО `super().__init__`)

## Класс ошибки

Resource lifecycle leak: ресурс выделяется раньше и на более широком времени жизни, чем нужно (ownership выделен не в паре start/stop, а в конструкторе). DPF-DEDICATED-IO-THREAD Pattern 8 (Start-Timing): владение должно начинаться явным триггером; здесь fd захватываются на конструировании, а не на старте потока.

## Описание

`ConnectionDrainer.__init__` немедленно делает `os.pipe()` (два fd). Закрываются они исключительно через `_close_wakeup_pipe`, а его зовёт только `stop()`. `stop()`, в свою очередь, в боевом коде вызывается только из `ThreadSafeConnection.collect()`. У дренера нет `__del__`/финализатора, GC пайп не подбирает.

Значит, любой `ThreadSafeConnection(dedicated_drainer=True)`, который построен, но не дошёл до `collect()`, утекает 2 fd:
- исключение в `super().__init__(*args, **kwargs)` (`__init__.py:575`) — оно идёт уже ПОСЛЕ конструирования дренера (`:571-573`), объект не достроен, `collect()` по нему никто не позовёт;
- короткоживущий объект соединения, созданный спекулятивно и отпущенный в GC без `connect()`/`collect()`;
- в тестах — `test_option_true_enables_drainer` конструирует такое соединение и не прибирает его.

Для приложения с частыми реконнектами (каждый цикл — новый `ThreadSafeConnection` → новый пайп) это медленная, но неограниченная утечка при любом сбойном пути, обходящем `collect()` → в пределе исчерпание fd.

## Доказательство (evidence — прогон)

20 конструирований `ThreadSafeConnection(dedicated_drainer=True)` без `connect()`/`collect()`, затем drop ссылок + `gc.collect()`:

```
fds before=4  after 20 constructs (no collect)=44  delta=40   (= 2 fd на дренер)
fds after drop+gc=44                                            (GC не освобождает)
```

## Направление фикса (без кода)

Сдвинуть выделение self-pipe из `__init__` в `start()` (парно к закрытию в `stop()`) — тогда несостоявшийся/неподнятый дренер не держит fd, а lifecycle остаётся симметричным start↔stop (Pattern 8). Как минимум — добавить надёжное закрытие пайпа на всех путях отказа конструирования соединения (или финализатор как страховку). Учесть идемпотентность: `start()` уже single-flight под `_lifecycle_lock`, туда же ложится и разовое создание пайпа.
