---
artifact: "Phase-6 Critic / Package-Adequacy (E.4.DPF.DA + CC-DPF.1–9)"
dpf_id: "DPF-DEDICATED-IO-THREAD"
phase: 6
date: "2026-07-14"
role: "DPF-ADVERSARIAL-REVIEW @2026-07-06 (Mode B — Critic / package adequacy; owner: guardian)"
role_separation: "guardian-pass, независим от сборки DPF.md (assembler) и от Phase-1/2 owner — role-separation-gate (Паттерн 1 / DEC-003) удовлетворён: этот проход research/bridge/assembly не делал"
mode: "PRETRAIN-ONLY run (2026-07-14): FPF-канон сверен живьём Grep по FPF-Spec.md (E.4.DPF:7, E.4.DPF:8, E.4.DPF.DA целиком). Web-верификация доменных claim'ов НЕ выполнена — это оценивается как свойство пакета, а не как дефект критика."
input: "DPF.md + references/{scope,sota-research,theses-antitheses,source-pack}.md; live FPF-Spec E.4.DPF/E.4.DPF.DA (grep 66421–66757)"
verdict: "repairBeforeDPFUse — D11 ниже пола 4 для заявленного reliance-bearing использования"
gate: "CC-DPF.1–9 PASS, но статус ≠ admissibleForDeclaredDPFUse → gate_passed=false"
---

# DPF-DEDICATED-IO-THREAD — Phase 6: Critic / Package-Adequacy

> Дисциплина остроты (Паттерн 5, анти-угодливость). Пакет собран исключительно тщательно и честно;
> это НЕ основание смягчать вердикт. Ниже — ≥3 вероятных И значимых концерна, а не 50 придирок и не
> подтверждающий штамп. Severity выставлен как есть. Один внимательный проход (норма роли).

---

## 0. Completeness-критика (Режим B, шаг 1 — до PFM и D1–D11)

Проверено по файлам пакета и по живому канону (Grep FPF-Spec `E\.4\.DPF`, `E\.4\.DPF\.DA`), не по
отчёту сборщика.

### 0.1 Упущенная традиция
- **Actor / Erlang-OTP (`gen_server`: один процесс единолично владеет состоянием) — не харвестена.**
  Оправдано parsimony (A.11): это по сути Active Object (T1-C1) в другом синтаксисе, независимого
  claim'а не даёт. **Не пробел.**
- **Go: goroutine + channel-ownership («share memory by communicating», один owner-goroutine на
  ресурс) — не представлена и НЕ является рестейтом Active Object** (иная модель: владение выражено
  каналом, не очередью+потоком-планировщиком; это живой, широко используемый current-SoTA
  инстанс). Мягкий пробел: обогатил бы T3/D8, не блокирует. **Repair-кандидат D11/D8, не floor-дефект.**

### 0.2 Непокрытая тензия (значимо)
Компетенция названа «Ownership, **Servicing**, and **Lifecycle**», а `scope.md` (Bounded context)
явно перечисляет в servicing/start: **write-side backpressure**, **timers/heartbeat**, **lazy-on-first-use
vs explicit `start()`**, **thread naming/observability**, **who is the lifecycle owner**, **daemon vs
non-daemon**. Паттерны §4 сильно покрывают: модель владения (P1), crossing (P2), узкий scope (P3),
shutdown (P4), reconnect/fork (P5), AI-чек-лист (P6). **НЕ операционализированы ни в тезис, ни в паттерн:**
- **Write-side backpressure** — назван в bounded context И заведён отдельным термином в §8 глоссария
  («An unbounded queue silently growing forever»), но НЕТ ни тезиса в `theses-antitheses.md`, ни
  паттерна, ни строки в каталоге ошибок. Bounded context/глоссарий обещают то, чего паттерн-язык не
  выдаёт — это ровно near-miss «carrier обещает структуру, которой нет за ним».
- **Start-timing / lifecycle-owner / naming** (lazy vs explicit start, кто владелец жизненного цикла,
  именование потока) — перечислены в scope как первоклассная забота компетенции, но растворены: P1 про
  *какое семейство владения*, не про *когда/кем стартует и как наблюдается*. Отдельного решающего
  паттерна нет.
- **Repair (наименьший):** либо добавить (а) тезис+паттерн «Bounded write backpressure» и (б)
  паттерн «Start-timing & lifecycle ownership (lazy vs explicit, naming, daemon)», либо **явно
  сузить** bounded context / non-use boundary, убрав backpressure и start-timing из обещанного охвата.
  Сейчас охват заявлен шире, чем паттерны решают → бьёт по D1 (recoverability охвата) и D7 (одна
  обещанная задача проектирования не решена).

### 0.3 Claim без источника / голая частность / отсутствующий контрпример
- **Claim без источника: нет.** Каждый несущий claim несёт источник+дату+trust-cue; AI-срез (S15/Тезис 6)
  без цитируемого носителя честно помечен `opinion/hypothesis, lower-confidence` и НЕ пропущен в несущие
  наравне с T1–T4 — это ровно корректная работа Popper-гейта (Паттерн 3), а не дефект.
- **Голая частность без принципа: нет.** Каждый worked slice (`DrainGuard`/`_transport_lock`/
  `channel_thread_bindings`/`_teardown_lock`) предварён общим SoTA-принципом (Паттерн 2 метода соблюдён).
- **Контрпримеры присутствуют и отделены от анти-паттернов** (A.11): CE1–CE5 отдельной секцией в
  `theses-antitheses.md` §3; в DPF.md встроены в блоки паттернов как `Counterexample [A.11]`, отдельно
  от `Anti-pattern [E.8]`. **Не пробел.**
- **Положительная находка (усиливает, не смягчает):** фальсификация T2-C4 (kombu Hub self-pipe)
  прямым чтением kombu 5.6.2 — образцовая evidence-дисциплина (RP-1, Repair register). Она же —
  ключевая улика против D11 (см. §3).

---

## 1. Подпроход формы пакета PFM1–PFM11 (CC-DPFDA.6a — до значений D)

| PFM | Проверка | Дисп. | Обоснование / evidence-locus |
|-----|----------|-------|------------------------------|
| PFM1 Front-door order | ToC + структурный отчёт до тел паттернов, читатель выбирает паттерн, не читая аппарат | **PASS** | «Оглавление (PFM1 — patterns first)» + структурный отчёт в шапке; тяжёлый BridgeMatrix — в references |
| PFM2 Pattern-language primacy | Паттерны — главный язык; тяжёлые карты после/в приложениях | **PASS** | §4 (6 паттернов) идёт как основной язык; BridgeMatrix/ClaimSheets вынесены в references, в §2/§3 только сводка+указатель |
| PFM3 Map discoverability | У каждой карты есть живой маршрут входа из работы | **PASS** | §2/§3 и «Artifacts» линкуют `theses-antitheses.md` (BridgeMatrix), достижимо из ToC и из тел паттернов («BridgeMatrix Ось A/B») |
| PFM4 Dependency direction | DPF цитирует FPF Core/метод; Core не зависит от DPF | **PASS** | §9 Relations: `uses`→DPF-AUTHORING, `grounded_in`→FPF; обратной зависимости нет |
| PFM5 Publication/access-carrier boundary | Карьер не подменяет архитектуру/качество/провенанс | **PASS** | DPF.md — публикационный носитель; провенанс/качество/repair — в `references/` |
| PFM6 Public package naming | Доменное имя, process-state вне идентичности | **PASS** | Имя «Dedicated IO Thread: Ownership, Servicing, and Lifecycle…»; `status: stage-0` — во frontmatter, не в заголовке (допустимо) |
| PFM7 Development-state absence | Нет разбросанного process-run/handoff/review-status residue в носителе | **FAIL (repairable)** | `research_mode:` во frontmatter (process-run state); повторяющееся «this run» / «Phase 6 has not run» / «this is a Phase 4–5 assembly» / «assembler, this run» (структурный отчёт, §11, Conformance) — это process-run/admission-blocker residue сверх одной допустимой финальной conformance-строки. **Различать:** per-claim trust-cue `pretrain recall` = ЛЕГИТИМНЫЙ durable user-facing контент (качество evidence нужно читателю); а фаза-трекинг прогона — нет. Тот же класс дефекта (D9/PFM7 process-residue), что HC-2/HC-3 в самом DPF-ADVERSARIAL-REVIEW. Лечит D5/D9, не роняет их ниже пола |
| PFM8 Cross-DPF relation discipline | Ссылка на соседний DPF как E.4.PFR-связь с blocked reading | **PASS** | §9: `DPF-CONCURRENT-PROGRAMMING` как `scope_boundary/peer`, граница названа, не резолвится |
| PFM9 Normal-pattern maturity | Каждый паттерн — полноценный E.8, не скелет | **PASS** | 6 паттернов, каждый recognition→принцип(SoTA)→инстанциация→CE[A.11]→анти-паттерн[E.8]→conformance→связи. Не skeleton-carrier |
| PFM10 Access-currentness boundary | Skill/MCP access-карьер экспонирует edition/refresh | **n.a.** | У пакета нет skill-pack/MCP access-карьера; `assets/` пуст. Причина зафиксирована |
| PFM11 Carrier structure-account | Структурный отчёт: для кого, что на переднем плане, что огрублено, куда возврат | **PASS** | Структурный отчёт в шапке DPF.md — полный (foregrounded / deliberately coarsened / honest status / return-to) |

**Итог подпрохода:** 9 PASS, 1 n.a., **1 FAIL (PFM7, repairable)**. FAIL понижает D5/D9 в сторону
«soft-4», но не ниже пола сам по себе (слоение references↔carrier в остальном чистое).

---

## 2. Таблица координат D1–D11 (E.4.DPF.DA:4.2/4.3) — пол = 4 (reliance-bearing, `architect`)

> Заявленное использование — reliance-bearing DPF для роли `architect` (проектирует реальные
> многопоточные клиенты по этому пакету) → пол 4 (E.4.DPF.DA:4.1). Floor-3-лицензия («fast seed /
> exploratory») НЕ применяется: это полный 6-фазный авторинг, заявленный как опорный. Средним баллом
> паттернов статус НЕ подменяется (CC-DPFDA.4).

| Коорд. | Знач. | Почему не выше И не ниже | Evidence-locus | Repair / no-proposal |
|--------|:----:|--------------------------|----------------|----------------------|
| **D1** DomainScope&Use | **4** | Bounded context, reader, first-use, non-use boundary — восстановимы и остры (4 явных NOT). Не 5: §0.2 — backpressure/start-timing заявлены в охвате, но паттернами не выданы → охват не полностью реплицируем. Не 3: границы сформулированы точно, sibling-boundary назван | §1 Context; scope.md; §9 scope_boundary | Закрыть §0.2 (добавить паттерны ИЛИ сузить bounded context) |
| **D2** DidacticEntry | **4** | ToC patterns-first, структурный отчёт с «первой задачей», паттерны самодостаточны. Не 5: часть входа зашумлена process-трекингом (PFM7). Не 3: adoption дёшев и не-магичен | Структурный отчёт; ToC; §4 | Убрать фаза-трекинг из носителя (PFM7-repair) |
| **D3** ScalableFormality | **4** | Путь от plain-guidance к записям/evidence/refresh стадирован (паттерны→references→refresh-триггеры→named repair-шаги). Не 5: assurance-путь назван, но не пройден (web-repair не взят). Не 3: стадии явные | §11; §9 pending Phase-6 | — (проверено: стадии присутствуют) |
| **D4** CoreDependency&Boundary | **4** | Зависит от FPF Core/метода, не переопределяет Core, sibling-DPF отграничен, обратной зависимости нет (PFM4). Не 5: нет явного Core-amendment-кандидата (и не нужен). Не 3: направление зависимости чистое | §9 Relations; PFM4/PFM8 | — (no-proposal: направление корректно) |
| **D5** PackageFormLayering | **4** | references (scope/sota/theses/source-pack) ↔ DPF.md разделены; паттерны до карт; провенанс/качество вне носителя. Не 5: PFM7-residue (process-run state в носителе) снижает чистоту слоения. Не 3: локусы findable и достижимы | §Artifacts; references/*; PFM7 FAIL | PFM7-repair: вынести фаза-трекинг в этот файл |
| **D6** DomainLexicon | **4** | 9 терминов с определением и «Is not» (blocked overread), кандидаты в glossary честно НЕ мигрированы (файла нет). Не 5: owner/turn не сведён к одному каноническому термину (сам помечен provisional). Не 3: термины годны к использованию | §8 Names; source-pack open-q #4 | Свести owner↔turn при стабилизации (мелко) |
| **D7** PracticeUtility | **4** | 6 паттернов решают распознаваемые задачи проектирования + 10 failure modes + 5-пунктовый ревью-чек-лист; не таксономия (§8 явно вторичен). Не 5: одна обещанная задача (backpressure-дизайн) не решена (§0.2). Не 3: паттерны реально меняют действие | §4; §6; §7 | Добавить backpressure-паттерн ИЛИ вынести из охвата (§0.2) |
| **D8** HeterogeneousCase | **4** | HC-1 (Kafka pinned) / HC-2 (Android GUI, out-of-networking + сосед-owner) / HC-3 (Redis server-side) закрывают 3 разных оси D8-риска, включая границу-к-соседу. Не 5: все три `worked-evidence pending` — не исполнены, литературные transfer-probes. Не 3: пробы гетерогенны и показывают work/fail/сосед честно | §10; selection rationale | Исполнить хотя бы один HC как факт (web/эксперимент) при возврате доступа |
| **D9** EditionState&Currentness | **4** | Состояние edition/currentness ПОЛНОСТЬЮ явно и восстановимо: читатель точно знает версию, что за source-state её держит (`pretrain recall`), что её меняет (web-repair триггер). Именно транспарентность даёт 4. Не 5: PFM7-residue + фактическая свежесть слабая (13/15 источников web-pending). Не 3: state явен и recoverable — это сильная сторона | §2 Currentness; §11; frontmatter fpf_edition; refresh-триггеры | PFM7-repair; web-repair поднимет фактическую свежесть |
| **D10** Improvement&Refresh | **4** | Refresh-триггеры конкретны (изменение кода репо → re-verify line-цитат; FPF-Spec change; sibling reaches Phase 5; web-доступ вернулся), below-floor даёт repair-строки, reopen-условия named. Не 5: телеметрия использования/E.23-петля не заведена. Не 3: маршруты конкретны, не театр | §11 Refresh triggers; §9 pending | — (проверено: маршруты конкретны) |
| **D11** DomainSoTAAlignment | **3** ⚠ | **Ниже пола.** ЗА 4: источники реально дисциплинируют контент, не bibliography-theatre (Redis-нюанс→CE5; kombu-фальсификация→CE2/P2; RabbitMQ-split→P3; Kafka close(timeout)→P4) — CC-DPFDA.5 удовлетворён по существу. **Почему НЕ 4 для reliance-bearing:** ВЕСЬ внешний литературный базис (S1–S13) — `pretrain recall, не верифицирован`; ни один внешний источник не подтверждён этим прогоном. **Решающая улика:** единственный несущий claim, реально проверенный (T2-C4 kombu self-pipe), оказался ФАЛЬСИФИЦИРОВАН — прямое внутрипакетное доказательство, что recall ненадёжен ровно на той зернистости, от которой зависят паттерны (несколько непроверенных claim'ов — несущие: RabbitMQ-пулы, Kafka-buffer-loss, Redis-io-threads-scope). Пол-4 «current SoTA disciplines content» для опоры НЕ заслужен, пока SoTA неподтверждён и здесь же продемонстрированно ошибаем. Почему НЕ 2: дисциплина реальна, лимиты+repair явны = locallyUsableWithVisibleLimits | §2 Claim status; §11 gaps; theses §5 Repair register (T2-C4 falsified); source-pack open-q #1; Carrier note | **Наименьший repair:** (а) прогнать web-верификацию S1–S13 → поднять trust-cue до verified; ИЛИ (б) `architect`/customer формально сузить declaredUse до bounded/exploratory (пол 3) — тогда пакет admissible-at-floor-3 |

**Свод:** 10 координат ≥ 4; **D11 = 3 ниже пола 4**. Ровно одна координата ниже пола — точечный,
именованный дефицит, не системный развал.

---

## 3. Вердикт CC-DPF.1–9 (E.4.DPF:7, построчно)

> Присутствие секций ≠ адекватность (Паттерн 4 / error №4): CC-DPF даёт «секции конформны», статус
> выносится по D1–D11 отдельно (см. §4).

| CC | Условие | Вердикт |
|----|---------|---------|
| CC-DPF.1 Context declared | Bounded context/reader/first-use/non-use — §1 | **PASS** |
| CC-DPF.2 Source pack present | `source-pack.md` (19 строк, adopted/rejected+причина, claim-status, currentness) | **PASS** |
| CC-DPF.3 Architecture decision present | PFAD свёрнут в структурный отчёт + §1 non-use + §9 Relations; отдельный DRR не создан — пропорционально одиночной компетенции (E.4.DPF:4) | **PASS** |
| CC-DPF.4 Names prepared | §8, 9 терминов + provisional, честно не мигрированы в отсутствующий glossary | **PASS** |
| CC-DPF.5 Carriers admitted | Admission через recall с явным trust-cue на claim; 2 file-read отделены от recall; FPF live-grep. (Мягкая нота: «recall как carrier» — растянутое, но честно помеченное C.35-подобное допущение) | **PASS** |
| CC-DPF.6 Patterns through E.8 | 6 паттернов, полный E.8-блок каждый (≥4 гейт с запасом) | **PASS** |
| CC-DPF.7 Quality & refresh present | §11: что прогнано / что нет (Phase 6) / gaps / refresh-триггеры / review_due | **PASS** |
| CC-DPF.8 Structure-account visible | Структурный отчёт в шапке — полный | **PASS** |
| CC-DPF.9 Problem-solving primacy | §4 задачи проектирования, §6 10 блокируемых провалов, §7 15 source-grounded ходов; не онтология-каталог | **PASS** |

**CC-DPF.1–9: PASS (9/9).** Секции конформны и содержательны.

---

## 4. Статус пакета (ровно один — E.4.DPF.DA:4.5)

### `repairBeforeDPFUse`

**Обоснование.** CC-DPF.1–9 PASS, PFM 9/1 n.a./1 fail(repairable), 10 из 11 координат ≥ пола. Но
**D11 = 3 ниже пола 4** для заявленного reliance-bearing использования: литературный базис целиком
`pretrain recall, не верифицирован`, и внутрипакетная фальсификация T2-C4 доказывает ненадёжность
recall на несущей зернистости. Это НЕ `seedOnly` — пакет далеко за заготовкой (полный 6-фазный
авторинг, role-separated фазы, 6 зрелых E.8-паттернов, NQD-анти-тезисы, отделённые контрпримеры,
гетерогенные кейсы, refresh-маршруты, две реальные file-read-верификации + одна фальсификация).
Дефицит точечный и нанесён на карту; путь к admissible — короткий и named. Поэтому именно
`repairBeforeDPFUse`, а не `seedOnly` (который занизил бы объём реально сделанного) и не
`admissibleForDeclaredDPFUse` (который переоценил бы неподтверждённый базис для опоры — прямое
нарушение CC-DPFDA.8 и анти-sycophancy дисциплины; сам пакет своими §2/§11/Carrier-note просит НЕ
опираться до web-repair).

> **Знание-распространение (Паттерн 6).** Даже будь пакет «чист», этот разбор — inspectable-карта для
> следующих ролей: facilitator (гейт), architect (владелец repair), keeper (следующая сборка). Дефект
> не найден «пустым»: найден один floor-дефект (D11) + одна форменная (PFM7) + две coverage-gap (§0.2).

### Наименьшие правки (по возрастанию цены)

1. **[дёшево, форменное — снимает PFM7, лечит D5/D9]** Вынести из `DPF.md` фаза-трекинг прогона
   (`research_mode:` frontmatter; «this run» / «Phase 6 has not run» / «this is a Phase 4–5 assembly» /
   «assembler, this run») в этот `critic-review.md`. Оставить в носителе: per-claim trust-cue
   `pretrain recall` (durable, нужен читателю) + одну финальную conformance-строку. Не трогать смысл.
2. **[дёшево, охват — лечит D1/D7 §0.2]** Явно решить судьбу **write-backpressure** и
   **start-timing/lifecycle-owner/naming**: либо добавить тезис+паттерн на каждую, либо сузить bounded
   context/non-use boundary, убрав их из обещанного охвата. Сейчас глоссарий/scope обещают больше, чем
   паттерны выдают.
3. **[решающее для D11 — снимает статус до admissible]** ОДНО из двух:
   - (а) прогнать web-верификацию несущих S1–S13 (POSA2, pika/RabbitMQ/Kafka, libuv/asyncio/Redis,
     Qt/Android) против живых источников → поднять trust-cue до `verified`, зафиксировать как repair-шаг;
   **или**
   - (б) `architect`/customer формально фиксируют declaredUse = bounded/exploratory (не reliance-bearing),
     при котором пол = 3 легитимен (E.4.DPF.DA:4.1: non-use + missing evidence + next repair явны — они
     явны) → пакет становится admissible-at-floor-3.
4. **[обогащение, не блокирует]** При возврате доступа: исполнить ≥1 из HC-1..3 как факт (снимает
   `worked-evidence pending`, поднимает D8 к 5); рассмотреть Go channel-ownership как инстанс T3 (D11/D8).

### Reopen-условия
- Взят repair-шаг 3(а) [web-verify S1–S13] или 3(б) [re-scope declaredUse] → **переоценить D11**,
  при D11≥4 и снятом PFM7 статус переходит в `admissibleForDeclaredDPFUse` (независимым guardian-проходом).
- Изменение FPF-Spec E.4.DPF/E.4.DPF.DA → пересмотреть форму.
- Изменение reconnect/teardown-кода репозитория → re-verify пять line-цитат §4 прямым чтением.

---

## 5. Гейт (для оркестратора)
- **CC-DPF.1–9:** PASS (9/9).
- **Статус пакета:** `repairBeforeDPFUse` (D11=3 ниже пола 4).
- **gate_passed = false** (гейт требует И CC-DPF PASS, И `admissibleForDeclaredDPFUse`; второе не
  выполнено).
- **Conformance-строка в `DPF.md` НЕ дописана** — дописывается только при заслуженном
  `admissibleForDeclaredDPFUse` (apply-prompt Mode B / задание). Самозаявленная строка авторов
  «seedOnly — Phase 6 not yet run» оставлена как есть; настоящий файл её уточняет до `repairBeforeDPFUse`.
