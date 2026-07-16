# Planner Output — FEAT-0001 ConnectionDrainer (гибридный шаг 1+2)

**Mode:** execution
**Generated:** 2026-07-14
**Inputs read:** `FEAT-0001-PLAN-01.md` (базовый план, сверен с DPF-компетенциями; копия `~/.claude/plans/merry-squishing-aho.md`), `.claude/planner-context.md` (bootstrap 2026-07-14)
**Planner-context version:** 2026-07-14

## Task summary

- **Type:** feature
- **Size:** M — 2 модуля кода (`drainer.py` новый ~200 LOC, `__init__.py` 5 точечных правок ~80 LOC), 3 новых тест-файла (~500 LOC тестов), правка `conftest.py`, без миграций
- **Criticality:** normal по формальной шкале, но **ядро конкурентности** (циклы дренажа, локи, ожидания) — ревью-гейты как для core: после фазы ядра и в конце
- **Parallelism axis:** независимы только тестовые сценарии поверх готового ядра (бенчмарк / реконнект / фрагментация — разные файлы); всё ядро строго последовательно (каждая итерация меняет `drainer.py`/`__init__.py`)

## Execution plan

### Phase 1 — Каркас: опция и жизненный цикл (serial)
- Agent: `tdd-master:tdd-master` | Model: **sonnet** | Skills: tdd-master, functional-clarity
  - Focus: итерации 1–3 плана — опция `dedicated_drainer` (default False, доезд до `ThreadSafeConnection`), скелет `ConnectionDrainer` (start/stop/имя/идемпотентность/pid-guard/self-pipe), интеграционный старт/стоп на реальном RabbitMQ
  - Inputs: `FEAT-0001-PLAN-01.md` (§«План реализации»), `src/kombu_pyamqp_threadsafe/__init__.py:540-745`, `tests/conftest.py`
  - Outputs: `src/kombu_pyamqp_threadsafe/drainer.py` (скелет), правки `__init__/connect/collect`, `tests/test_connection_drainer.py`, `tests/test_drainer_integration.py` (первые тесты)
  - Est. tokens: ~60k | Est. wall-clock: ~15 мин

### Phase 2 — Ядро конкурентности (serial, depends on Phase 1)
- Agent: `sdlc:code-implementer` | Model: **opus** | Skills: tdd-master (RED→GREEN→REFACTOR)
  - Focus: итерации 4–6 — цикл `_run` (drain-until-dry, переиспользование `_execute_and_finish_drain`), `wait_activity` (Condition + поколения, while-ожидание), ветка в `drain_events`, ветка `close()` без внешнего лока (дедлок CloseOk), `_fail`-путь (Rule 2, `mark_for_teardown`). Обоснование Opus: нестандартный конкурентный алгоритм — профиль «ядро» из planner-context §4
  - Inputs: Phase 1 diff, `FEAT-0001-PLAN-01.md` §«Цикл дренера»/§«drain_events», требования 1–13 из компетенций (там же)
  - Outputs: рабочий `drainer.py`, правки `drain_events`/`close`, тесты итераций 4–6
  - Est. tokens: ~100k | Est. wall-clock: ~25 мин

### Gate A — Ревью ядра (serial, depends on Phase 2)
- Agent: `sdlc:code-reviewer` | Model: **opus**
  - Focus: дифф Phase 1+2 по чек-листу Pattern 6 свода `DPF-DEDICATED-IO-THREAD` (wakeup / bounded join / не-GIL-обоснования / примитивы под runtime / reconnect-guard) + П6 свода `DPF-CONCURRENT-PROGRAMMING` (инвариант каждого лока назван комментарием); найденное чинит implementer до Phase 3
  - Est. tokens: ~30k | Est. wall-clock: ~8 мин

### Phase 3 — Heartbeat (serial, depends on Gate A)
- Agent: `tdd-master:tdd-master` | Model: **sonnet** | Skills: tdd-master
  - Focus: итерация 7 — тикер в `_run` (негоциированный interval, `heartbeat_tick(rate=2)` под `_transport_lock`, `ConnectionForced` → `_fail`); RED-контроль «без опции брокер убивает по heartbeat-miss»
  - Outputs: heartbeat-ветка `_run`, тесты (интеграция + toxiproxy timeout)
  - Est. tokens: ~40k | Est. wall-clock: ~10 мин

### Phase 4 — Тестовые сценарии поверх ядра (parallel ×3, depends on Phase 3)
Три агента, три РАЗНЫХ файла — конфликтов записи нет:
- Agent: `general-purpose` | Model: **sonnet** — итерация 8: бенчмарк «публикация не ждёт дренера» (`tests/benchmarks/test_drainer_benchmarks.py`, p99 old vs new)
- Agent: `general-purpose` | Model: **sonnet** — итерация 9: реконнект с дренером (`tests/test_drainer_integration.py` — отдельный класс; сценарий 2e2cf64, отсутствие утечки потоков за M циклов)
- Agent: `general-purpose` | Model: **sonnet** — итерация 10: фрагментированные кадры через toxiproxy bandwidth (busy-spin риск из отчёта §8)
  - Est. tokens: ~90k суммарно | Est. wall-clock: ~15 мин (параллельно)
  - Найденные багфиксы — серийно после фазы (implementer, sonnet)

### Phase 5 — Регрессия и параметризация (serial, depends on Phase 4)
- Agent: `sdlc:code-implementer` | Model: **sonnet**
  - Focus: итерация 11 — полный `uv run poe test` (опция off → старый свод нетронут), параметризация 3–4 ключевых интеграционных тестов обоими режимами, фиксы
  - Est. tokens: ~50k | Est. wall-clock: ~15 мин (доминирует время прогона тестов)

### Phase 6 — Документация + финальное ревью (parallel, depends on Phase 5)
- Agent: `general-purpose` | Model: **sonnet** — итерация 12: README (секция опции, lifecycle-фраза Pattern 8, heartbeat-нота, fork), CHANGELOG
- Agent: `sdlc:code-reviewer` | Model: **opus** — финальное ревью всего диффа перед коммитом
  - Est. tokens: ~40k | Est. wall-clock: ~10 мин

## Cost estimate

| | Naive /plan-do | Optimized | Δ |
|---|---|---|---|
| Tokens | ~380k (всё serial, всё sonnet, 1 ревью) | ~410k | +8% |
| Wall-clock | ~95 мин | ~75 мин | −20% |
| $-cost (relative) | 1.0 | ~1.25 (opus на ядре и двух ревью) | +25% |

Обоснование: экономии денег нет и не заявляется — план покупает **надёжность** (Opus на конкурентном
ядре + два ревью-гейта по чек-листам компетенций) и −20% времени за счёт единственной честно
параллельной оси (три независимых тест-файла в Phase 4). Дефект в конкурентном ядре, пойманный после
релиза, стоит дороже 25% надбавки — это и есть рентабельность плана.

## Risks & human-in-the-loop gates

- **Gate 0 (активен): одобрение человека на старт реализации** — работа была явно остановлена;
  ни одна фаза не запускается без явного «поехали».
- **Gate A** после ядра (см. выше) — обязательный, конкурентный код.
- **Gate B (человек):** интерпретация бенчмарка итерации 8 — порог p99 задаёт владелец, не агент.
- **Gate C (человек):** если тест фрагментации (итерация 10) покажет реальный busy-spin — решение о
  contingency-ручке (read-timeout первого drain) за человеком; в план заложена только фиксация метрики.
- Инфраструктура: RabbitMQ + toxiproxy подняты (`docker compose -f docker-compose.test.yml up -d`,
  2026-07-14); toxiproxy-тесты авто-skip'аются при недоступности — проверить, что не заскипались молча.
- `❌ GAP (infra)` из planner-context: правка CI (workflow test.yml) — fallback: general-purpose.

## Fallback

- Opus недоступен / бюджет жмёт → Phase 2 на sonnet, Gate A усиливается: два независимых
  opus-ревьюера диффа ядра (адверсарный режим).
- Параллельная Phase 4 даёт конфликты записи → сериализовать 8→9→10.
- Toxiproxy недоступен → итерации 8/10 помечаются `skipped: infra`, план не считается выполненным
  до их прогона (без тихого «всё зелёное»).

## Текущее состояние (2026-07-14)

- Ветка `feat/dedicated-drainer` создана, коммитов нет; контейнеры RabbitMQ+toxiproxy подняты.
- Ни одной строки реализации/тестов не написано — Gate 0 не пройден.
