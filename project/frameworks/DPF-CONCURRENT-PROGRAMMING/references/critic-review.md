# Critic Review — DPF-CONCURRENT-PROGRAMMING (Фаза 6: completeness-critic + E.4.DPF.DA)

> Роль: `DPF-ADVERSARIAL-REVIEW` (owner guardian), Режим B — критика собранного пакета.
> Вход: `DPF.md` + `references/{scope,sota-research,theses-antitheses,source-pack}.md` +
> сверка worked-evidence с `src/kombu_pyamqp_threadsafe/__init__.py`.
> FPF читан живьём: E.4.DPF §66066–66504, E.4.DPF.DA §66506–66757 (D1–D11 §66594–66607,
> PFM1–PFM11 §66622–66634, статусы §66660–66668, CC-DPFDA §66695–66705, анти-паттерны §66709–66723)
> — Grep+Read по `~/.claude/knowledge/fpf/FPF-Spec.md`, не по памяти.
> Дата прогона: **2026-07-14**. Режим ресёрча пакета: pretrain-only (решение заказчика).
> **Role-separation-gate (Паттерн 1):** этот критик — отдельный агент/сессия от сборки Фаз 0–5;
> нарушения разделения ролей нет.

---

## 0. Итог одной строкой

Пакет — **образцовая заготовка (seedOnly)**: полный скелет, 6 обогащённых паттернов сверх пола
≥4, worked-evidence дословно и верно процитирован из реального кода (спот-чек 6 цитат — 0 битых
атрибуций, стоп-находок нет), честный структурный отчёт, честное раскрытие режима и честный
самостатус. НО **НЕ `admissibleForDeclaredDPFUse`**: 4 координаты ниже пола 4 (D5, D8, D9, D11),
корень — mode-wide неверифицированный провенанс (pretrain-only) + одна несущая частность без
crisp-источника (A4/TOCTOU) + процессный след в носителе (PFM7). Гейт Фазы 6 НЕ пройден.

---

## 1. Completeness-критика (что упущено / что оспаривается) — ≥3 значимых концерна (Паттерн 5, anti-sycophancy)

Дисциплина: «вероятно И значимо», severity как есть; «автор старался» и pretrain-режим — не
основание смягчать (E.4.DPF.DA:6 local-excellence laundering; CC-DPFDA.8 seed honest).

### C-1 (значимый). Несущая частность A4/TOCTOU держится на opinion-grade провенансе
TOCTOU/check-then-act несёт вес в Паттерне 1 (инстанциация + conformance), типовой ошибке №5 и
термине §8, НО в `sota-research.md`/`source-pack.md` §Открытые вопросы п.3 сам пакет признаёт: у A4
нет единичного crisp «источник+дата» («security-литература, общеупотребительна, в паре с S1»);
Netzer/Miller (S5) покрывает разделение data race ⊋ race condition, но НЕ термин TOCTOU. По
Falsifiability-gate/A.10 несущий claim без источника+даты = пограничный `opinion`. Пакет честно
это отмечает — но для reliance-использования дефект остаётся. **Понижает D11.**
*Repair:* привязать TOCTOU к первоисточнику (напр. Bishop/Dilger 1996 «Checking for Race Conditions
in File Accesses», или McPhee 1974 TOCTTOU) при веб-верификации, либо явно оформить как
«durable-определение без единого первоисточника» с фиксацией в §7.

### C-2 (значимый). Memory-model / visibility как класс — не покрыт для free-threaded будущего, которое пакет сам выдвигает на передний план
Пакет опирается на B5 («GIL сериализует bytecode → нет visibility reordering в CPython») и явно
выносит PEP 703/free-threaded в самое молодое, decay-рисковое знание (Паттерн 2 анти-паттерн,
repair-приоритет №1). Но под free-threaded сборкой именно **memory visibility / ordering**
(acquire-release, барьеры, happens-before без GIL) становится ЖИВЫМ классом — а среди 6 паттернов
и claim'ов A1–D4 НЕТ ни одного, покрывающего visibility/ordering-семантику как самостоятельную
тему (Lamport happens-before S7 сознательно вынесен за non-use boundary; Herlihy S6 упомянут только
как «фон»). Пакет трактует free-threaded как «переаудит тем же чек-листом», хотя free-threaded
вводит НОВЫЙ класс, которого текущие паттерны не адресуют. Это упущенная тензия/традиция (модель
памяти как first-class концерн), значимая именно потому, что пакет сам акцентирует PEP 703.
**Понижает D11 и D8 (нет кейса под free-threaded).**
*Repair:* добавить тезис/claim о memory-visibility под free-threaded (что happens-before теперь
надо устанавливать явно, а не наследовать от GIL) при следующем расширении; сейчас — зафиксировать
как известный пробел scope, не как покрытое.

### C-3 (значимый). Вся worked-evidence и все 3 разнородных кейса — из одного файла одного проекта
D8 heterogeneity номинальна: HC-1 (`ChannelCoordinator`), HC-2 (`_connection_dispatch_lock`
non-blocking) и мотивирующий пример (`DrainGuard`) — три точки координации ОДНОГО модуля
`__init__.py`; HC-3 (`DPF-DEDICATED-IO-THREAD`) — пустой каталог, явно principle-grounded без
worked-evidence. Для `kind: Domain Principle Framework`, заявляющего применимость за пределами kombu
(«любой похожий домен: пул соединений, кэш, буфер очереди», §1), НЕТ ни одной worked-инстанциации
вне этого файла и ни одной вариации reader-role. Обобщение утверждается, но не показано (E.4.DPF.DA
D8: «diverse enough domain cases, reader roles, or local situations»). **Понижает D8.**
*Repair:* добавить хотя бы один worked-кейс из другого домена (даже из стандартной библиотеки —
напр. `logging` handlers lock, `concurrent.futures` executor shutdown) или явно сузить claim
применимости до «в пределах паттернов доступа к разделяемому сокет-подобному ресурсу».

### C-4 (значимый, корневой). Провенанс mode-wide неверифицирован — source-basis seed-grade
Каждый anchor S1–S21 несёт «pretrain recall, не верифицирован». Recall-consistency-чек (§0.1
theses-antitheses) проверяет ВНУТРЕННЮЮ согласованность, не внешний мир — пакет корректно говорит,
что это не снимает unverified-статус. Несколько несущих claim'ов явно decay-рисковы (B4/PEP 703
статус развёртывания; AI1/AI2 перенос эмпирики 2021–22 на современные модели; S19/D4 «для pure
Python нет TSan» — могло устареть). Для пола 4 D11 требует, чтобы источники дисциплинировали пакет
(они дисциплинируют — контент реально source-grounded, не декоративен, не authority-by-citation),
НО evidence-anchor'ы сами не верифицированы. Это фундаментально seed-grade source-basis.
**Понижает D11; корень статуса `seedOnly`.**
*Repair:* веб-верификация минимум B4 (release notes CPython/PEP 703), AI1/AI2, S19/D4, A4 — явный
именованный repair-шаг, невыполнимый в pretrain-only режиме этого прогона.

### C-5 (форменный, легко чинится). Процессный след в носителе (PFM7)
`status: "stage-0"` во frontmatter — процессная фаза в идентичности пакета: ровно тот класс
дефекта D9/PFM7, который пакет `DPF-ADVERSARIAL-REVIEW` ловил у себя (HC-4) и у DPF-EBPF (HC-2)
как `status: stage-0` → `maturity`/`edition`. Дополнительно §11 и Conformance содержат заметную
run-narrative («этот прогон закрывает Фазы 0–5», «НЕ выполнена в этом прогоне», «задание было
ограничено»), которую метод (PFM7, разделение носителей) относит в `references/`, не в
пользовательский DPF.md. Честный самостатус — durable-контент и допустим одной строкой; но
`status: stage-0` + phase-completion-нарратив — процессный остаток. **Понижает D5 и D9.**
*Repair:* заменить `status: "stage-0"` на `maturity: "seed"` + `edition: "0.1"`; сжать §11/Conformance
run-narrative до durable-attestation, ход прогона оставить только в этом `critic-review.md`.

### Мелочь (не блокирует). Имприцизность диапазона строк HC-1
DPF §10 цитирует `begin_teardown()` как `__init__.py:442-459`; фактически строки 442–459 — это
class `ChannelCoordinator` + его docstring (цитата «Mark and count share one lock… reliably rejected
rather than slipping in» дословно верна, строки 448–449), а сам метод `begin_teardown` — строка 484.
Атрибуция НЕ битая (процитированный текст реально там), диапазон слегка неточен. No-proposal нужен
только косметический.

### Положительное (Паттерн 6 — knowledge distribution; чистота ≠ пустое ревью)
- Worked-evidence **верен дословно**: спот-чек 6 несущих цитат против `__init__.py` — все совпали
  (`change_owner` 127–136; `wait`-комментарий «workaround… through ChannelPool» 138–145;
  `start_drain` «should be ALWAYS last… to prevent race condition» 380–381; `_basic_publish`
  «concurrent teardown can null self.connection mid-publish… not retried by kombu» 230–231;
  `ChannelCoordinator` docstring 448–449; `_connection_dispatch_lock.acquire(blocking=False)` 649;
  `finish_drain` «can not finish drain started by other thread» 402). **0 стоп-находок.**
- 4 традиции + ИИ-срез (FamilyCoverageFloorK=3 пройден), каждый тезис со scope+NQD≥3+тип связи,
  6 контрпримеров отдельно от анти-паттернов, 11 типовых ошибок (3 ИИ).
- Честность режима образцовая: unverified trust-cue не скрыт fluency; пакет сам НЕ повышает себя
  до admissible и явно называет, что даже после Фазы 6 нужна веб-верификация (F-8). Это прямое
  соблюдение CC-DPFDA.8 и собственного anti-fluency.

---

## 2. Подпроход формы PFM1–PFM11 (E.4.DPF.DA:4.3a) — до значений D

| PFM | Проверка | Дисп. | Обоснование |
|-----|----------|-------|-------------|
| PFM1 Front-door order | ToC/readme/preface до паттернов | **pass** | Структурный отчёт носителя + Оглавление предшествуют §4; читатель выбирает паттерн по симптому, не читая аппарат первым |
| PFM2 Pattern-language primacy | паттерны — главный язык | **pass** | §4 паттерны первые; полный BridgeMatrix/NQD вынесены в references; тяжёлые таблицы после паттернов |
| PFM3 Map discoverability | карты достижимы из work-триггера | **pass** | §5 связи, §6 ошибки, §7 SoTA — из Оглавления; references-ссылки живые |
| PFM4 Dependency direction | Core не зависит от DPF | **pass** | только grounded_in/uses к FPF; обратной зависимости нет |
| PFM5 Pub/access-carrier boundary | носитель ≠ архитектура/провенанс | **pass с оговоркой** | процессное состояние в references; но `status: stage-0` во frontmatter — граничит с PFM7 |
| PFM6 Public naming | доменное имя, без process-slang | **pass с оговоркой** | заголовок предметный («Конкурентное программирование…»); НО frontmatter `status: stage-0` — process-phase в идентичности (workspace-артефакт, терпимо, но лучше maturity/edition) |
| PFM7 Development-state absence | нет draft/DRR/run-residue | **fail (минорный)** | `status: stage-0` + run-narrative «в этом прогоне»/phase-completion в §11 и Conformance — процессный остаток в пользовательском носителе → D5/D9 |
| PFM8 Cross-DPF relation discipline | ссылки на др. DPF типизированы, blocked reading | **pass** | `DPF-DEDICATED-IO-THREAD` как peer, пустой каталог, явно не слит содержательно |
| PFM9 Normal-pattern maturity | паттерны E.8+E.21, не скелет | **pass** | 6 паттернов полностью развёрнуты (recognition→принцип→worked slice→контрпример→анти-паттерн→conformance→связи); seed-статус — из-за провенанса, не из-за тел паттернов; PFM9 разрешает seed при status seedOnly |
| PFM10 Access-currentness | skill/MCP edition-refs | **n.a.** | у этого DPF нет собственного skill/MCP access-carrier (причина: доступ через общий dpf-authoring, не отдельный endpoint) |
| PFM11 Structure-account | readme даёт structure-account | **pass** | Структурный отчёт: для-кого/на-переднем-плане/огрублено-опущено/денора-отбора/куда-возврат — присутствует |

**Итог подпрохода:** PFM7 **fail** (минорный, легко чинится) → тянет D5/D9; PFM5/PFM6 pass с той же
оговоркой; PFM10 n.a.; остальные pass. Тела паттернов сильны (PFM9 pass) — но по E.4.DPF.DA:4.3a
провал формы понижает координату независимо от качества тел.

---

## 3. Таблица координат D1–D11 (E.4.DPF.DA:4.2/4.3) — пол = 4 (reliance-bearing DPF use)

| Координата | Знач. | ShortRationale (почему не выше И не ниже) | EvidenceLocus | Repair / no-proposal |
|-----------|:---:|---|---|---|
| **D1** DomainScopeAndUse | **4** | Bounded context, reader, first use, non-use boundary — все явны и crisp (не asyncio/multiprocessing/distributed/AMQP-proto). Не 5: не «replayable across cases» — обобщение за kombu заявлено, не показано (см. D8). Не 3: scope полностью восстановим, non-use boundary образцовая | §1; scope.md | no-proposal (проверено: 4 пункта присутствуют, non-use сильна). Reopen при появлении `domain.md` |
| **D2** DidacticEntry | **4** | ToC + структурный отчёт + вход-по-симптому (§4) + worked-код делают adoption дешёвым и не-магическим; support-карты из work-триггеров, не front-loaded. Не 5: нет skill-entry/quick-card (assets/ пуст, §Артефакты TBD). Не 3: первый рабочий результат достижим без FPF-знаний | Структурный отчёт; Оглавление; §4 | no-proposal; опц. улучшение — AI-review чек-лист-карточка (assets/), явно отложена |
| **D3** ScalableFormality | **4** | Стадии есть: plain-паттерны → references (typed records/source pins) → §11 route к Фазе 6/evidence-upgrade. Не 5: путь к assurance назван, но не пройден (Фаза 6 не выполнена). Не 3: переход к сильным записям не требует переписывания | §11; references/* | no-proposal |
| **D4** CoreDependency | **4** | Зависит от FPF Core (grounded_in), domain-знание внутри DPF, локальные термины не переопределяют Core, обратной зависимости нет. Не 5: нет явных Core-amendment-кандидатов (их и не требуется). Не 3: граница Core/domain чистая | frontmatter grounded_in; §9 Relations; PFM4 | no-proposal |
| **D5** PackageFormLayering | **3** | Паттерны/references/relations/source-packs в основном разделены (PFM1–3 pass), НО PFM7 fail: `status: stage-0` frontmatter + run-narrative в §11/Conformance — процессный след в носителе. Не 4: процессное состояние протекло в пользовательский carrier. Не 2: разделение по большей части соблюдено, дефект локальный | frontmatter `status`; §11; Conformance; PFM7 | **repair:** `status:stage-0`→`maturity:seed`+`edition:0.1`; run-narrative → в этот critic-review, в DPF.md durable-строка |
| **D6** DomainLexicon | **4** | §8: 10 терминов с kind/определением/«не является»; provisional явно помечены; glossary не заполнен, но честно оговорено (файла нет). Не 5: термины не прошли F.18 name-card полностью, «guarded suspension» RU-калька не решена. Не 3: термины settled для использования | §8; F.18 | no-proposal (glossary-перенос — отдельный шаг без поручения) |
| **D7** PracticeUtility | **4** | Паттерны решают узнаваемые задачи (классификация гонки, выбор примитива, ревью) с SoTA-ходами + анти-паттернами + worked cases из РЕАЛЬНОГО кода (верифицировано дословно). Не 5: провенанс-оговорки ограничивают «SoTA-informed» до unverified. Не 3: явно не taxonomy-only — CC-DPF.9 выполнен содержательно | §4; §6; §7; спот-чек кода | no-proposal |
| **D8** HeterogeneousCase | **3** | HC-1/HC-2 — реально разные формы координации, дословно из кода (сила); НО все 3 кейса — из ОДНОГО файла одного проекта, HC-3 пуст/гипотетичен, нет reader-role diversity, нет worked-evidence вне `__init__.py` при заявленной применимости за kombu. Не 4: разнородность номинальна для DPF-уровня. Не 2: 2 кейса genuinely форсят разные паттерны | §10 HC-1/2/3; C-3 | **repair:** добавить worked-кейс из другого домена (stdlib `logging`/`concurrent.futures`) ИЛИ сузить claim применимости |
| **D9** EditionState | **3** | `fpf_edition` документирован и live-grep-сверен (сила); НО currentness domain-источников явно НЕ верифицирована (pretrain-only), decay-риск на B4/AI/S19 назван, и `status: stage-0` — process-phase во frontmatter (PFM7). Не 4: source-currentness ниже reliance-порога + process-residue. Не 2: edition-state FPF explicit, decay честно помечен | frontmatter; §2 Currentness; §11; PFM7 | **repair:** веб-сверка B4/AI/S19 currentness; `status`→`maturity/edition` |
| **D10** ImprovementRefresh | **4** | 7 конкретных refresh-триггеров + 6 открытых provenance-вопросов с «какой evidence нужен» + smallest-repair routes (repair-приоритеты №1/№2). Не 5: часть routes — веб-верификация, невыполнимая в режиме. Не 3: reopen-условия конкретны, не process-theatre | §11 Refresh triggers/Open assumptions | no-proposal (route-качество высокое) |
| **D11** DomainSoTAAlignment | **3** | Источники РЕАЛЬНО дисциплинируют пакет (контент source-grounded, BridgeMatrix явные потери, НЕ bibliography/authority-by-citation — тянет вверх от 2); НО каждый anchor unverified pretrain recall, A4/TOCTOU без crisp-источника (C-1), memory-model под free-threaded не покрыта (C-2). Не 4: source-basis seed-grade, несущая частность opinion-grade. Не 2: источники меняют селекцию/границы, не декоративны | §7 SoTA-Echoing; source-pack §1; C-1/C-2/C-4 | **repair:** веб-верификация несущих anchor'ов; привязка A4; тезис о visibility под free-threaded |

**Координаты ниже пола 4:** D5=3, D8=3, D9=3, D11=3 (четыре). Средним баллом сильных паттернов
(E.21) НЕ подменяется — CC-DPFDA.4 удержан: тела паттернов сильны, но source-basis/form/heterogeneity
тянут пакет ниже пола независимо.

---

## 4. Вердикт CC-DPF.1–9 (E.4.DPF:7, построчно)

Присутствие секций проверено содержательно (не только наличие заголовка — анти-паттерн №4 «зелёный
чек-лист»); статус пакета выносится по D1–D11, НЕ по этому чек-листу.

- **CC-DPF.1** Context declared — **PASS** (§1: context/reader/first-use/non-use, зеркалит scope.md).
- **CC-DPF.2** Source pack present — **PASS** (source-pack.md: 21 источник, adopted/rejected+причина, claim-status, currentness).
- **CC-DPF.3** Architecture decision present — **PASS** (структурный отчёт + non-use §1 + §9 Relations; purpose/pattern-split/dependency-boundary восстановимы).
- **CC-DPF.4** Names prepared — **PASS** (§8, 10 терминов, provisional помечены; glossary-перенос честно отложен).
- **CC-DPF.5** Carriers admitted — **PASS** (Carrier note: pretrain-источники + FPF live-grep + чтение кода отмечены; admission честен).
- **CC-DPF.6** Patterns drafted through E.8 — **PASS** (6 паттернов сверх пола ≥4, полная форма E.8 на каждый).
- **CC-DPF.7** Quality & refresh routes present — **PASS** (§11: критерии + 7 триггеров + 6 открытых вопросов).
- **CC-DPF.8** Структурный отчёт в шапке — **PASS** (для-кого/передний-план/огрублено/денора/возврат).
- **CC-DPF.9** Примат решения задач — **PASS** (§4/§6/§7: задачи домена, блокируемые провалы, SoTA-ходы; не ontology-only).

**CC-DPF.1–9: все PASS.** НО (Паттерн 4 / анти-паттерн №4): присутствие секций ≠ адекватность.
Статус — по D1–D11.

---

## 5. Статус пакета (E.4.DPF.DA:4.5 — ровно один)

### `seedOnly`

**Обоснование.** Пакет — genuinely полезная, качественная заготовка (полный скелет, 6 зрелых
паттернов, дословно верный worked-evidence), но НЕ reliance-bearing: 4 координаты ниже пола 4
(D5/D8/D9/D11). Корневая причина — mode-wide неверифицированный провенанс (pretrain-only, явное
решение заказчика), делающий source-basis seed-grade независимо от косметических правок; вторично —
процессный след формы (PFM7) и номинальная разнородность (D8). Это совпадает с honest self-status
пакета (`status: stage-0` = seedOnly в терминах CC-DPFDA.8) и его собственным заявлением, что даже
после Фазы 6 admissible недостижим без веб-верификации. Seed НЕ повышается до опорного без evidence
(CC-DPFDA.8 / анти-паттерн «Seed promotion»).

> Примечание о выборе между `seedOnly` и `repairBeforeDPFUse`: формально 4 координаты ниже пола →
> `repairBeforeDPFUse` для reliance-use. Но корень (unverified source-basis) — seed-grade по природе,
> не устраним косметикой; `seedOnly` вернее называет род состояния. Путь: сначала PFM7-правки
> (дёшево), затем веб-верификация + D8/D11-репейр → тогда переоценка на `admissibleForDeclaredDPFUse`.

### Наименьшие правки (по возрастанию цены)

1. **(тривиально)** `status: "stage-0"` → `maturity: "seed"` + `edition: "0.1"` во frontmatter; run-narrative §11/Conformance сжать до durable-строки, ход прогона — в этот файл. → чинит PFM7, поднимает D5/D9.
2. **(дёшево)** Привязать A4/TOCTOU к первоисточнику ИЛИ явно оформить «durable-определение без единого первоисточника» в §7. → C-1, поднимает D11.
3. **(средне)** Добавить 1 worked-кейс из другого домена (stdlib) ИЛИ сузить claim применимости в §1. → C-3, поднимает D8.
4. **(средне)** Зафиксировать пробел memory-visibility под free-threaded как известный (тезис/claim при расширении). → C-2, поднимает D11/D8.
5. **(дорого, вне режима)** Веб-верификация несущих anchor'ов B4/PEP 703, AI1/AI2, S19/D4, A4. → C-4, корневой подъём D11/D9. Невыполнимо в pretrain-only режиме этого прогона — именованный repair-шаг G.11.

---

## 6. Гейт Фазы 6

- CC-DPF.1–9: **PASS** (все 9).
- Статус пакета: **`seedOnly`** (НЕ `admissibleForDeclaredDPFUse`).
- **GATE НЕ ПРОЙДЕН** (gate требует CC-DPF.1–9 PASS **И** admissible). Строка conformance
  `admissibleForDeclaredDPFUse` в `DPF.md` **НЕ дописывается** — статус не заслужен. Существующая
  честная строка пакета (`seedOnly`) остаётся как есть.

Ревью зафиксировано как inspectable-артефакт (Паттерн 6: ценно и при отсутствии критичных дефектов —
здесь дефекты есть и названы). Следующая роль (architect-owner / facilitator-гейт) читает §5 как
карту наименьших правок.
