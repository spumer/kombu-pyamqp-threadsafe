---
dpf_id: "DPF-CONCURRENT-PROGRAMMING"
name: "Конкурентное программирование: гонки, инварианты, синхронизация"
kind: "Domain Principle Framework"
owner: ["architect"]
referenced_by: ["dev", "guardian"]
status: "active"
maturity: "conformant"
edition: "1.0"
grounded_in: ["FPF E.4.DPF", "FPF E.4.DPF.DA", "FPF G.2", "FPF E.4.PFR", "FPF A.2.6", "FPF B.5.2.1", "FPF A.10", "FPF A.1.1", "FPF A.11", "FPF A.7", "FPF F.18", "FPF E.8"]
fpf_edition: "ailev/FPF@f7c7e93f (снимок 2026-07-03; локальная копия ~/.claude/knowledge/fpf/FPF-Spec.md обновлена 2026-07-06); секции E.4.DPF/E.4.DPF.DA/E.4.PFR/G.2/E.8/A.1.1/A.2.6/A.7/A.10/A.11/B.5.2.1/F.18 сверены live-grep 2026-07-14 (см. Carrier note)"
date: "2026-07-14"
updated: "2026-07-14"
review_due: "2026-09-29"
---

# DPF-CONCURRENT-PROGRAMMING: Конкурентное программирование — гонки, инварианты, синхронизация

> Компетенция: классификация состязаний (race condition/data race/TOCTOU/order violation), дисциплина
> локов и condition variable, ownership-паттерны передачи разделяемого состояния между потоками,
> ревью конкурентного Python-кода (человеческого и LLM-сгенерированного) — под GIL и с учётом того, что
> GIL перестаёт быть бесплатной гарантией (PEP 703). Owner — architect. **kind: Domain Principle
> Framework** — это предметная область (конкурентное программирование), а не локальная организационная
> практика проекта (в отличие от `DPF-KNOWLEDGE-CURATION`, `kind: Local Practice Framework`).
> Заземлён на **SoTA-ресёрч** (4 традиции + обязательный ИИ-срез; `references/sota-research.md`) и
> **bridge/тезисы-антитезисы** (`references/theses-antitheses.md`).
> Часть источников — pretrain-only, не веб-верифицирована; trust-cue каждого claim'а —
> `references/source-pack.md`, протокол веб-верификации — `references/web-verification-2026-07-14.md`.
> Оценка адекватности пакета (completeness-critic + E.4.DPF.DA) — `references/critic-review*.md`.

## Структурный отчёт носителя (CC-DPF.8 / PFM11)

- **Для кого файл и первая задача:** architect (owner) — при проектировании или ревью многопоточного
  Python-кода с разделяемым состоянием (не только AMQP/kombu — любой похожий домен: пул соединений,
  кэш, буфер очереди); dev — при реализации/самопроверке перед PR; guardian — при ревью конкурентного
  участка кода и при оценке пакета (Фаза 6, E.4.DPF.DA). Первая задача читателя — не заучить весь файл линейно,
  а найти нужный паттерн по симптому (§4) или по таблице типовых ошибок (§6) для КОНКРЕТНОГО участка
  кода, который сейчас проектируется/ревьюится.
- **Что на переднем плане:** 7 паттернов (§4) — классификация состязаний, GIL-граница атомарности,
  Coffman-условия deadlock, guarded suspension, thread confinement, ревью-по-инварианту (включая
  ИИ-специфику), видимость памяти за пределами GIL под free-threaded (Паттерн 7) — каждый с принципом
  ПЕРЕД частностью и рабочей инстанциацией
  из `kombu-pyamqp-threadsafe` (`src/kombu_pyamqp_threadsafe/__init__.py`, код прочитан и процитирован
  дословно, не пересказан).
- **Что сознательно огрублено/опущено:** полные формулировки FPF (читать живьём по ID через
  `~/.claude/knowledge/fpf/FPF-Spec.md`); BridgeMatrix целиком (5-строчная таблица alignment/divergence)
  и полный текст 6 анти-тезисов×3 на тезис — сведены здесь до одной несущей строки на паттерн, полный
  текст в `references/theses-antitheses.md`; асинхронный (asyncio) и межпроцессный домены — явно НЕ
  описаны (см. non-use boundary §1); открытые provenance-вопросы (decay-риск PEP 703, hypothesis-статус
  AI-claims) — перечислены честно в §11, не решены здесь.
- **Денора отбора паттернов:** 6 тезисов `theses-antitheses.md`, каждый прошедший gate Фазы 2 (scope +
  анти-тезис NQD≥3 + тип связи), перенесены 1:1 в паттерны Фазы 5 без добавления нового содержания —
  куратор (роль сборки) faithful-сжимает форму, не меняет domain-содержание (Паттерн 5
  `DPF-KNOWLEDGE-CURATION`: owner содержания — architect, не исполнитель Фазы 5).
- **Куда возврат:** `references/scope.md` (Фаза 0, bounded context + честно зафиксированный гэп
  отсутствующих `domain.md`/`decisions/`/`competency-map.md`), `references/sota-research.md` (Фаза 1,
  G.2a CorpusLedger 21 источник (S1–S21, pretrain) + 5 источников (S22–S26, verified
  2026-07-14) + G.2b ClaimSheets A1–A5/B1–B5/C1–C5/D1–D4/AI1–AI4 + G.2e MicroExamples ME1–ME5 + G.2c
  Operator/Object inventory), `references/theses-antitheses.md` (Фаза 2, BridgeMatrix + 6 тезисов +
  6 контрпримеров + 11 типовых ошибок), `references/source-pack.md` (Фаза 3, provenance 21+5
  источников, реестр открытых provenance-вопросов), `references/
  critic-review.md` (Фаза 6), `references/quality-record-2026-07-14.md` + `references/
  web-verification-2026-07-14.md` (процессный след правок; протокол веб-верификации), FPF живьём через Grep по
  `~/.claude/knowledge/fpf/FPF-Spec.md`.

---

## Оглавление (PFM1)

1. [Паттерны](#4-паттерны-e8--фаза-5-е4dpf4) — Классификация состязаний · GIL-граница атомарности ·
   Deadlock-условия Коффмана · Guarded Suspension · Thread confinement · Ревью-по-инварианту (ИИ) ·
   Видимость памяти за пределами GIL (free-threaded)
2. [Контекст](#1-контекст-cc-dpf1) · [Source Pack](#2-source-pack--g2-cc-dpf2) ·
   [Forces](#3-forces--тензии-e4dpf3-scoped)
3. [Связи паттернов](#5-связи-паттернов-e4pfr) · [Типовые ошибки](#6-типовые-ошибки-e4dpf8) ·
   [SoTA-Echoing](#7-sota-echoing-e4dpf11)
4. [Имена](#8-имена--f18-cc-dpf4) · [Relations](#9-relations-e4pfr) ·
   [Quality & Refresh](#11-quality--refresh-e4dpfda-cc-dpf7)
5. [Разнородные приёмочные случаи](#10-разнородные-приёмочные-случаи-d8)
6. [Артефакты каталога](#артефакты-каталога-references--assets) ·
   [Carrier note](#carrier-note-cc-dpf5) · [Conformance checklist](#conformance-checklist-e4dpf7)

---

## 1. Контекст (CC-DPF.1)

- **Bounded context:** конкурентное программирование в многопоточном (не asyncio) Python-коде, где
  несколько ОС-потоков делят один ресурс с явным жизненным циклом (сокет/соединение, канал, буфер
  данных) и должны координироваться без порчи состояния и без взаимной блокировки. Референсная
  инстанциация — `kombu-pyamqp-threadsafe`: `threading.RLock` вокруг transport/dispatch/create-channel,
  `DrainGuard` (Condition + RLock, single-active-reader), `channel_thread_bindings` (per-thread channel
  ownership с явным `change_owner()`), `threading.Event` для teardown.
- **Intended reader:** architect (owner) — проектирует/ревьюит многопоточный Python-код с разделяемым
  состоянием; dev — реализует/самопроверяет; guardian — ревьюит и проводит Фазу 6.
- **First use:** дать architect/dev словарь и чек-лист для ревью/проектирования конкурентного участка
  кода — «к какому классу гонки относится этот код, какой примитив уместен, что проверить перед merge»
  — до того, как баг проявится в проде (флаки в тестах, redundant drain, двойное чтение сокета, потеря
  события). Для `kombu-pyamqp-threadsafe` конкретно: обосновать/провалидировать существующие решения
  (RLock вокруг transport, Condition-based DrainGuard, per-thread channel ownership) через призму
  устоявшихся паттернов индустрии.
- **Non-use boundary:** НЕ asyncio/корутины (event loop, `async/await` — другая модель конкурентности,
  другие failure mode); НЕ межпроцессная конкуренция (`multiprocessing`, файловые локи между процессами
  — нет GIL, нет общей кучи); НЕ распределённая согласованность (консенсус, репликация, CAP, Redis/
  Zookeeper-локи — другой домен, сетевые партиции, а не потоки одного процесса); НЕ AMQP-протокол как
  таковой (семантика фреймов/ack/exchange routing — предметная область kombu/AMQP, не конкурентное
  программирование).
- **Owner / critic:** architect (owner); guardian (Фаза 6, критик, пакет `DPF-ADVERSARIAL-REVIEW`) —
  оценка и статус пакета: `references/critic-review*.md`.

---

## 2. Source Pack — G.2 (CC-DPF.2)

> Полный реестр provenance — [`references/source-pack.md`](references/source-pack.md): 21 источник
> исходной Фазы 3 (15 adopted / 5 rejected-как-park / 1 adopted-как-hypothesis, 0 retired, pretrain)
> + 5 источников (S22–S26, все adopted, verified 2026-07-14) = 26 источников. SoTA-
> детализация — [`references/sota-research.md`](references/sota-research.md). Bridge — [`references/
> theses-antitheses.md`](references/theses-antitheses.md). Ниже — сводка.

- **Adopted:** 4 традиции + обязательный ИИ-срез — Традиция A классическая теория ОС/формальная
  конкурентность (Silberschatz S1, Coffman S2, Hoare S3, Netzer&Miller S5, Herlihy&Shavit S6);
  Традиция B CPython/GIL-специфика (Python core docs S8, Beazley S9, Beazley&Jones S10, PEP 703/Gross
  S11); Традиция C паттерны конкурентного ПО POSA2/JCiP (Buschmann et al. S13, Goetz et al. S14, Bacon
  et al. S16); Традиция D эмпирика багов конкурентности (Lu et al. ASPLOS 2008 S17, Musuvathi/CHESS
  S18, Serebryany/TSan S19); ИИ-срез (Pearce et al. S20 — fact; агрегированное наблюдение S21 —
  явно `hypothesis`). Плюс worked-evidence — прямое чтение `src/kombu_pyamqp_threadsafe/__init__.py`
  (RLock/DrainGuard/channel_thread_bindings/Event, подтверждено чтением 2026-07-14).
- **Rejected (park, не retired):** Dijkstra-семафоры (S4 — не первичный примитив в этом bounded
  context); Lamport happens-before для распределённых систем (S7 — распределённая часть за non-use
  boundary, само понятие переиспользовано опосредованно); Hettinger PyCon-доклады (S12 — пересекается
  с S9/S10 без нового claim); Lea *Concurrent Programming in Java* (S15 — пересекается с S13/S14,
  authority-by-citation риск). Причины — избежать раздувания ledger дублями без независимого нового
  утверждения (A.11 Parsimony), не содержательное отклонение традиции.
- **Claim status:** ядро (A1–A5, B1–B3, C1–C4, D1–D2) — `fact` (durable, канонические первоисточники);
  B4 (PEP 703 free-threaded) — `fact`, но с явно повышенным **decay-риском** (самое молодое знание
  пакета, 2023, статус развёртывания не переверифицирован); AI2/AI4 (LLM чаще ошибается в тонком,
  чек-лист-следствие) — явно **`hypothesis`**, усилена пересечением с D1/D2 (`fact`), не переоткрыта
  до измеренного факта; A4 (TOCTOU) — привязан к Bishop & Dilger,
  Computing Systems 1996 (verified 2026-07-14, см. §8).
- **Currentness:** scope/sota-research/theses-antitheses/source-pack — 2026-07-14; `fpf_edition`
  сверен live-grep 2026-07-14 (см. Carrier note); часть источников — pretrain-only, не
  веб-верифицирована (trust-cue по каждому — `references/source-pack.md`; протокол верификации —
  `references/web-verification-2026-07-14.md`).

---

## 3. Forces / тензии (E.4.DPF:3, scoped)

> Источник — `references/theses-antitheses.md` BridgeMatrix + 6 анти-тезисов (полный текст NQD≥3
> на тезис — там же; здесь одна несущая строка на тезис).

| # | Тензион | Scope | Как разрешается |
|---|---------|-------|------------------|
| F-1 | **«Использую примитив» vs «примитив защищает нужный инвариант»** | Любой код с `Lock`/`dict`/`Queue`/GIL | Наличие примитива синхронизации САМО ПО СЕБЕ не доказательство потокобезопасности (BridgeMatrix Alignment) — нужен явный инвариант, который примитив защищает (Тезис 6/D2) |
| F-2 | **Data race vs race condition без общей memory location (TOCTOU/order violation)** | Классификация бага, выбор примитива | Различение не академическая роскошь: order violation не лечится локом вокруг ресурса, а требует happens-before (`Event`/`join`/`Condition`) — Тезис 1 |
| F-3 | **«GIL сериализует всё» vs составная операция vs free-threaded будущее** | GIL-сборка CPython сейчас vs PEP 703 миграция | GIL атомизирует ОДИН bytecode, не последовательность (Тезис 2); под free-threaded даже эта гарантия рушится (B4, decay-риск) |
| F-4 | **Total lock ordering (структурная гарантия) vs timeout+retry (вероятностное смягчение)** | ≥2 лока или reentrancy | Timeout превращает deadlock в livelock/starvation — замена failure mode, не устранение (Тезис 3); silent fusion этих двух гарантий недопустим |
| F-5 | **`if` (короче) vs `while` (корректно) вокруг `cond.wait()`** | Ожидание произвольного предиката на `threading.Condition` | Две независимые причины требуют `while` (spurious wakeup И notify-не-тому); экономия строки = скрытый баг (Тезис 4, A.11 «нельзя вычесть цикл без потери») |
| F-6 | **Shared-state+lock-везде vs thread confinement/ownership transfer** | Состояние делимо на владеемые-одним-потоком части | Confinement сжимает синхронизационную поверхность до одной уже-потокобезопасной границы (put/get) вместо N мест захвата — но НЕ форсится языком (Python не Rust), держится на дисциплине/тесте (Тезис 5, контрпример 4) |
| F-7 | **Срочность LLM-кодогена vs целенаправленный чек-лист ревью** | Ревью человеческого И LLM-сгенерированного конкурентного кода | LLM статистически чаще ошибается в тонком (if-vs-while, exception-safety, compound-atomicity, TOCTOU) — `hypothesis` AI2, но чек-лист опирается на пересечение с `fact` D1/D2, не на AI2 в одиночку (Тезис 6) |
| F-8 | **Fluency pretrain-изложения vs честный статус claim'а** | Claim'ы с trust-cue «pretrain recall, не верифицирован» (`references/source-pack.md`) | Ни один тезис не повышается до `fact` по гладкости текста; апгрейд trust-cue — только по верификации с источником (§11, `references/web-verification-2026-07-14.md`) |

---

## 4. Паттерны (E.8, Фаза 5 — Е.4.DPF:4)

> Правило (A.1.1): **общий принцип (SoTA) → наша инстанциация (worked slice)**. Инстанциации — прямое
> чтение `src/kombu_pyamqp_threadsafe/__init__.py` (2026-07-14), не пересказ. Полный текст тезисов,
> BridgeMatrix и всех NQD-анти-тезисов — `references/theses-antitheses.md` §2; здесь — обогащённый
> блок паттерна (E.8) на каждый тезис, faithful-сжат (сохранены scope, статусы claim, фальсификаторы,
> формулировки «не применять»).

---

### Паттерн 1: Классификация состязаний — race condition ⊋ data race; TOCTOU/order violation без единой memory location

**Recognition** — код, где два потока трогают общее состояние и «баг» не обязательно выглядит как
классическая гонка за одну ячейку памяти (например: поток B читает значение раньше, чем поток A его
инициализировал, — без конкуренции за один и тот же лок вообще).

**Принцип (SoTA-grounded).**
Race condition — исход программы зависит от непредсказуемого порядка/тайминга операций нескольких
потоков; data race — частный случай: конкурентный доступ к одной memory location без синхронизации,
где ≥1 доступ — запись (Netzer & Miller, ACM LOPLAS 1992, S5). Не всякий race condition — data race:
TOCTOU (check-then-act) и order violation — race condition без единой разделяемой ячейки в классическом
смысле (A1, A4; ранняя каноническая работа по TOCTOU в file-access — Bishop, M.; Dilger, M., *"Checking
for Race Conditions in File Accesses"*, Computing Systems, 1996, pp. 131–152, verified 2026-07-14;
исходно class check-then-act формулировался в security-литературе, но не ограничен ею, см. Паттерн 1
conformance ниже). Эмпирически
(Lu, Park, Seo, Zhou, *Learning from Mistakes*, ASPLOS 2008, S17)
atomicity violation и order violation — два доминирующих класса реальных багов конкурентности (D1).

**Наша инстанциация (worked slice).**
`ThreadSafeChannel.change_owner()` (`__init__.py:127-136`) явно управляет ownership-переходом
(`bindings[prev_owner].discard(...)`, `bindings[new_owner].add(...)`) — устраняет ИМЕННО order-violation
риск «поток читает канал до того, как владение официально передано», а не data race за одну ячейку.
`DrainGuard.wait_drain_finished()` явный `assert self._drain_is_active_by != caller, "You can not wait
your own; deadlock detected"` (`__init__.py:425`) — защита от иного класса бага (self-deadlock), не от
data race; разные классы состязаний требуют разных структурных мер, не одного лока «на всякий случай».

**Контрпример [A.11 Sharp Boundary].**
Race condition vs безобидный недетерминизм порядка: два потока пишут в лог/метрику в непредсказуемом
порядке — выглядит как race condition, но если НИКАКОЙ инвариант от этого порядка не зависит, это
benign недетерминизм, не баг (и лок здесь — лишняя сериализация, lock convoy). Тест: «зависит ли
корректность от порядка, или порядок просто наблюдаемо разный?»

**Анти-паттерн [E.8].**
«Под GIL для pure Python настоящих data race нет — значит различение академическая роскошь» — ложный
вывод: именно потому data-race-подкласс под GIL почти пуст, инструменты и интуиция из C/Java (TSan
«защити каждую memory location») промахиваются мимо реального класса — TOCTOU/atomicity violation над
составной операцией, для которого TSan-эквивалента в pure Python нет (D4).

**Conformance.**
- Перед выбором примитива синхронизации явно назван класс бага: data race / atomicity violation
  (TOCTOU) / order violation.
- Order violation НЕ «лечится» локом вокруг ресурса без установления happens-before (`Event`/`join`/
  `Condition`).
- TOCTOU-инстанции распознаются и вне ФС (`if key not in d: d[key]=...`, ленивая инициализация), не
  только в security-контексте.

**Связи [E.4.PFR].**
- **composes** с Паттерном 6 (order violation — частный случай «неверного допущения о порядке», D1/D2).
- **conflict** с «любая гонка = добавь лок» (силовое слияние классов — anti-pattern).
- **scope-dependent**: активен на этапе классификации бага/выбора примитива; НЕ несёт вес для
  single-threaded кода и распределённой согласованности (non-use boundary §1).

---

### Паттерн 2: Граница атомарности GIL — один bytecode, НЕ составная операция

**Recognition** — код полагается на GIL как на «бесплатный» мьютекс для последовательности из
нескольких операций над разделяемым объектом (`x += 1`, `d[k] = d[k] + 1`, `if k not in d: d[k] = v`).

**Принцип (SoTA-grounded).**
GIL гарантирует атомарность одной bytecode-инструкции CPython и отдельной встроенной операции
контейнера (`list.append`, `dict.__setitem__`), но НЕ атомарность последовательности из нескольких
таких операций (Python core docs FAQ «What kinds of global value mutation are thread-safe?»,
docs.python.org/3/faq/library.html, verified 2026-07-14, S8; Beazley, PyCon 2010, S9; Beazley & Jones,
*Python Cookbook* 3rd ed., 2013, гл.12, S10 — book source, verified as existing chapter, полный текст
книги не веб-сверяем). GIL освобождается явно вокруг блокирующих C-уровневых
вызовов (сетевой I/O) — переключение происходит не только по таймеру, но и в непредсказуемых точках
вокруг I/O (B2), что критично для кода, держащего составное состояние вокруг сетевого вызова.

**Наша инстанциация (worked slice).**
`ThreadSafeConnection.__init__` (`__init__.py:549-555`): `self._transport_lock = threading.RLock()`,
`self._connection_dispatch_lock = threading.RLock()`, `self._create_channel_lock = threading.RLock()`
— каждый явно оборачивает СОСТАВНУЮ операцию над transport/dispatch/channel-creation, не полагается на
атомарность отдельного bytecode. `_basic_publish` (`__init__.py:218-259`) читает `conn._transport` под
`with channel_operation(self) as conn:` — составная последовательность (снимок `conn`, проверка
`transport is None`, вызов `send_method`) защищена явным критическим участком именно потому, что
конкурентный teardown может обнулить `self.connection` МЕЖДУ шагами (комментарий в коде:
«a concurrent teardown can null self.connection mid-publish, and the resulting AttributeError is not
retried by kombu»).

**Контрпример [A.11 Sharp Boundary].**
`q.append(x)` в одном потоке и `q.pop()` в другом — каждая ОТДЕЛЬНО атомарна (B3), выглядит как «уже
потокобезопасная очередь», но `if q: x = q.pop()` — составная (check-then-act; между проверкой и pop
другой поток мог опустошить очередь). Граница: атомарность применима к ОДНОЙ встроенной операции, не
к паре «проверить-и-взять».

**Анти-паттерн [E.8].**
«PEP 703 (free-threaded) скоро сделает это неважным — там своя внутренняя синхронизация, локи руками не
нужны» — наоборот (B4): под free-threaded инварианты «атомарность отдельного bytecode/встроенной
операции» перестают быть бесплатной гарантией; код, полагавшийся на GIL как на неявный global lock,
ломается СИЛЬНЕЕ и требует переаудита. Состояние на 2026-07-14 (PEP 779, verified): free-threaded
CPython в 3.14 — **«officially supported, но НЕ default»** (в 3.13 был «experimental»); полный default
(Phase III) — не ранее 2028+ (см. `references/web-verification-2026-07-14.md`). Decay-риск как ТИП
остаётся: следующая ревизия обязана сверить снова (PEP 703/779 — живой процесс).

**Conformance.**
- Перед тем как назвать операцию «безопасной под GIL», явно проверено: это ОДНА встроенная операция
  или последовательность из ≥2.
- Составные операции над разделяемым состоянием — под явным локом вокруг ВСЕЙ последовательности, не
  вокруг отдельного присваивания.
- Claim «GIL защищает» помечен как специфичный для GIL-сборки CPython, не как гарантия языка Python
  (B5, Strict Distinction реализация vs спецификация) — не переносится на PyPy/free-threaded без
  переверификации.

**Связи [E.4.PFR].**
- **composition** с Паттерном 6 (та же false-atomicity-ассумпция — корень D1).
- **conflict** с «GIL = бесплатный мьютекс».
- **scope-dependent**: истинно только для GIL-сборки CPython (эталонная реализация), не для
  PyPy/Jython/GraalPy/free-threaded build без переверификации.

---

### Паттерн 3: Deadlock ⟺ 4 условия Коффмана — снять любое одно, обычно total lock order

**Recognition** — код держит ≥2 лока одновременно (включая reentrant-захват одного и того же
нерекурсивного лока тем же потоком) или комбинирует лок с ожиданием другого потока (`join`).

**Принцип (SoTA-grounded).**
Deadlock возникает тогда и только тогда, когда одновременно выполнены 4 условия: mutual exclusion,
hold-and-wait, no preemption, circular wait (Coffman, Elphick, Shoshani, *System Deadlocks*, ACM
Computing Surveys, 1971, S2). Достаточно нарушить ЛЮБОЕ одно — чаще всего вводят total order на захват
локов, структурно убирая circular wait (A2).

**Наша инстанциация (worked slice).**
`DrainGuard.start_drain()` (`__init__.py:372-396`) использует ДВА лока (`_drain_cond` с внутренним
`cond_lock`, и отдельный `_drain_check_lock`) с явно закомментированным порядком операций: «That's mean
`self._drain_is_active_by = ...` operation should be ALWAYS last in this function to prevent race
condition» — порядок захвата и порядок присваивания внутри лока задокументирован намеренно, не
случайно. `finish_drain()`/`wait_drain_finished()` содержат явный assert против self-deadlock
(«You can not wait your own; deadlock detected», `__init__.py:425`) — структурная проверка ОДНОГО из
4 условий (circular wait между потоком и самим собой) вместо надежды, что «на практике не случится».

**Контрпример [A.11 Sharp Boundary].**
«У нас один лок вокруг сокета — circular wait с одним локом невозможен, дисциплина порядка не нужна» —
неверно по двум причинам: (а) reentrancy — тот же поток повторно берёт нерекурсивный `Lock` →
self-deadlock БЕЗ circular wait между потоками (решение — `RLock`, как и выбрано в
`ThreadSafeConnection`, не порядок захвата); (б) «один лок сегодня» не гарантирует «один лок навсегда»
— в этом же bounded context уже два: `_transport_lock` и `DrainGuard`-локи.

**Анти-паттерн [E.8].**
Deadlock «решён» добавлением `acquire(timeout=…)` + retry — timeout убирает no-preemption ценой
прогресса (вероятностное смягчение), но заменяет deadlock на livelock/starvation (два потока
бесконечно берут-отпускают-ретраят), а не устраняет структурно. Silent fusion «total order = timeout»
недопустим — это разные гарантии (structural vs probabilistic).

**Conformance.**
- При ≥2 локах — явный документированный порядок захвата (total lock order) ИЛИ обоснование, почему
  порядок не нужен (locks не пересекаются по времени жизни ни в одном потоке).
- Reentrancy — `RLock`, не голый `acquire()` того же лока тем же потоком.
- Timeout+retry не выдаётся за решение deadlock без явной оговорки «это смягчение до livelock, не
  структурное устранение».

**Связи [E.4.PFR].**
- **scope-dependent**: активен при ≥2 локах или reentrancy; не применим к чисто lock-free/
  ownership-transfer дизайну (там deadlock невозможен by construction, но появляется livelock/ABA).
- **conflict** с «один лок → расслабься» и с «timeout = решение deadlock».
- **composes** с Паттерном 5 (ownership-transfer убирает mutual exclusion как класс).

---

### Паттерн 4: Guarded Suspension — `cond.wait()` обязан быть в `while`, перепроверяющем предикат

**Recognition** — код ожидает предикат на `threading.Condition` через `if predicate: cond.wait()`
(единичная проверка) вместо цикла.

**Принцип (SoTA-grounded).**
Monitor (Hoare, *"Monitors: An Operating System Structuring Concept"*, CACM, 1974, S3) — condition
variable сама по себе не хранит состояние и не гарантирует, что предикат, разбудивший ожидающего,
всё ещё истинен к моменту получения лока обратно. Guarded Suspension (Goetz et al., *Java Concurrency
in Practice*, 2006, гл.14, S14): ожидание — ОБЯЗАНО быть в цикле `while not predicate(): cond.wait()`,
не в `if`, по двум независимым причинам — spurious wakeup И «настоящий» notify мог относиться не к
этому ожидающему (несколько ждущих на разные предикаты, `notify_all` будит всех).

**Наша инстанциация (worked slice).**
`DrainGuard.wait_drain_finished()` (`__init__.py:410-436`): `with self._drain_cond: if
self.is_drain_active(): self._drain_cond.wait(timeout=timeout)` — единственная проверка предиката
работает корректно НЕ вопреки Тезису 4, а благодаря структурной гарантии, задокументированной рядом:
`finish_drain()` — единственное место, снимающее `_drain_is_active_by`, делает это ПОД ТЕМ ЖЕ локом
(`with self._drain_cond:`) и сразу вызывает `notify_all()` (`__init__.py:404-408`) — предикат не может
«снова стать ложным» между notify и повторным захватом лока, потому что дренаж — не FIFO-очередь с
несколькими независимыми предикатами, а single-active-drain инвариант с одним writer'ом за раз под
локом. Это НЕ отменяет общий принцип «`while` — минимальная корректная форма для произвольного
предиката» — это документированный частный случай, где предикат монотонен и меняется только под тем
же локом, что и его проверка (см. контрпример ниже — где такая структурная гарантия ОТСУТСТВУЕТ).

**Контрпример [A.11 Sharp Boundary].**
«Python `threading.Condition` не даёт spurious wakeup — значит `if` достаточно» — бьёт только по одной
из двух причин требования `while`. Для ЛЮБОГО condition variable с НЕСКОЛЬКИМИ ждущими на разные
предикаты и `notify_all()`, будящим всех разом, вторая причина («настоящий» notify не обязательно
относится к этому ждущему) требует повторной проверки — `if` там ошибочен структурно, а не только
теоретически. Граница отличия от инстанциации выше: single-active-drain с одним предикатом и
единственным writer'ом под тем же локом — это НЕ общий случай, переносить «`if` достаточно» на
condition variable с множественными ждущими/предикатами нельзя.

**Анти-паттерн [E.8].**
«Проще заменить `Condition` на `queue.Queue` — там while-предикат уже внутри» — часто верно (Паттерн 5),
но `Queue` решает только «ждать элемент FIFO»; не покрывает произвольный/составной предикат (например
«соединение восстановлено И буфер дренирован» — предикат `DrainGuard`). Подмена `Condition`→`Queue`
сужает выразительность для непокрываемых случаев, не универсальная замена.

**Conformance.**
- Ожидание ПРОИЗВОЛЬНОГО предиката на `Condition` — в `while`, если нет структурной гарантии
  единственности writer'а под тем же локом (как в `DrainGuard`); такая гарантия — явно
  задокументированный частный случай, не умолчание по умолчанию.
- `notify_all()` с несколькими ждущими на разные предикаты — всегда `while` без исключений.
- Ручная одноразовая перепроверка после `if` НЕ эквивалентна `while` (A.11: нельзя корректно вычесть
  цикл, развернув его в одну строку).

**Связи [E.4.PFR].**
- **composition** с claim A3 (Hoare monitor: condition variable не хранит состояние → re-check).
- **conflict** с «`if` достаточно».
- **scope-dependent**: только для произвольного предиката без структурной гарантии single-writer;
  не нужен там, где примитив сам инкапсулирует ожидание (`queue.Queue.get`, одноразовый `Event.wait`).

---

### Паттерн 5: Thread confinement / ownership transfer — дешевле, чем shared-state + lock везде

**Recognition** — состояние делимо на части, каждой из которых естественно владеет ровно один поток в
любой момент времени (в противовес неделимому единому ресурсу — одному fd сокета).

**Принцип (SoTA-grounded).**
Самый дешёвый способ избежать гонки — не делить mutable-объект, а передавать его владение ЦЕЛИКОМ
через уже потокобезопасную точку передачи (thread-safe очередь), так что в любой момент им владеет
ровно один поток. Синхронизационная поверхность сжимается до ОДНОЙ точки (put/get) вместо N залоченных
обращений (Goetz et al., *JCiP*, 2006, гл.3 "Sharing Objects", S14; Buschmann et al., POSA2, 2000, S13).

**Наша инстанциация (worked slice).**
`channel_thread_bindings: collections.defaultdict[int, set[int]]` (`__init__.py:555`) — явная
таблица «какой поток владеет каким channel_id», не shared dict-без-владельца. `ThreadSafeChannel.wait()`
(`__init__.py:138-145`): `if thread_ident != self._owner_ident: self.change_owner(thread_ident)` —
владение явно ПЕРЕДАЁТСЯ (не разделяется молча) при обнаружении вызова из другого потока (комментарий:
«workaround for case when channel used in another thread, e.g. through ChannelPool»). `change_owner()`
(`__init__.py:127-136`) — атомарный (под capture исходного `prev_owner`) переход `discard`/`add` в двух
множествах `bindings`, границей передачи владения выступает сама операция смены записи в таблице, не
захват лока на каждое обращение к каналу.

**Контрпример [A.11 Sharp Boundary].**
Rust/Go ownership vs Python confinement (граница Паттерна 5): «передал владение — трогать нельзя»
выглядит как Rust move / Go «share memory by communicating», но Python НЕ форсит — объект после
передачи физически доступен предыдущему владельцу, компилятор не запретит мутацию. Граница: в Rust
ownership enforced типами (borrow-checker); в Python — конвенция, держится ревью/линтом/тестом, не
языком. `change_owner()` меняет ЗАПИСЬ о владении, но не отбирает физический доступ у предыдущего
потока — дисциплина, не гарантия рантайма.

**Анти-паттерн [E.8].**
«В нашем bounded context сокет физически один, все потоки пишут в один fd — confinement неприменим в
принципе» — ложная дихотомия «всё или ничего»: confinement применяется НЕ к сокету, а к буферам
кадров/каналам (каждый — одному потоку-владельцу по таблице `channel_thread_bindings`), а к границе
самого сокета — отдельный лок (`_transport_lock`, Half-Sync/Half-Async, C5: I/O-слой сериализован,
обработка confined).

**Conformance.**
- Состояние явно разбито на confined-часть (одно владение, таблица/конвенция передачи) и shared-часть
  (единый ресурс под локом) — «неприменим целиком» не принимается как обоснование пропустить
  confinement там, где состояние делимо.
- Передача владения — через явную операцию (put/get, `change_owner()`), не через «просто перестали
  трогать по молчаливой договорённости».
- Отсутствие compiler-enforcement в Python — повод завести тест/линт на «предыдущий владелец не трогает
  после передачи», не повод отказаться от паттерна.

**Связи [E.4.PFR].**
- **composition** с C5 Half-Sync/Half-Async (confined обработка за queueing-границей) и с Паттерном 3
  (убирает mutual exclusion как класс → deadlock невозможен для confined части).
- **conflict** с «share memory + lock везде».
- **scope-dependent**: применим когда состояние делимо на владеемые-одним-потоком части; НЕ применим
  к неразделимому единому ресурсу (сериализация локом, Паттерн 2/3).

---

### Паттерн 6 (центральный, ИИ-специфичный): Ревью по инварианту, не по наличию лока — LLM воспроизводит те же допущения чаще

**Recognition** — код-ревью (человеческого ИЛИ LLM-сгенерированного) многопоточного участка; момент
принятия решения «этот код потокобезопасен» на основании присутствия `Lock`/`Condition`/`Queue`.

**Принцип (SoTA-grounded).**
Эмпирически доминируют atomicity violation и order violation (Lu, Park, Seo, Zhou, ASPLOS 2008, S17,
D1); корень — не «забыл поставить лок», а неверное ментальное допущение об инварианте (D2). Ревью
эффективнее, когда проговаривает «какой инвариант это защищает», а не только «здесь стоит лок». LLM
генерирует синтаксически-корректный конкурентный код, но статистически чаще ошибается в тонком (if-vs-
while, exception-safety лока, compound-atomicity, ленивая инициализация без лока), потому что обобщает
по поверхностному сходству кода, а не по инварианту (**AI2, явно `hypothesis`**, усилена пересечением
с D1/D2 `fact`); для pure Python нет TSan-эквивалента (Serebryany & Iskhodzhanov, WBIA 2009, S19, D4) —
ИИ ускоряет производство кода, который нужно проверять тем же чек-листом, гэп тулинга не закрывает.

**Наша инстанциация (worked slice).**
Комментарии-инварианты в `__init__.py` документируют ИМЕННО то, что должно проверяться ревью, не
наличие лока: `finish_drain()` — «You can not finish drain started by other thread» (какой инвариант
нарушится, если снять чужой дренаж); `start_drain()` — развёрнутый комментарий про порядок операций
внутри лока («это должно быть последним, чтобы не race»); `_basic_publish()` — «a concurrent teardown
can null self.connection mid-publish, and the resulting AttributeError is not retried by kombu» —
называет КОНКРЕТНЫЙ инвариант (снимок `conn` должен быть взят под локом ДО обнуления), а не просто
«здесь лок». Это прямая инстанциация D2: ревьюер, читающий такой комментарий, проверяет инвариант, а
не факт присутствия `with lock:`.

**Контрпример [A.11 Sharp Boundary].**
«Прогнал у модели 3 раза / спросил 3 модели — согласовано, значит корректно» для конкурентного кода —
НЕ применимо: согласие проходов модели evidence не считается (у гонки нет наблюдаемого краша на
большинстве прогонов — редкость воспроизведения маскирует баг, не подтверждает отсутствие). Граница:
self-consensus заменяет НЕЗАВИСИМЫЙ метод (чек-лист инвариантов, рассуждение о happens-before), только
если баг детерминирован — для конкурентности это условие обычно ложно.

**Анти-паттерн [E.8].**
«Раз корень — неверное допущение, а не отсутствие лока, то лок ВЕЗДЕ ("на всякий случай") безопасно
решает проблему» — over-locking даёт свой failure mode (deadlock, Паттерн 3; lock convoy, B2) и
МАСКИРУЕТ order violation (лок вокруг ресурса не создаёт отсутствующую happens-before связь, D1).
Лишний лок = ложное чувство защиты + не документирует инвариант, который D2 требует называть явно.

**Conformance.**
- Ревью конкурентного кода явно называет инвариант, который защищает каждый лок/condition/очередь —
  не только фиксирует его присутствие.
- Целевой чек-лист для LLM-сгенерированного кода: if-vs-while (Паттерн 4), exception-safety лока
  (`with`/`try-finally`, никогда голый `acquire()`), compound-operation atomicity (Паттерн 2), TOCTOU
  (Паттерн 1) — вместо общего «код выглядит разумно».
- AI2 не цитируется как измеренный факт без оговорки `hypothesis`; чек-лист обоснован ПЕРЕСЕЧЕНИЕМ
  AI2 и D1/D2, не одной AI2.

**Связи [E.4.PFR].**
- **composition** с Паттерном 2 (та же false-atomicity-ассумпция) и Паттерном 1 (order violation =
  race без общего лока).
- **conflict** с «лок везде = безопасно» и «LLM закроет гэп тулинга сам».
- **requires** refresh-триггеры G.11 (AI-claims и статус тулинга decay-чувствительны, §11).

---

### Паттерн 7: Видимость памяти за пределами GIL — двойная проверка без лока требует переанализа под free-threaded

**Recognition** — код читает разделяемый атрибут БЕЗ лока как быстрый путь перед взятием лока
(double-checked-locking idiom: `if self._x is None: with lock: if self._x is None: self._x = create()`),
либо иначе полагается на то, что «раз GIL сериализует байткод, внешнее чтение безопасно».

**Принцип (SoTA-grounded).**
Double-checked locking сломан в языках с формальной memory model без явного `volatile`/happens-before
(Bacon et al., JavaOne declaration, ~2001, S16 — уже адаптирован типовой ошибкой 8 этого DPF: механизм
не переносится 1:1 на CPython, т.к. у CPython нет JMM, есть GIL, B5). **Официальное** подтверждение
той же категории риска для CPython самого по себе (не по аналогии с Java) даёт Python Free-Threading
Guide («Porting Python Packages»,
py-free-threading.github.io, verified 2026-07-14): «situations where the GIL _was_ providing safety
will need new analysis to ensure they are safe under free-threaded Python» и явная рекомендация
«readers should atomically copy the shared reference to a local variable and then only access the
local variable» — вместо повторного чтения shared-атрибута вне лока. Официальные thread-safety
guarantees (docs.python.org/3/library/threadsafety.html, verified 2026-07-14) сами приводят
check-then-act (`if key in d: del d[key]`) как явно **NOT atomic** под free-threaded — прямое
подтверждение A4/TOCTOU (Паттерн 1) от первоисточника языка, не только от security-литературы.

**Наша инстанциация (worked slice).**
`ThreadSafeConnection.transport` (`__init__.py:907-913`): `if self._transport is None: with
self._transport_lock: if self._transport is None: self._transport = self.create_transport()` —
классический double-checked-locking. Под GIL-сборкой это безопасно ровно в границах Паттерна 2
conformance (GIL сериализует bytecode, присваивание атрибута — атомарная встроенная операция,
внешнее чтение `self._transport is None` не может застать «частично созданный» объект). Тот же
паттерн повторён в `default_channel` (`__init__.py:948-970`): `channel = self._default_channel; if
channel is None or not channel.is_usable(): with self._transport_lock: ...` — ДВА места одного файла
разделяют одну структуру, оба — кандидаты для будущего переаудита под free-threaded (сам
переаудит НЕ выполнен — источники подтверждают КЛАСС риска и дают conformance-критерий,
но построчный аудит `__init__.py` на предмет всех double-checked-locking мест — отдельный, не
выполненный шаг, честно не приписан).

**Контрпример [A.11 Sharp Boundary].**
Это НЕ то же самое, что «GIL защищает составную операцию» (Паттерн 2) — там речь о НЕСКОЛЬКИХ
read-modify-write шагах над контейнером (`x += 1`); здесь риск ИНОЙ: одна attribute-запись атомарна
и под GIL, и (предположительно) под free-threaded per-object locking — но официальная free-threading
документация explicitly покрывает только built-in `dict`/`list`/`set` (docs.python.org/3/library/
threadsafety.html: «This page documents thread-safety guarantees for **built-in types**»), НЕ атрибуты
пользовательских объектов. Граница проверенного здесь ИМЕННО в этом: атомарность самой записи
правдоподобна, но НЕ officially документирована для произвольных `self.attr = value`, и port-гайд
советует не полагаться на «раньше было безопасно под GIL» без переанализа.

**Анти-паттерн [E.8].**
«Если запись атрибута — одна bytecode-операция, значит double-checked locking безопасен и под
free-threaded» — непроверенное расширение: официальный порт-гайд явно советует НЕ читать
shared-состояние вне лока и копировать ссылку в локальную переменную ПЕРЕД использованием именно
потому, что «GIL-was-providing-safety»-кейсы требуют переанализа. Самоуверенность «раз работало под
GIL, будет работать и без него» — та же ошибка, от которой уже предостерегает анти-паттерн Паттерна 2,
но здесь она собрана как worked-instance с конкретным `if x is None: with lock: if x is None` в коде,
а не абстрактно.

**Conformance.**
- Double-checked-locking-подобный код (`if attr is None: with lock: if attr is None: attr = create()`)
  явно помечен как GIL-специфичный паттерн (аналогично Паттерну 2 conformance) — не переносится на
  free-threaded без переверификации.
- При переаудите под free-threaded — либо снять внешнюю проверку (взять лок безусловно, если
  стоимость приемлема), либо явно задокументировать, почему предполагаемая atomic-write гарантия для
  пользовательского атрибута (недокументированная официально) в конкретном случае достаточна.
- Источник для conformance-проверки при следующей ревизии — `docs.python.org/3/library/
  threadsafety.html` + `py-free-threading.github.io/porting/` (живые, версионируемые документы), не
  pretrain recall.

**Связи [E.4.PFR].**
- **composes** с Паттерном 2 (та же GIL-specific atomicity ассумпция, другая грань — attribute read
  вне лока, не составная container-операция).
- **composes** с Паттерном 1 (TOCTOU/check-then-act — free-threading docs подтверждают ИМЕННО этот
  класс явно, независимо от security-происхождения термина).
- **requires** refresh-триггер B4/free-threaded (§11) — Паттерн 7 decay-чувствителен той же природы,
  что и Паттерн 2 анти-паттерн (Phase III default — горизонт 2028+, см. web-verification).

---

## 5. Связи паттернов (E.4.PFR)

| Паттерн | П1 Классификация | П2 GIL-граница | П3 Deadlock | П4 Guarded Suspension | П5 Confinement | П6 Ревью-по-инварианту | П7 Видимость памяти |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **П1 Классификация** | — | scope-dependent (разные слои гонки) | — | — | — | composes (order violation = частный случай D1/D2) | composes (TOCTOU-класс инстанциируется в П7) |
| **П2 GIL-граница** | — | — | — | — | — | composes (false-atomicity-ассумпция) | composes (та же ассумпция, грань attribute vs container) |
| **П3 Deadlock** | — | — | — | conflict-по-направлению (structural vs probabilistic timeout) | composes (confinement убирает mutual exclusion) | — | — |
| **П4 Guarded Suspension** | — | — | conflict (не тот же conflict, что П3×timeout) | — | scope-dependent (Queue как более узкий частный случай) | — | — |
| **П5 Confinement** | — | — | composes | scope-dependent | — | — | — |
| **П6 Ревью-по-инварианту** | composes | composes | — | — | — | — | scope-dependent (чек-лист П6 обязан включать П7 при переаудите free-threaded) |
| **П7 Видимость памяти** | composes | composes | — | — | — | scope-dependent | — |

**Sequence:** П1 (классифицировать класс гонки) → П2/П3/П4/П5 (выбрать структурную меру под класс:
атомарность/порядок захвата/guarded wait/ownership transfer) → П6 (ревьюить результат по инварианту,
не по наличию примитива; ИИ-специфика усиливает приоритет, не заменяет основание). П7 — ортогональная
проверка, активная именно при переаудите под free-threaded (не заменяет П1–П6, добавляется поверх них
при смене режима GIL/free-threaded).

**Conflict:** П3 × «timeout как решение deadlock» (structural total-order vs probabilistic
smoothing) — разрешается НЕ слиянием гарантий, а явной пометкой timeout как смягчения, не устранения
(F-4). П4 × «if достаточно» — разрешается структурной проверкой единственности writer'а под тем же
локом (см. инстанциация Паттерна 4), не общим допущением «Python Condition не даёт spurious wakeup».

---

## 6. Типовые ошибки (E.4.DPF:8)

> Полный bridge-анализ (симптом + источник) — `references/theses-antitheses.md` §4 (11 ошибок).
> Новичковые и ошибки опытных из устаревшей/локальной практики — вместе; ИИ-специфичные помечены.

| # | Симптом | Почему происходит | Исправление | Источник |
|---|---------|--------------------|--------------|----------|
| 1 | «Использую dict/list — потокобезопасно»: составная операция (`d[k]=d[k]+1`, `if k in d: del d[k]`) без лока | Путают атомарность ОДНОЙ встроенной операции (GIL, B3) с атомарностью последовательности | Лок вокруг всей read-modify-write секции; атомарный примитив — с пониманием его границ (контрпример 3 Паттерна 1) | B1/B3 Beazley & Jones, *Python Cookbook* 3rd, 2013; D1 Lu et al. ASPLOS 2008 |
| 2 | `if` вместо `while` вокруг `cond.wait()` | Допущение «проснулся → предикат истинен»; игнор spurious wakeup И notify-не-тому | `while not predicate(): cond.wait()` — если нет структурной гарантии single-writer под тем же локом (см. Паттерн 4 инстанциация) | A3 Hoare CACM 1974; C2 Goetz et al. *JCiP* 2006, гл.14 |
| 3 (ИИ) | LLM выдаёт синтаксически корректный `Lock`/`Condition`/`Queue`-код, но ошибается в тонком (if-vs-while, exception-safety, compound-atomicity, ленивая init) | LLM обобщает по поверхностному сходству сниппета, не по инварианту; обучающие данные смещены к однопоточным туториалам | Целевой чек-лист (Паттерн 6) вместо «код выглядит разумно» | AI2/AI4 (`hypothesis`, усилен D1/D2 `fact`); Pearce et al. IEEE S&P 2021/22 |
| 4 | Забытое снятие лока на exception-пути (голый `acquire` без `try/finally`) | Ручной acquire/release без RAII; исключение между ними → лок навсегда занят → deadlock всех ждущих | Всегда `with lock:`; никогда голый `acquire()` без `finally` | C1 Monitor Object (POSA2 2000) |
| 5 | Ленивая инициализация `if x is None: x = create()` без лока | TOCTOU/check-then-act (A4) в duck-typed виде — оба потока проходят проверку и оба создают | Лок вокруг проверки+создания; либо инициализация в конструкторе/один раз (confinement, Паттерн 5) | A4 (Bishop & Dilger 1996, verified 2026-07-14); D1; AI2 |
| 6 | «Уменьшил switchinterval, тест прошёл 1000 раз → гонки нет» | Случайный stress-test плохо ловит редкий интерливинг (D3); отсутствие наблюдения принято за отсутствие бага | Систематическое рассуждение по чек-листу инвариантов (D2) как основа; stress — дополнение, не доказательство; TSan для pure Python нет (D4; верно для GIL-сборки, для free-threaded TSan-инструментированные интерпретаторы существуют и используются CPython CI, см. §11/web-verification) | D3 Musuvathi et al. CHESS ~2007-08; D4 Serebryany & Iskhodzhanov WBIA 2009 |
| 7 | Deadlock «решён» добавлением `acquire(timeout=…)` + retry | Timeout убирает no-preemption, но заменяет deadlock на livelock/starvation, не устраняет структурно | Total lock ordering там, где ≥2 лока (Паттерн 3); timeout — смягчение, не решение | A2 Coffman, Elphick, Shoshani, ACM Comp. Surveys 1971 |
| 8 | Перенос «double-checked locking сломан» как актуальной угрозы reordering в CPython | Silent fusion Java memory model и CPython (у которого её нет, B5) — category error | Различать: в CPython риск иной («неверифицированная оптимизация»), не visibility reordering; переносить урок, не механизм | C4 Bacon et al. ~2001; B5; A.1.1 no silent fusion |
| 9 (ИИ) | «Прогнал у модели 3 раза / спросил 3 модели — согласовано, значит корректно» для конкурентного кода | Self-agreement: согласие проходов принято за верификацию; у гонки нет наблюдаемого краша на большинстве прогонов | Согласие модели ≠ evidence; нужен независимый метод (чек-лист инвариантов, happens-before), не консенсус проходов | AI-срез (S21, `hypothesis`) |
| 10 (ИИ) | «GIL всё сериализует» без учёта free-threaded/PyPy | Инвариант РЕАЛИЗАЦИИ принят за контракт языка (B5); decay: PEP 703 меняет базу | Различать «поведение CPython сейчас» vs «гарантия языка Python»; переаудит под free-threaded (B4, Паттерн 7) | B4 PEP 703 (Gross) 2023, PEP 779 (verified 2026-07-14: 3.14 officially supported non-default, default не ранее 2028+); B5 |
| 11 | Over-locking «на всякий случай» — лок вокруг всего | «Больше локов = безопаснее»; маскирует order violation (лок не создаёт happens-before) и плодит deadlock/convoy | Локать по ИНВАРИАНТУ, не по страху; order violation лечится синхронизацией порядка (`Event`/`join`/`Condition`), не локом вокруг ресурса | D1/D2; B2 (lock convoy) |
| 12 | Double-checked locking над атрибутом (`if self._x is None: with lock: if self._x is None: ...`) считается безопасным под free-threaded «потому что работал под GIL» | GIL-was-providing-safety случаи требуют переанализа (Паттерн 7); официальная free-threading документация покрывает только built-in dict/list/set, не пользовательские атрибуты | Копировать shared-ссылку в локальную переменную перед использованием (port-гайд); переаудит double-checked-locking мест при миграции на free-threaded (Паттерн 7) | py-free-threading.github.io/porting/, docs.python.org/3/library/threadsafety.html (verified 2026-07-14) |

---

## 7. SoTA-Echoing (E.4.DPF:11)

| # | Claim | Источник | Статус | Adoption в DPF |
|---|-------|---------|--------|----------------|
| SE-1 | Race condition ⊋ data race; разделение формально независимо от memory location | Netzer & Miller, ACM LOPLAS, 1992 (S5) | **fact** | Adopted: Паттерн 1 |
| SE-2 | 4 условия deadlock (Коффман); достаточно снять любое одно | Coffman, Elphick, Shoshani, ACM Computing Surveys, 1971 (S2) | **fact** | Adopted: Паттерн 3 |
| SE-3 | Monitor = один лок + condition variable, предикат не хранится в CV → re-check после `wait()` | Hoare, CACM, 1974 (S3) | **fact** | Adopted: Паттерн 4 |
| SE-4 | GIL атомизирует один bytecode/встроенную операцию, НЕ составную последовательность | Python core docs FAQ, docs.python.org/3/faq/library.html (S8, **verified 2026-07-14**); Beazley PyCon 2010 (S9); Beazley & Jones *Python Cookbook* 3rd (S10, book source, pretrain) | **fact** | Adopted: Паттерн 2 |
| SE-5 | Free-threaded CPython (PEP 703) отменяет «бесплатность» GIL-атомарности | Gross, PEP 703, 2023 (S11); PEP 779 (verified 2026-07-14) | **fact, verified 2026-07-14**: 3.14 — officially supported, НЕ default (PEP 779); default (Phase III) не ранее 2028+ | Adopted: Паттерн 2 (contrapример/repair-кандидат №1), Паттерн 7 |
| SE-6 | Monitor Object / Guarded Suspension / Thread confinement / Half-Sync-Half-Async — прямая онтологическая база паттернов доступа к разделяемому состоянию | Buschmann et al., POSA2, 2000 (S13); Goetz et al., *JCiP*, 2006 (S14) | **fact** | Adopted: Паттерны 3/4/5 |
| SE-7 | Double-checked locking сломан по visibility-reordering (JMM); механизм НЕ переносится 1:1 на CPython (нет formal memory model) | Bacon et al., ~2001 (S16); B5 | **fact (урок) / не-факт (буквальный перенос механизма)** | Adopted: типовая ошибка 8, контрпример 1 Паттерна 2 |
| SE-8 | Atomicity violation и order violation — два доминирующих эмпирических класса реальных concurrency-багов | Lu, Park, Seo, Zhou, *Learning from Mistakes*, ASPLOS 2008 (S17) | **fact** (категории; цифры/Python-специфика — не перенесены, BridgeMatrix явная потеря) | Adopted: Паттерн 1/6 (центральный тезис) |
| SE-9 | Систематический контроль интерливинга находит баги, которые случайный stress-test пропускает | Musuvathi, Qadeer et al., CHESS, ~2007-2008 (S18) | **fact** | Adopted: типовая ошибка 6 |
| SE-10 | Для pure Python нет TSan-эквивалента в стандартном тулинге | Serebryany & Iskhodzhanov, WBIA 2009 (S19); D4 | **fact** (про инструментарий других экосистем); для GIL-сборки CPython по-прежнему нет pure-Python-уровня детектора; для free-threaded CPython TSan-инструментированные интерпретаторы существуют и используются CPython CI (2025–2026) — C-уровневый, не pure-Python-level инструмент | Adopted: Паттерн 6, типовая ошибка 6, открытый provenance-вопрос §11 |
| SE-11 | LLM-сгенерированный код содержит заметную долю багов из классов, смежных с TOCTOU/race, при наивном промптинге | Pearce et al., IEEE S&P 2021/2022 (S20) | **fact** (эмпирика, verified 2026-07-14: атрибуция точна); цифры НЕ переносить на современные модели без переверификации | Adopted: Паттерн 6, типовая ошибка 3 |
| SE-12 | LLM статистически чаще ошибается в тонких местах конкурентного кода (if-vs-while, exception-safety, compound-atomicity, TOCTOU) | Агрегированное наблюдение сообщества (S21) | **hypothesis, явно не повышено до fact** (природа claim'а исключает единичный citable источник — не переоткрыто веб-проверкой 2026-07-14) | Adopted: Паттерн 6 (усилено пересечением с SE-8 `fact`), типовая ошибка 3/9 |
| SE-13 | GIL-was-providing-safety код (включая double-checked locking над атрибутами) требует переанализа под free-threaded; читатели должны копировать shared-ссылку в локальную переменную перед использованием | Python Free-Threading Guide, «Porting Python Packages», py-free-threading.github.io (verified 2026-07-14) | **fact** (официальный порт-гайд CPython-экосистемы) | Adopted: Паттерн 7 (принцип) |
| SE-14 | Под free-threaded `if key in d: del d[key]` (check-then-act) explicitly NOT atomic — TOCTOU-класс подтверждён официальной документацией языка, не только security-литературой | docs.python.org/3/library/threadsafety.html (verified 2026-07-14) | **fact** (первый порядок — официальная документация Python) | Adopted: Паттерн 1 (усиление A4), Паттерн 7 |

---

## 8. Имена — F.18 (CC-DPF.4)

> Кандидаты в `project/glossary.md` (проект не имеет этого файла на 2026-07-14, см. §11
> открытые provenance-вопросы source-pack) — НЕ перенесены, отдельный шаг без явного поручения.
> Источник — `references/sota-research.md` G.2c Operator/Object inventory.

| RU термин | EN (код) | Определение | Не является |
|-----------|----------|--------------|-------------|
| Гонка данных | data race | конкурентный доступ ≥2 потоков к одной memory location без синхронизации, где ≥1 доступ — запись | синоним race condition (более узкое понятие) |
| Состязание / гонка порядка | race condition | исход программы зависит от непредсказуемого порядка/тайминга операций нескольких потоков | всегда data race — включает TOCTOU/order violation без единой ячейки |
| TOCTOU (check-then-act) | time-of-check to time-of-use | между проверкой условия и действием на его основе состояние меняет другой поток | исключительно термин файловой/ФС-безопасности |
| Atomicity violation | atomicity violation | последовательность операций, которая должна была выполниться неделимо, прервана другим потоком между шагами | «забыл поставить лок» вообще (это неверное допущение об инварианте) |
| Order violation | order violation | нарушение ожидаемого порядка между операциями двух потоков без общей конкуренции за лок | data race (нет общей memory location под спором) |
| Guarded Suspension | guarded suspension | ожидание предиката на condition variable в цикле `while`, с повторной проверкой после пробуждения | однократная проверка предиката (`if`) |
| Thread confinement | thread confinement / ownership transfer | состояние принадлежит ровно одному потоку в любой момент, владение передаётся явной операцией | shared state, защищённое локом на каждое обращение |
| Total lock ordering | total lock ordering | глобальный согласованный порядок захвата ≥2 локов, структурно устраняющий circular wait | timeout-based backoff (вероятностное смягчение) |
| Lock convoy | lock convoy | деградация производительности, когда много потоков сериализуются на одном горячем локе | deadlock (иной failure mode) |
| Free-threaded CPython | free-threaded build | опциональная сборка CPython без GIL (PEP 703), где атомарность bytecode перестаёт быть бесплатной | текущий default GIL-режим CPython |

**Provisional (не фиксировать до стабилизации):** «single-active-drain инвариант» как рабочее
обозначение частного случая Паттерна 4 (DrainGuard); выбор между «guarded suspension» и русской
калькой «защищённое ожидание» — не решён здесь.

**Источник термина:** ранняя каноническая работа по TOCTOU в file-access — Bishop, M.; Dilger, M.,
*"Checking for Race Conditions in File Accesses"*, Computing Systems, 1996, pp. 131–152 (verified
2026-07-14, см. `references/web-verification-2026-07-14.md`; работа — ранняя каноническая по теме,
явная чеканка номенклатуры TOCTOU ей не приписывается); термин зародился в security-литературе, но, как
отмечает столбец «Не является» выше, этим не ограничен (Паттерн 1 conformance).

---

## 9. Relations (E.4.PFR)

| Relation | Target | Function | Note |
|----------|--------|----------|------|
| grounded_in | FPF E.4.DPF | meta | spine, CC-DPF.1–9, канон-скелет — метод сборки, `~/.claude/skills/dpf-authoring/references/method.md` |
| grounded_in | FPF G.2 | meta | SoTA harvest (CorpusLedger/ClaimSheets/MicroExamples) — Фаза 1, `references/sota-research.md` |
| grounded_in | FPF A.2.6 | meta | ClaimScope — scope-строка каждого тезиса (§4, Фаза 2) |
| grounded_in | FPF B.5.2.1 | meta | NQD≥3 — анти-тезисы каждого тезиса, `references/theses-antitheses.md` |
| grounded_in | FPF A.1.1 | meta | BoundedContext / no silent fusion — BridgeMatrix, разделение слоёв (OS/GIL/PAT/BUG/AI) |
| grounded_in | FPF A.11 | meta | Sharp Boundary — 6 контрпримеров §4/`theses-antitheses.md` §3 |
| uses | FPF A.7 | meta | Strict Distinction — реализация CPython (GIL) vs спецификация языка Python (B5) |
| uses | FPF A.10 | meta | Evidence Graph — claim без источника+даты = мнение; A4/TOCTOU помечен пограничным provenance |
| instantiates (worked-evidence) | `kombu-pyamqp-threadsafe` `src/kombu_pyamqp_threadsafe/__init__.py` | dependency | Референсная инстанциация bounded context: `ThreadSafeConnection`, `ThreadSafeChannel`, `DrainGuard`, `channel_thread_bindings` |
| peer | `DPF-DEDICATED-IO-THREAD` | peer | Соседняя компетенция в `project/frameworks/`; содержательно не смешана с этим пакетом (см. HC-3 §10) |
| coordinates_with | `references/source-pack.md` | dependency | Provenance-реестр (26 источников, реестр открытых вопросов) — не пересказан здесь дословно |
| coordinates_with | `references/critic-review.md` | dependency | Фаза 6 (2026-07-14): completeness-критика, оценка E.4.DPF.DA (D1–D11), repair-список |
| coordinates_with | `references/quality-record-2026-07-14.md` + `references/web-verification-2026-07-14.md` | dependency | Процессный след ремонта (PFM7) и полный протокол веб-верификации — не пересказаны здесь дословно |
| coordinates_with | `references/theses-antitheses.md` | dependency | Полный текст 6 тезисов × NQD≥3 анти-тезисов, BridgeMatrix — источник §4/§5/§6 этого файла |
| scope_boundary | (не существуют в проекте) `project/domain.md` / `project/decisions/` | peer | Файлы контекста проекта; не существуют на 2026-07-14 (см. `scope.md`, `source-pack.md` секция 3) — открытый вопрос §11, не решён здесь |

---

## 10. Разнородные приёмочные случаи (D8)

> 2–3 непохожих кейса за пределами мотивирующего примера (`kombu-pyamqp-threadsafe` целиком), проверяющих,
> что паттерны обязаны сработать в ДРУГОЙ форме разделяемого ресурса. Взяты из bounded context проекта
> (не новый ресёрч, A.11 Parsimony) — каждый закрывает разный узел координации внутри одного и того же
> файла, чтобы не повторять единственный мотивирующий пример дословно.

| # | Кейс | Отличие от мотивирующего примера (транспорт/дренаж целиком) | Как паттерны переносятся | Статус |
|---|------|----------------------------------------------------------------|----------------------------|--------|
| **HC-1** | **`ChannelCoordinator.begin_teardown()`** (`__init__.py:442-` — счётчик активных операций канала: enter/exit критической секции, teardown ждёт их завершения перед обнулением `self.connection`) | Не про лок вокруг состояния объекта (Паттерн 3/Monitor), а про **счётчик + drain-ожидание** — гибрид Паттерна 3 (лок на mark+count) и Паттерна 4 (ожидание условия «активных операций 0»), явно ДРУГАЯ форма координации, чем `DrainGuard` | Паттерн 1 классифицирует риск: не data race за один лок, а order violation («операция стартовала ПОСЛЕ пометки teardown» — должна быть отклонена, не проскочить). Паттерн 6 (ревью-по-инварианту): docstring класса явно называет инвариант — «Mark and count share one lock, so an operation racing teardown is reliably rejected rather than slipping in» — прямая инстанциация D2 (проговорить инвариант, не факт наличия лока) | **fact, worked-evidence present** — код прочитан (`__init__.py:442-459`, docstring процитирован дословно) |
| **HC-2** | **`_connection_dispatch_lock.acquire(blocking=False)`** (`__init__.py:649-656` — non-blocking захват с `if not acquired: return`, а не блокирующее ожидание) | НЕ Guarded Suspension (Паттерн 4 — там ждут, пока предикат станет истинным) и НЕ total lock ordering (Паттерн 3 — там ≥2 лока в фиксированном порядке): это third форма — «попробовать один раз, если занято — отступить», ближе к paттерну «single active reader, остальные не ждут, а пропускают» | Паттерн 3 инстанциируется НЕГАТИВНО как контрпример собственной инстанциации: `blocking=False` — это НЕ timeout-retry (типовая ошибка 7, «timeout решает deadlock» — здесь `False` не timeout, а немедленный отказ без ретрая внутри этой функции), значит это НЕ тот анти-паттерн, который Паттерн 3 предостерегает; отдельный случай, где non-blocking acquire — намеренный дизайн «пропустить, не ждать», не смягчение deadlock | **fact, worked-evidence present** — код прочитан (`__init__.py:649-656`) |
| **HC-3** | **Соседняя компетенция `DPF-DEDICATED-IO-THREAD`** (`project/frameworks/DPF-DEDICATED-IO-THREAD/` — на момент сборки этого файла, 2026-07-14, каталог-заготовка; НЕ прочитан как источник паттернов) | Гипотетический (НЕ worked-evidence) перенос паттернов ЭТОГО DPF на соседний домен: выделенный I/O-поток, который единолично читает сокет, а остальные потоки передают ему работу через очередь — структурно похоже на Паттерн 5 (thread confinement) в предельной форме («весь I/O confined одному потоку», не просто буферы кадров) | Паттерн 5 переносится по принципу (confinement сжимает синхронизационную поверхность), НЕ по деталям реализации `DPF-DEDICATED-IO-THREAD` (файл не прочитан, содержание не проверено — это НЕ silent fusion, это явно помеченный gap) | **principle-grounded, worked-evidence НЕ проверялось** — содержание соседнего пакета не использовано; открытый вопрос §11: при опоре на собранный `DPF-DEDICATED-IO-THREAD` потребуется отдельная проверка, не смешение содержания задним числом |
| **HC-4** | **`urllib3.PoolManager`** — race condition между получением `ConnectionPool` из LRU-кэша и его фактическим использованием ([`urllib3/urllib3#1252`](https://github.com/urllib3/urllib3/issues/1252), verified WebFetch 2026-07-14) | **ДРУГОЙ проект, другой домен, другой авторский коллектив** (HTTP-транспорт, не AMQP/kombu) — впервые worked-evidence ЭТОГО DPF выходит за пределы `kombu-pyamqp-threadsafe`. Форма координации — LRU-кэш connection pool'ов, а не лок/condition/ownership-таблица | Паттерн 1 классифицирует риск напрямую: пул получен из кэша («check»), между этим и `pool._get_conn()` («act») другой поток может вытеснить именно этот pool из LRU — ровно TOCTOU/check-then-act (A4), не data race за одну ячейку; структурно идентично классу, который Паттерн 1 conformance требует распознавать «и вне ФС» — здесь это не файловая система, а in-memory кэш, третье независимое подтверждение, что TOCTOU не ограничен security/ФС-контекстом | **fact, worked-evidence present, ДРУГОЙ проект** — issue прочитан WebFetch 2026-07-14, `references/web-verification-2026-07-14.md` |

**Денора отбора этих четырёх кейсов:** HC-1 и HC-2 — реальный код того же файла, но структурно ДРУГАЯ
форма координации, чем мотивирующий пример (`DrainGuard`), проверяющая, что классификация (Паттерн 1)
и ревью-по-инварианту (Паттерн 6) работают не только на «главном» примере; HC-3 — явно помеченный
случай на грани applicability (соседняя компетенция, содержание которой НЕ проверено), чтобы не
скрывать честно, где worked-evidence кончается и начинается principle-grounded экстраполяция (A.10);
**HC-4** — единственный кейс вне `kombu-pyamqp-threadsafe`: без него вся worked-evidence и
все 3 кейса были бы из одного файла одного проекта, что
подрывало бы заявленную в §1 применимость «любой похожий домен: пул соединений, кэш, буфер очереди» —
HC-4 инстанциирует именно «пул соединений» из формулировки §1, но в СТОРОННЕМ, независимо
поддерживаемом проекте, не в `kombu-pyamqp-threadsafe`.

---

## 11. Quality & Refresh (E.4.DPF.DA, CC-DPF.7)

**Что оценивается:** прошли ли Фазы 0–5 (да); ≥3 традиции (выполнено: 4 + ИИ-срез); принцип→
инстанциация в каждом из 7 паттернов (все прошли); контрпримеры/анти-паттерны/связи (§4/§5/§6);
пакет целиком — по E.4.DPF.DA (11 координат, не средний балл паттернов). Оценка адекватности пакета —
`references/critic-review*.md`; процессный след правок — `references/quality-record-2026-07-14.md`.

**Статус пакета (CC-DPFDA.8):** `maturity: "conformant"` во frontmatter — пакет прошёл независимую
оценку критика по E.4.DPF.DA (`references/critic-review-2026-07-14-r3.md`, статус
`admissibleForDeclaredDPFUse`, все 11 координат ≥ пола 4). Опорный свод (7 паттернов, полный скелет,
worked-evidence из реального кода, в том числе из независимого стороннего проекта — HC-4); статус не
самозаявлен — вынесен guardian, отдельным от сборки агентом (role-separation, DEC-003).
Часть decay-чувствительных claim'ов (A4, B4/S11, S19/D4, AI-срез, S8) веб-верифицирована 2026-07-14,
см. `references/web-verification-2026-07-14.md`; остаток (S1/S4/S7/S10/S12/S15) —
`pretrain recall, не верифицирован`, без апгрейда без evidence.

**Refresh triggers (G.11):**
- **B4/PEP 703 decay:** verified 2026-07-14 — 3.14 officially supported non-default (PEP 779);
  default (Phase III) не ранее 2028+. Триггер остаётся живым: следующая ревизия обязана сверить снова
  (PEP 703/779 — активный процесс, не застывший факт).
- **AI1/AI2:** атрибуция S20 verified 2026-07-14; перенос цифр на современные модели НЕ
  выполнен (research-gap не закрыт эмпирически, только атрибуция подтверждена) — нужно свежее
  эмпирическое сравнение LLM-сгенерированного конкурентного Python-кода на актуальных моделях.
- **A4/TOCTOU provenance:** привязан к Bishop & Dilger, 1996 (verified 2026-07-14).
- **S19/D4 «для pure Python нет TSan-эквивалента»:** верно для GIL-сборки; для
  free-threaded TSan-инструментированные интерпретаторы существуют (см. §7 SE-10).
- **S8 (GIL-atomicity, Python core docs):** verified 2026-07-14 — `docs.python.org/3/faq/library.html#
  what-kinds-of-global-value-mutation-are-thread-safe` подтверждает точный список атомарных/неатомарных
  операций, используемый Паттерном 2/SE-4. S10 (Python Cookbook 3rd, книга) остаётся pretrain — глава
  подтверждена по оглавлению, полный текст не веб-сверяем без доступа к книге.
- **Триггер Паттерна 7:** построчный аудит `__init__.py` на предмет ВСЕХ
  double-checked-locking мест (найдено минимум 2: `transport`, `default_channel`) под free-threaded —
  НЕ выполнен, кандидат для architect при реальной миграции проекта на free-threaded.
- Появление `project/domain.md`/`project/decisions/`/`project/frameworks/competency-map.md` — при
  создании этих файлов пересмотреть §1/§9 (сейчас Relations честно отмечает их отсутствие, не
  додумывает содержание).
- Сборка `DPF-DEDICATED-IO-THREAD` (соседний каталог, сейчас пустой) — пересмотреть HC-3 §10 на
  worked-evidence вместо principle-grounded экстраполяции.
- Изменение `method.md`/`fpf_edition` (родительский канон) — пересмотреть PFM-ссылки этого файла.
- FPF-Spec меняет E.4.DPF/G.2/E.4.PFR/A.2.6/B.5.2.1/A.11 → пересмотреть весь файл.
- `review_due`: 2026-09-29.

**Open assumptions / provenance-вопросы (реестр — `source-pack.md`; состояние на 2026-07-14):**
1. B4/PEP 703 decay-риск (S11): 3.14 officially supported non-default (PEP 779, verified 2026-07-14);
   decay-риск как ТИП остаётся (следующая ревизия сверяет снова).
2. AI1/AI2 (S20/S21) — перенос эмпирики 2021–2022 на современные LLM НЕ измерен (S20 атрибуция
   verified 2026-07-14; эмпирического повторения на новых моделях нет).
3. A4 (TOCTOU): привязан к Bishop & Dilger, 1996, "Checking for Race Conditions in File Accesses",
   Computing Systems, pp. 131–152 (verified 2026-07-14).
4. S19/D4: верно для GIL-сборки; free-threaded TSan-инструментированные сборки существуют и
   используются CPython CI (см. §7 SE-10, Паттерн 7).
5. Полное отсутствие `domain.md`/`decisions/` в проекте — открытый вопрос, адресован
   facilitator/architect.
6. Покрытие веб-верификации: приоритетные якоря A4/B4/S19/AI-срез + S8 + 10 научных первоисточников
   verified 2026-07-14 (`references/web-verification-2026-07-14.md`); S1/S4/S7/S10/S12/S15 остаются
   pretrain-only.

---

## Артефакты каталога (references/ · assets/)

- [`references/scope.md`](references/scope.md) — Фаза 0: bounded context, intended reader, first use,
  non-use boundary, честно зафиксированный гэп отсутствующих project-контекстных файлов.
- [`references/sota-research.md`](references/sota-research.md) — Фаза 1: G.2a CorpusLedger (21
  источник), G.2b ClaimSheets (A1–A5, B1–B5, C1–C5, D1–D4, AI1–AI4), G.2e MicroExamples (ME1–ME5),
  G.2c Operator/Object inventory.
- [`references/theses-antitheses.md`](references/theses-antitheses.md) — Фаза 2: BridgeMatrix
  (alignment/divergence 5 линий), 6 тезисов (scope + NQD≥3 анти-тезис + тип связи), 6 контрпримеров
  (A.11), 11 типовых ошибок, gate-проверка Фазы 2.
- [`references/source-pack.md`](references/source-pack.md) — Фаза 3: реестр provenance (21 источник
  pretrain + 5 источников S22–S26 verified 2026-07-14 = 26), retired premises (ноль, обоснованно),
  реестр открытых provenance-вопросов.
- `assets/` — (TBD) чек-лист-карточка Паттерна 6 (AI-review checklist) для быстрой самопроверки при
  ревью LLM-сгенерированного конкурентного кода.
- [`references/critic-review.md`](references/critic-review.md) и `references/critic-review-2026-07-14-r*.md`
  — Фаза 6: completeness-критика, PFM1–11, координаты D1–D11, статусы пакета по итерациям, repair-списки.
- [`references/quality-record-2026-07-14.md`](references/quality-record-2026-07-14.md) — процессное
  состояние ремонтов (PFM7): вынесенный дословно run-narrative, ход правок по кругам, границы каждого
  ремонта.
- [`references/web-verification-2026-07-14.md`](references/web-verification-2026-07-14.md) — полный
  протокол веб-верификации ремонта (claim → источник+URL+дата → вердикт → что изменено).

---

## Carrier note (CC-DPF.5)

Все pretrain-источники (S1–S21) в этом пакете несут trust-cue «pretrain recall, не верифицирован» —
унаследовано от `sota-research.md`/`theses-antitheses.md`/`source-pack.md` mode-wide, не переоткрыто
здесь заново (A.10: не дублировать evidence-цепочку без необходимости). Выборочная проверка
атрибуции 3 несущих источников (S2, S17, S11) выполнена как recall-consistency check в
`theses-antitheses.md` §0.1 (НЕ веб-сверка) — стоп-находок нет, но это НЕ повышает mode-wide
unverified-статус.

**Веб-верификация 2026-07-14** (WebSearch/WebFetch): 10 научных первоисточников (S2, S3, S5, S6, S9,
S13, S14, S16, S17, S18) верифицированы (0 битых атрибуций), приоритетные якоря A4/B4-S11/S19-D4/
AI-срез (S20)/S8 привязаны к конкретным URL. Новые источники — официальная
документация Python (`docs.python.org/3/library/threadsafety.html`, `docs.python.org/3/faq/
library.html`, `py-free-threading.github.io/porting/`, PEP 779), ранняя каноническая работа по
TOCTOU (Bishop & Dilger 1996), сторонний worked-case (`urllib3/urllib3#1252`) — admitted через тот же
admission-процесс CC-DPF.5 (первый порядок: официальная документация/публичный issue-трекер, не
carrier-пересказ). Полный протокол — `references/web-verification-2026-07-14.md`; остаток источников
(S1/S4/S7/S10/S12/S15) — pretrain-only, не повышен без evidence.
FPF-разделы использованы через **live Grep** по
`~/.claude/knowledge/fpf/FPF-Spec.md` дважды: в Фазе 2 (`theses-antitheses.md`
шапка — E.4.DPF §66066, E.4.PFR §66759/66830–66845, A.2.6 §4185/4204–4207, B.5.2.1 §37336/37401,
A.11:2 §20739–20748) и повторно при сборке этого файла (Фаза 5, 2026-07-14) — подтверждены
дополнительно: E.4.DPF.DA §66506, подсекции E.4.DPF:1–12 (§66072–66504, включая :8 Anti-Patterns
§66441, :11 SoTA-Echoing §66484), A.1.1 §1732, A.7 §19604, A.10 §20278, F.18 §89773, G.2 §91683,
E.8 §67558 — все секции существуют по указанным ID на 2026-07-14 в локальной копии
FPF-Spec.md, не по памяти. Worked-evidence из `kombu-pyamqp-threadsafe` — прямое чтение
`src/kombu_pyamqp_threadsafe/__init__.py` в этой же Фазе 5 (2026-07-14), цитаты кода и комментариев
дословны (Read tool), не пересказаны по памяти. Метод (`method.md`), шаблон (`template-dpf.md`) и
роль-пакет куратора (`DPF-KNOWLEDGE-CURATION/DPF.md` + `apply-prompt.md`) прочитаны целиком перед
началом сборки, их процедурные требования применены буквально.

---

## Conformance checklist (E.4.DPF:7)

- [x] CC-DPF.1 Context declared — bounded context, intended reader, first use, non-use boundary (§1).
- [x] CC-DPF.2 Source pack present — `references/source-pack.md` (21+5=26 источников,
      adopted/rejected+причина, claim status, currentness).
- [x] CC-DPF.3 Architecture decision present — Purpose/pattern split/dependency boundary покрыты
      структурным отчётом носителя + non-use boundary §1 + §9 Relations.
- [x] CC-DPF.4 Names prepared — 10 терминов §8 (F.18), явно НЕ перенесены в glossary.md (файла нет
      в проекте).
- [x] CC-DPF.5 Carriers admitted — pretrain-источники, FPF-грепы и verified 2026-07-14
      веб-источники отмечены явно (Carrier note).
- [x] CC-DPF.6 Patterns drafted through E.8 — **7 паттернов** (≥4 гейта пройден с запасом), каждый:
      recognition → принцип (SoTA) → инстанциация (worked slice из реального кода) → контрпример
      [A.11] → анти-паттерн [E.8] → conformance → связи [E.4.PFR].
- [x] CC-DPF.7 Quality & refresh routes present — §11: критерии оценки, refresh triggers (часть
      закрыта веб-верификацией 2026-07-14), open provenance-вопросы (часть закрыта, остаток
      адресован).
- [x] CC-DPF.8 Структурный отчёт носителя в шапке — для кого/на переднем плане/огрублено-опущено/
      денора отбора/куда возврат.
- [x] CC-DPF.9 Примат решения задач — §4 (принцип→worked slice на каждый паттерн, называет типовые
      задачи домена — классификация гонки, выбор примитива, ревью), §6 (12 блокируемых failure modes),
      §7 SoTA-Echoing (14 source-grounded solution moves); не vocabulary/ontology-only каталог.

**Фаза 6:** оценка адекватности пакета (completeness-critic + E.4.DPF.DA) — `references/
critic-review*.md`; процессный след правок — `references/quality-record-2026-07-14.md`; протокол
веб-верификации источников — `references/web-verification-2026-07-14.md`.

> conformance: CC-DPF.1–9 verified; E.4.DPF.DA: admissibleForDeclaredDPFUse (critic, guardian, 2026-07-14, после ремонта r3)
> (см. `references/critic-review*.md` для истории оценки D1–D11 по кругам)
