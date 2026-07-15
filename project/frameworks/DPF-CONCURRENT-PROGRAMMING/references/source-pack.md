# Source Pack (G.2) — DPF-CONCURRENT-PROGRAMMING

> Реестр provenance (Фаза 3 метода `DPF-AUTHORING`, §4): по каждому источнику — что **взято**
> в DPF, что **намеренно отброшено** (и почему), статус claim'а (fact/hypothesis/opinion) и
> актуальность (currentness). Дом решений по референсам (FPF E.4.DPF шаг 2 / G.2). Контент
> источников — в [`sota-research.md`](sota-research.md) (G.2a CorpusLedger, G.2b ClaimSheets,
> G.2e MicroExamples) и [`theses-antitheses.md`](theses-antitheses.md) (BridgeMatrix, Тезисы
> 1–6, контрпримеры 1–6, каталог ошибок 1–11); здесь — **решения**, не пересказ содержания.
>
> **Роль исполнителя:** `DPF-KNOWLEDGE-CURATION`, Режим A (провенанс) — куратор формата/провенанса,
> НЕ владелец содержания традиций (owner содержания — architect, компетенция DPF-CONCURRENT-PROGRAMMING).
> Содержательные вопросы по традициям/claim'ам зафиксированы как открытые provenance-вопросы,
> адресованы owner-у, не решены здесь единолично (Паттерн 5 `DPF-KNOWLEDGE-CURATION`).
>
> **Режим ресёрча (явное решение заказчика, прогон 2026-07-14):** ТОЛЬКО pretrain-знания,
> WebSearch/WebFetch не использовались ни в Фазе 1, ни в Фазе 2, ни здесь (Фаза 3). Каждый
> источник ниже несёт trust-cue **«pretrain recall, не верифицирован»**, унаследованный от
> `sota-research.md`/`theses-antitheses.md` mode-wide. Веб-верификация — допустимый будущий
> repair-шаг (G.11), явно не выполнена в этом прогоне. Это НЕ снимает и не смягчает планку
> Фазы 3 (provenance-решение обязано существовать по каждому источнику независимо от режима
> ресёрча) — трактуется честно, не скрыто.
>
> **Дополнение ремонтом 2026-07-14 (круг 1, режим C):** описание выше остаётся точным для Фаз 1–3.
> ОТДЕЛЬНЫМ, более поздним прогоном тем же днём ремонт по repair-списку критика
> (`critic-review.md`) ИСПОЛЬЗОВАЛ WebSearch/WebFetch — см. секцию «Пополнение ремонта 2026-07-14»
> ниже и «Резолюции ремонта 2026-07-14» (для открытых вопросов). Полный протокол —
> [`web-verification-2026-07-14.md`](web-verification-2026-07-14.md).

---

## 1. Источники CorpusLedger (G.2a) — по каждому решение adopted/rejected

> 21 позиция сквозной нумерации `sota-research.md` (S1–S21): 15 `include` → adopted ниже
> (с указанием, ЧТО именно взято — конкретный тезис/паттерн-кандидат/типовая ошибка),
> 5 `park` → rejected ниже (с причиной из триажа Фазы 1, не молчаливым пропуском), 1 позиция
> (S21) — include, но заявлен как `hypothesis`, не `fact` (понижен явно). 0 `retire`.

### Традиция A — Классическая теория ОС / формальная конкурентность

| Источник | Adopted (взято в DPF) | Rejected (намеренно отброшено) + причина | Claim status | Currentness |
|----------|----------------------|--------------------------------------------|--------------|-------------|
| S1 — Silberschatz, Galvin, Gagne, *Operating System Concepts*, 9th/10th ed. (~2012/2018) | Базовая таксономия race condition / критическая секция / deadlock — словарь-основа для Тезиса 1 и Тезиса 3 | — | fact | Durable (учебник, канон не устаревает); edition 2012/2018 по recall, не сверена |
| S2 — Coffman, Elphick, Shoshani, *System Deadlocks*, ACM Computing Surveys, 1971 | 4 условия deadlock (mutual exclusion / hold-and-wait / no preemption / circular wait); достаточно снять любое одно → Тезис 3, типовая ошибка №7 | — | fact | Durable; проверена на recall-consistency (theses-antitheses §0.1) — «не битая», не веб-верифицирована |
| S3 — Hoare, *"Monitors: An Operating System Structuring Concept"*, CACM, 1974 | Monitor = один лок + condition variable, предикат не хранится в CV → обязателен re-check после `wait()` → Тезис 4, прямой предок `threading.Condition` | — | fact | Durable |
| S4 — Dijkstra, *"Cooperating Sequential Processes"*, 1965/1968 (семафоры) | — | Семафоры не первичный примитив в bounded context (Python предпочитает Lock/Condition в нашем домене); держится как исторический фон, не отдельный claim-носитель — избежать раздувания ledger дублями без нового независимого утверждения | fact (историческая база, не адаптирован для DPF) | Durable как история; не отобран для DPF.md |
| S5 — Netzer & Miller, *"What Are Race Conditions? Some Issues and Formalizations"*, ACM LOPLAS, 1992 | Формальное разделение data race vs race condition (race condition ⊋ data race) → центральное для Тезиса 1 | — | fact | Durable |
| S6 — Herlihy & Shavit, *The Art of Multiprocessor Programming*, Morgan Kaufmann, 2008 (rev. 2012) | Linearizability как критерий корректности конкурентного объекта; lock-free/CAS как понятие (не примитив) → фон Тезиса 5/контекст для проектирования собственных потокобезопасных структур | — | fact | Durable (концепция); издание 2008/2012 не протухает как теория |
| S7 — Lamport, *"Time, Clocks, and the Ordering of Events in a Distributed System"*, CACM, 1978 | — | Happens-before изначально сформулирован для распределённых систем; понятие используется опосредованно (через B5/order violation), сам источник и распределённая часть — за non-use boundary этого DPF (см. `scope.md`: НЕ распределённая согласованность) | fact (историческая база, не адаптирован) | Durable как история; не отобран как отдельный источник DPF.md |

### Традиция B — CPython / GIL-специфика

| Источник | Adopted (взято в DPF) | Rejected (намеренно отброшено) + причина | Claim status | Currentness |
|----------|----------------------|--------------------------------------------|--------------|-------------|
| S8 — Python core docs, `threading` module reference / GIL раздел (Python 3.x devguide); FAQ «What kinds of global value mutation are thread-safe?» (docs.python.org/3/faq/library.html) | Нормативное описание: GIL атомизирует один bytecode, не составную операцию; освобождение GIL вокруг блокирующих C-вызовов → Тезис 2, типовая ошибка №1 | — | fact, **verified 2026-07-14** (atomicity-список сверен дословно по FAQ-URL) | Version-dependent (охватывает разные версии «до ~3.12» по recall для GIL/threading-раздела) — требует периодической сверки с текущей версией docs при review_due; FAQ-atomicity-claim сверен 2026-07-14 |
| S9 — Beazley, *"Understanding the Python GIL"* / *"Inside the New GIL"*, PyCon 2010 | Эмпирика переключения GIL по интервалу; I/O-bound vs CPU-bound convoy → обоснование Тезиса 2 (анти-тезис №2: I/O-safepoint непредсказуем) | — | fact (эмпирический доклад) | 2009–2010, дата дана; концепция durable, конкретные бенчмарки не переверифицированы |
| S10 — Beazley & Jones, *Python Cookbook*, 3rd ed., O'Reilly, 2013, гл. 12 (Concurrency) | Практические идиомы: `Queue`/`Condition`, границы атомарности встроенных операций контейнеров → MicroExamples ME1/ME2, типовая ошибка №1 | — | fact | Durable как практическая ссылка; 2013 |
| S11 — Gross, PEP 703 *"Making the GIL Optional in CPython"*, 2023 | Free-threaded build меняет инварианты «GIL как бесплатный лок» → claim B4, Тезис 2 анти-тезис №3, типовая ошибка №10 (ИИ) | — | fact | **Decay-риск повышен явно** (самое молодое знание пакета, 2023) — точный статус развёртывания (какая версия делает free-threaded default) НЕ переверифицирован, кандидат №1 на веб-верификацию при repair |
| S12 — Hettinger, *"Thread Synchronization Methods in Python"*, PyCon talks (~2011–2013) | — | Пересекается с S9/S10 без нового независимого claim; не даём отдельную запись, чтобы не раздувать ledger дублями (сохранена причина из триажа Фазы 1) | fact (не переоткрыт отдельно) | Не отобран как отдельный источник |

### Традиция C — Паттерны конкурентного ПО (POSA2 / JCiP)

| Источник | Adopted (взято в DPF) | Rejected (намеренно отброшено) + причина | Claim status | Currentness |
|----------|----------------------|--------------------------------------------|--------------|-------------|
| S13 — Buschmann, Schmidt, Stal, Rohnert, *POSA2: Patterns for Concurrent and Networked Objects*, Wiley, 2000 | Monitor Object (C1), Half-Sync/Half-Async (C5) → Тезис 4/5, прямая онтологическая база паттернов DPF.md | — | fact | Durable |
| S14 — Goetz et al., *Java Concurrency in Practice*, Addison-Wesley, 2006 | Guarded Suspension (`while` вокруг `wait()`, C2), thread confinement / safe publication (C3) → Тезис 4/5, типовая ошибка №2 | — | fact | Durable |
| S15 — Lea, *Concurrent Programming in Java*, 2nd ed., 1999/2000 | — | Пересекается с S13/S14 (тот же круг идей, частично тот же автор); держится как фон, не отдельный claim-носитель — избежать authority-by-citation дублирования (причина унаследована из триажа Фазы 1) | fact (не переоткрыт отдельно) | Не отобран как отдельный источник |
| S16 — Bacon et al., *"The 'Double-Checked Locking is Broken' Declaration"*, ~2001 | Anti-pattern DCL (C4) — контрпример 1 (граница Тезиса 2): урок «неверифицированная оптимизация» переносится, конкретный механизм visibility-reordering (JMM) — НЕ переносится на GIL-CPython без переверификации | — | fact | Durable как урок; применимость к CPython явно ограничена оговоркой B5 (нет formal memory model) |

### Традиция D — Эмпирическое изучение багов конкурентности

| Источник | Adopted (взято в DPF) | Rejected (намеренно отброшено) + причина | Claim status | Currentness |
|----------|----------------------|--------------------------------------------|--------------|-------------|
| S17 — Lu, Park, Seo, Zhou, *"Learning from Mistakes"*, ASPLOS 2008 | Таксономия atomicity violation / order violation (D1), корень багов — неверное допущение об инварианте, не «забыл лок» (D2) → **центральный Тезис 6**, типовая ошибка №1/№11 | — | fact | Durable как эмпирический паттерн; выборка (2008, тогдашние C/C++/Java проекты) — категории признаны переносимыми, ЦИФРЫ и Python-специфика — нет (BridgeMatrix «явная потеря»); проверена на recall-consistency (theses-antitheses §0.1) |
| S18 — Musuvathi, Qadeer et al., CHESS, ~2007–2008 | Систематический контроль интерливинга vs случайный stress-test (D3) → типовая ошибка №6 | — | fact | Durable как принцип тестирования |
| S19 — Serebryany & Iskhodzhanov, *"ThreadSanitizer: Data Race Detection in Practice"*, WBIA, 2009 | Контраст: индустриальный race-детектор (happens-before/vector clocks) существует для C/C++/Go/Rust, для pure Python эквивалента нет (D4) → Тезис 6, типовая ошибка №6 | — | fact | Факт про инструментарий других экосистем — durable; заявление «для Python эквивалента НЕТ» — pretrain recall на момент cutoff, не переверифицировано (могло появиться новое после обучающих данных модели) — открытый provenance-вопрос |

### Обязательный ИИ-срез

| Источник | Adopted (взято в DPF) | Rejected (намеренно отброшено) + причина | Claim status | Currentness |
|----------|----------------------|--------------------------------------------|--------------|-------------|
| S20 — Pearce et al., *"Asleep at the Keyboard? Assessing the Security of GitHub Copilot's Code Contributions"*, IEEE S&P 2021/2022 | Эмпирика: LLM-сгенерированный код содержит заметную долю багов из классов, смежных с TOCTOU/race (AI1) → типовая ошибка №3/№9 | — | fact (эмпирическое исследование) | 2021–2022; **цифры явно НЕ переносить** на современные модели — тестировались ранние Copilot/Codex, устаревшие относительно текущих LLM |
| S21 — агрегированное наблюдение сообщества (не единичная статья): распределение обучающих данных LLM смещено к однопоточным туториалам / устаревшим StackOverflow-ответам про GIL | Мотивирует AI2 (LLM статистически чаще ошибается в тонком: if-vs-while, exception-safety, compound-atomicity, ленивая init) и приоритет чек-листа AI4 → усилено пересечением с D1/D2 (`fact`), НЕ единственная опора (Тезис 6, анти-тезис №3) | — | **hypothesis, явно понижено** (не единичный citable источник — агрегированное наблюдение практиков) | Не датируется отдельно; explicit `claim_status: hypothesis` унаследован из sota-research.md AND theses-antitheses.md — НЕ повышать до fact без эмпирического измерения |

**Итог секции 1:** 15 `adopted` (из 21 позиции CorpusLedger), 5 `rejected` (S4, S7, S12, S15 — «фон/дубликат, не отдельный claim-носитель»; отдельно S21 — `adopted`, но как `hypothesis`, что не эквивалентно rejected). Согласуется с триажем Фазы 1 (`sota-research.md`: 15 include / 5 park / 0 retire) — **числа сверены и совпадают**, решения секции 1 не переопределяют триаж Фазы 1, а формализуют его в терминах adopted/rejected Фазы 3 (та же классификация, другой словарь метода).

### Пополнение ремонта 2026-07-14 (круг 1, режим C) — S22–S26, все `adopted`, все `verified`

> Паттерн 1 `DPF-KNOWLEDGE-CURATION`: новая, ДОПОЛНИТЕЛЬНАЯ секция — S1–S21 выше и их adopted/
> rejected решения НЕ переписаны. Источники ниже прошли admission через WebSearch/WebFetch
> 2026-07-14 (не pretrain recall); полный протокол — `web-verification-2026-07-14.md`.

| Источник | Adopted (взято в DPF) | Rejected + причина | Claim status | Currentness |
|----------|------------------------|---------------------|--------------|-------------|
| S22 — Bishop, M.; Dilger, M., *"Checking for Race Conditions in File Accesses"*, Computing Systems, 1996, pp. 131–152 | Ранняя каноническая детальная работа по TOCTOU в file-access — закрывает A4-provenance-gap (открытый вопрос №3) → Паттерн 1 (`DPF.md`). **Исправлено по верификации 2026-07-14:** было «первоисточник термина TOCTOU/TOCTTOU», стало «ранняя каноническая детальная работа» — Wikipedia (Time-of-check_to_time-of-use, спот-чек 2026-07-14) держит эту работу в разделе Further reading, не приписывая ей явно чеканку номенклатуры | — | fact (genuine источник, атрибуция авторы/venue/год/страницы точна; verified) | 1996; durable (работа не устаревает); атрибуция подтверждена 2026-07-14, формулировка «coining» смягчена тем же днём |
| S23 — Python core team, *Thread Safety Guarantees*, docs.python.org/3/library/threadsafety.html | Официальные атомарность-гарантии dict/list/set под free-threaded + явный TOCTOU-пример (`if key in d: del d[key]`) → усиливает A4/Паттерн 1, основа Паттерна 7 | — | fact (официальная документация первого порядка) | Живой документ (версионируется вместе с Python); verified 2026-07-14, требует сверки при смене мажорной версии Python |
| S24 — Python Free-Threading Guide, «Porting Python Packages to Support Free-Threading», py-free-threading.github.io/porting/ | «GIL-was-providing-safety» требует переанализа; рекомендация копировать shared-ссылку в локальную переменную → принцип Паттерна 7 | — | fact (официальный community-гайд CPython free-threading экосистемы) | Живой документ; verified 2026-07-14 |
| S25 — Python Steering Council, PEP 779 *"Criteria for supported status for free-threaded Python"* | Уточняет B4/S11: 3.14 officially supported non-default; default не ранее 2028+ → Паттерн 2 анти-паттерн, §11 refresh | — | fact (принятый PEP) | 2025 (принятие), verified 2026-07-14 — decay-риск как ТИП остаётся (Phase III не наступил) |
| S26 — GitHub `urllib3/urllib3#1252` "PoolManager is not thread-safe" (+ #1232, #204) | Worked-evidence TOCTOU-класса ВНЕ `kombu-pyamqp-threadsafe` → HC-4 (`DPF.md` §10), закрывает D8/C-3 | — | fact (публичный issue-трекер, воспроизводимая история бага) | Issue открыт исторически, статус закрыт; verified WebFetch 2026-07-14 — конкретный статус фикса может измениться, сама история бага durable |

**Итог пополнения:** 5 `adopted`, 0 `rejected`, 0 `retired` — все `verified 2026-07-14` (WebSearch/
WebFetch), не pretrain recall. Общий CorpusLedger после ремонта: S1–S26 (26 источников).

---

## 2. Артефакты пайплайна (Фазы 0–2 этого же прогона)

| Источник | Adopted (взято в DPF) | Rejected (намеренно отброшено) + причина | Claim status | Currentness |
|----------|----------------------|--------------------------------------------|--------------|-------------|
| `references/scope.md` (Фаза 0) | Bounded context, intended reader, first use, non-use boundary — рамка всего пакета; честно зафиксированный гэп (domain.md/decisions/competency-map.md отсутствуют в репозитории) | Полный OAIS-аппарат курирования и т.п. не рассматривались на этой фазе — вне scope Фазы 0 | decision (не claim в смысле G.2, а зафиксированная граница компетенции) | 2026-07-14 |
| `references/sota-research.md` (Фаза 1) | Полный G.2a CorpusLedger + G.2b ClaimSheets (A1–A5, B1–B5, C1–C5, D1–D4, AI1–AI4) + G.2e MicroExamples (ME1–ME5) + G.2c Operator/Object inventory — базовый слой для Bridge (Фаза 2) | BridgeMatrix/тезисы намеренно НЕ производились здесь (research-first гейт метода: Фаза 1 и Фаза 2 разделены) | mode-wide unverified (pretrain recall) | 2026-07-14 |
| `references/theses-antitheses.md` (Фаза 2) | BridgeMatrix (alignment/divergence 5 линий, явные потери), 6 тезисов (scope + анти-тезис NQD≥3 + тип связи), 6 контрпримеров (A.11 Sharp Boundary), 11 типовых ошибок — прямой вход для сборки DPF.md (Фаза 5, вне scope этого прогона) | — | mode-wide unverified (pretrain recall); ни один тезис не повышен до `fact` по гладкости изложения (явно оговорено в §5 gate-проверки файла) | 2026-07-14 |
| `~/.claude/skills/dpf-authoring/references/method.md` (канон метода, live) | Канон-скелет DPF.md, 6-фазный алгоритм, Фаза 3 требование («по каждому источнику: adopted/rejected+причина/claim-status/currentness», gate «provenance полон») — структурная рамка ЭТОГО файла | — | fact (канон метода, не предмет ревизии этой роли) | `fpf_edition: ailev/FPF@f7c7e93f` (снимок 2026-07-03; локальная копия FPF-Spec обновлена 2026-07-06); сверено live-grep 2026-07-14 (см. carrier note) |
| `~/.claude/skills/dpf-authoring/frameworks/DPF-KNOWLEDGE-CURATION/DPF.md` + `assets/apply-prompt.md` (роль-пакет куратора) | Процедура Режима A (провенанс): гейт самопроверки, дисциплина «реестр копится, не переписывается», требование отдельной retired-секции с явным нулём, требование «провенанс пишется в момент решения, не постфактум» — применены буквально к структуре этого файла | Режим B (Assemble) этого пакета — НЕ выполняется в этом прогоне (задание ограничено Фазой 3/Source-pack) | fact (роль-пакет метода) | `updated: 2026-07-06`, `review_due: 2026-09-29` — не протух на дату прогона 2026-07-14 |
| FPF `G.2` (SoTA Harvester & Synthesis), `E.4.DPF` (spine), сверено live-grep `~/.claude/knowledge/fpf/FPF-Spec.md` (паттерн `^## G\.2`, `^## E\.4\.DPF`) | Подтверждение: структура source-pack (adopted/rejected/claim-status/currentness по источнику) соответствует G.2 требованию evidence-addressable/actionable/refreshable SoTA-пака; Фаза 3 метода — прямая инстанциация G.2 применительно к DPF-каталогу | Полный текст G.2:1–G.2:3 (Problem frame/Problem/Forces) и весь E.4.DPF.DA (адекватность пакета, Фаза 6) — НЕ предмет Фазы 3, читаются живьём при необходимости, не пересказываются здесь | fact (FPF-спека, не предмет ревизии этой роли) | Сверено Grep 2026-07-14 (эта роль); `fpf_edition` — см. строку method.md выше |

---

## 3. Отсутствующий контекст проекта (честно зафиксировано, не додумано)

| Источник | Adopted (взято в DPF) | Rejected (намеренно отброшено) + причина | Claim status | Currentness |
|----------|----------------------|--------------------------------------------|--------------|-------------|
| `project/domain.md` | — | **Rejected: файл не существует** в репозитории `kombu-pyamqp-threadsafe` на момент прогона. Проверено `ls`/`find`, 2026-07-14 (Bash, evidence не мнение). Не «отброшен по содержанию» — отброшен, потому что нет носителя. Задокументировано в `scope.md` как известный гэп контекста (A.10, не молчком) | n/a (источник отсутствует) | Проверено 2026-07-14 |
| `project/decisions/` (каталог DEC-NNN) | — | **Rejected: каталог не существует.** Проверено `ls`, 2026-07-14. Ни одного DEC-NNN не может быть процитирован в этом пакете — не потому что решения отклонены по содержанию, а потому что решений-документов в проекте нет | n/a (источник отсутствует) | Проверено 2026-07-14 |
| `project/frameworks/competency-map.md` | — | **Rejected: файл не существует.** Проверено `ls`, 2026-07-14. `project/frameworks/` на момент прогона содержит только `DPF-CONCURRENT-PROGRAMMING/` (этот пакет) и пустой каталог-заготовку `DPF-DEDICATED-IO-THREAD/` | n/a (источник отсутствует) | Проверено 2026-07-14 |
| `src/kombu_pyamqp_threadsafe/__init__.py` (прямое чтение исходников) | Референсная инстанциация bounded context в `scope.md`: `threading.RLock` вокруг transport/dispatch/create-channel, `DrainGuard` (Condition + RLock, single-active-reader паттерн), `channel_thread_bindings` (per-thread channel ownership), `threading.Event` для teardown — подтверждено прямым чтением кода, 2026-07-14 | Полный код проекта НЕ прочитан построчно — только конструкции, релевантные bounded context конкурентности (сфокусированное чтение, не аудит всего файла) | fact (evidence — чтение кода, A.10 Work, не MethodDescription) | Проверено чтением 2026-07-14; трактуется как «инстанциация domain-фактов», не как сам domain-факт (нет decisions-документа, подтверждающего ИНТЕНЦИЮ выбора именно этих примитивов — только их присутствие в коде) |

---

## Retired premises

**Ноль.** Обоснование: G.2a CorpusLedger (`sota-research.md`) зафиксировал триаж на 2026-07-14
с итогом «15 include, 5 park, **0 retire**» — ни один источник не был отозван (retired) ни на
Фазе 1, ни при построении Bridge (Фаза 2), ни в этом прогоне Фазы 3. `Park`-источники (S4, S7,
S12, S15) — НЕ retired: они удержаны видимыми для будущего расширения scope (см. секцию 1), в
отличие от retired premise, которая была бы явно признана несостоятельной/устаревшей и выведена
из обращения. Пограничный случай — claim A4 (TOCTOU) в `theses-antitheses.md` §0.1: помечен как
provenance пограничного качества (нет единичного crisp источника), но НЕ retired — это открытый
provenance-вопрос (см. ниже), кандидат на repair (привязка к источнику или явная пометка
«durable-определение без единого первоисточника») в Фазе 5/6, не решение об отзыве.

---

## Открытые provenance-вопросы

1. **B4/PEP 703 decay-риск (S11).** Точный статус развёртывания free-threaded CPython (какая
   версия делает non-GIL сборку default) заявлен по pretrain recall модели и НЕ переверифицирован
   веб-поиском. Какой evidence нужен, чтобы повысить до fact: сверка с текущей CPython release
   notes/PEP 703 status на момент repair-шага (G.11).
2. **AI1/AI2 (S20/S21) — перенос на современные LLM.** Эмпирика Pearce et al. (2021–2022,
   ранние Copilot/Codex) и агрегированное наблюдение о training-data skew — оба explicitly НЕ
   переносимы 1:1 на модели текущего поколения. Какой evidence нужен: свежее эмпирическое
   сравнение LLM-сгенерированного конкурентного Python-кода на предмет C2-нарушений (if vs while)
   на актуальных моделях — не выполнено ни в Фазе 1, ни здесь (hypothesis остаётся hypothesis).
3. **A4 (TOCTOU) — provenance пограничного качества.** Claim не несёт единичного crisp
   «источник+дата» в `sota-research.md` (сказано «security-литература, общеупотребительна, в
   паре с S1»); Netzer/Miller (S5) покрывает разделение data race vs race condition, но не сам
   термин TOCTOU. Какой evidence нужен: либо привязать к конкретному первоисточнику термина
   (repair-кандидат Фазы 5/6), либо явно задокументировать как «durable-определение без единого
   первоисточника» — решение оставлено owner-у домена (architect) / guardian (Фаза 6), не куратору.
4. **S19/D4 — «для pure Python нет TSan-эквивалента».** Заявлено по pretrain recall на момент
   cutoff модели; не переверифицировано, могло появиться новое в тулинге экосистемы Python после
   даты обучения. Какой evidence нужен: веб-проверка актуального состояния race-detection
   тулинга для CPython (repair-шаг G.11).
5. **Полное отсутствие domain.md/decisions/competency-map.md в проекте.** Задание ссылалось на
   эти файлы как на контекст; ни один не существует (см. секцию 3). Это НЕ блокирует Фазу 1/2/3
   (bounded context задан текстом задания + прямым чтением кода), но лишает Bridge/будущую сборку
   DPF.md возможности сослаться на project-специфичные DEC/domain-факты. Открытый вопрос,
   адресован facilitator/architect: создавать ли `domain.md`/`decisions/`/`competency-map.md` для
   `kombu-pyamqp-threadsafe` до Фазы 5, или DPF.md сознательно обойдётся без project-level
   decision-ссылок (только `scope.md`-инстанциация через прочитанный код).
6. **Веб-верификация целиком не проводилась** (mode-wide, явное решение заказчика на этот
   прогон). Статус ПАКЕТА в целом (`seedOnly`/`repairBeforeDPFUse`/`admissibleForDeclaredDPFUse`)
   решается независимо Фазой 6 (guardian) — этот source-pack честно не присваивает себе более
   высокий статус, чем позволяет режим ресёрча (см. `theses-antitheses.md` §5 итоговая честная
   оговорка, унаследована сюда).

---

## Резолюции ремонта 2026-07-14 (круг 1, режим C) — дополнение, не переписывание

> Паттерн 1 `DPF-KNOWLEDGE-CURATION`: открытые вопросы №1–4 выше НЕ удалены и НЕ переписаны;
> ниже — датированные резолюции, добавленные отдельным ремонтом. Полный протокол проверок —
> [`web-verification-2026-07-14.md`](web-verification-2026-07-14.md).

- **→ Вопрос №1 (B4/PEP 703) — уточнён.** Веб-верифицировано 2026-07-14: PEP 779 подтверждает
  free-threaded в Python 3.14 как «officially supported», НЕ default; полный default (Phase III) —
  не ранее 2028+. Источник — S25 (`sota-research.md` «Пополнение»). Decay-риск как ТИП остаётся:
  следующая ревизия обязана сверить снова (живой процесс CPython, не застывший факт).
- **→ Вопрос №2 (AI1/AI2) — частично закрыт.** Атрибуция Pearce et al. (S20) верифицирована
  2026-07-14 (авторы/venue/год/страницы точны). Перенос эмпирики 2021–2022 на модели текущего
  поколения — **НЕ закрыт**, свежее эмпирическое сравнение не выполнено (research-gap остаётся,
  `hypothesis` не переоткрыт до `fact`, честно).
- **→ Вопрос №3 (A4/TOCTOU) — закрыт.** Первоисточник термина найден и верифицирован 2026-07-14:
  Bishop, M.; Dilger, M., *"Checking for Race Conditions in File Accesses"*, Computing Systems,
  1996, pp. 131–152 (S22, `sota-research.md`). Привязка добавлена в `DPF.md` Паттерн 1, §6 ошибка 5,
  §8 имена, §11.
- **→ Вопрос №4 (S19/D4, TSan) — уточнён.** Верно для GIL-сборки CPython (по-прежнему нет
  pure-Python-уровня детектора). Для free-threaded сборок (PEP 703/779) TSan-инструментированные
  интерпретаторы существуют и активно используются CPython CI (S24, py-free-threading.github.io/
  thread_sanitizer/, десятки issue 2025–2026) — C-уровневый, не pure-Python-level инструмент.
- **Вопросы №5 и №6 — БЕЗ ИЗМЕНЕНИЙ.** №5 (`domain.md`/`decisions/`/`competency-map.md`) вне
  мандата куратора формата — адресован facilitator/architect, не решён здесь. №6 (веб-верификация
  целиком) — **частично** выполнена этим ремонтом (приоритетные якоря + 10 научных первоисточников
  S1–S21, спот-чек), но НЕ ПОЛНОСТЬЮ (S1/S4/S7/S8/S10/S12/S15 остаются pretrain-only) — статус
  пакета по-прежнему решает Фаза 6/критик, не этот файл.

---

## Резолюции ремонта 2026-07-14 (круг 2) — дополнение по repair-списку `critic-review-2026-07-14-r1.md`

> Паттерн 1 `DPF-KNOWLEDGE-CURATION`: круг 1 выше НЕ переписан; ниже — датированные резолюции по
> двум наименьшим правкам круга 2 (R2-2, R2-3). Полный протокол — `web-verification-2026-07-14.md`.

- **→ Вопрос №3 (A4/TOCTOU) — формулировка уточнена (R2-2, косметика, не блокирует).** Спот-чек
  критика Круга 2 показал, что круг-1 формулировка «первоисточник термина найден» опиралась на
  прочтение web-verification сильнее, чем позволяет сам источник (Wikipedia держит Bishop & Dilger
  1996 в разделе Further reading, не приписывая ему явно чеканку TOCTOU/TOCTTOU-номенклатуры).
  Прямая повторная сверка WebFetch 2026-07-14 (та же страница) подтвердила находку критика.
  **Исправлено:** было «первоисточник термина TOCTOU/TOCTTOU» / «первоисточник термина найден»,
  стало «ранняя каноническая детальная работа по TOCTOU в file-access» — genuine источник и
  атрибуция (авторы/venue/год/страницы) остаются точны и verified, claim «coining» снят. Правка
  внесена в `sota-research.md` A4/S22 и в этот файл (строка S22 выше).
- **→ Вопрос №6 (веб-верификация целиком) — S8 частично закрыт (R2-3, дёшево, refresh-route).**
  Приоритет круга 1 не включал S8/S10 (GIL-atomicity core docs) явно. WebFetch 2026-07-14 на
  `docs.python.org/3/faq/library.html` подтвердил дословно: список атомарных операций
  (`L.append(x)`, `x=y`, `D[x]=y`, ...) и неатомарных (`i=i+1`, `D[x]=D[x]+1`, ...) — ровно то, что
  claim B1/SE-4/Паттерн 2 заявляют. **S8 переведён из pretrain в verified 2026-07-14** (см.
  `sota-research.md` B1, CorpusLedger S8; `DPF.md` Паттерн 2/§7 SE-4). **S10** (Beazley & Jones,
  *Python Cookbook* 3rd ed., книга) — существование главы 12 подтверждено через оглавление
  издателя/автора (WebSearch 2026-07-14), но точный текст книги недоступен для прямой веб-сверки
  (paywall) — остаётся `pretrain recall`, честно не повышен без доступа к первоисточнику. Остаток
  pretrain-only после этой правки: S1/S4/S7/S10/S12/S15.

---

## Carrier note (CC-DPF.5)

Все pretrain-источники (S1–S21) в этом пакете несут trust-cue «pretrain recall, не
верифицирован» — унаследовано от `sota-research.md`/`theses-antitheses.md` mode-wide, не
переоткрыто здесь заново (A.10: не дублировать evidence-цепочку без необходимости). FPF-разделы
(G.2, E.4.DPF) использованы через live Grep по `~/.claude/knowledge/fpf/FPF-Spec.md` в этом
прогоне (2026-07-14), не по памяти — секция 2 таблица, последняя строка. Метод (`method.md`) и
роль-пакет куратора (`DPF-KNOWLEDGE-CURATION/DPF.md` + `apply-prompt.md`) прочитаны целиком перед
началом работы, их процедурные требования применены буквально (структура таблиц, retired-секция
с явным нулём, открытые provenance-вопросы адресованы owner-у, не решены куратором).
