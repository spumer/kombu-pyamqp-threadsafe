# Critic Review — DPF-CONCURRENT-PROGRAMMING (r2: повторная проверка после ремонта R2-2/R2-3, режим C)

> Роль: `DPF-ADVERSARIAL-REVIEW` (owner guardian), Режим B — критика собранного пакета,
> переоценка по E.4.DPF.DA после ремонта, следующего за `critic-review-2026-07-14-r1.md`.
> Вход: `DPF.md` (883 строки) + `references/{scope,sota-research,theses-antitheses,source-pack,
> critic-review,critic-review-2026-07-14-r1,quality-record-2026-07-14,web-verification-2026-07-14}.md`
> + сверка worked-evidence с `src/kombu_pyamqp_threadsafe/__init__.py`.
> FPF читан живьём (Grep+Read по `~/.claude/knowledge/fpf/FPF-Spec.md`, не по памяти):
> E.4.DPF §66066–66504; E.4.DPF.DA §66506–66757 — шкала §66575 (пол 4 §66586), координаты D1–D11
> §66588–66607, форма-строка §66608, **PFM1–PFM11 §66618–66634** (PFM5 §66628, PFM7 §66630),
> правило «form failure lowers coordinate» §66636, статусы §66658–66668, anti-patterns §66707
> («Process-state leakage» §66721), Bias third drift §66687.
> Дата прогона: **2026-07-14**, r2 (после ремонта R2-2/R2-3 куратора, зафиксированного в
> `web-verification-2026-07-14.md` секция «Круг 2»).
> **Role-separation-gate (Паттерн 1):** этот критик — отдельный агент/сессия от сборки Фаз 0–5, от
> ремонта r1 И от ремонта R2-2/R2-3 (`DPF-KNOWLEDGE-CURATION`); нарушения нет.
> **Anti-sycophancy (Паттерн 5):** ремонт сделан по прошлому repair-списку этого же критика — это НЕ
> основание завышать. Проверено содержательно; **3 web-якоря независимо перепроверены по URL live
> WebFetch** (см. §0.1) — 0 галлюцинаций. Severity как есть.

---

## 0. Итог одной строкой

Ремонт после r1 **закрыл два НЕ-блокирующих пункта (R2-2 wording, R2-3 S8-verify) и НЕ тронул
единственный БЛОКИРУЮЩИЙ (R2-1 / PFM7-residue).** Провенанс-корень, устранённый в r1, остаётся
устранён (независимо перепроверил 3 якоря по URL — PEP 779, threadsafety.html, urllib3#1252 —
подтверждены дословно). Но пользовательский `DPF.md` **по-прежнему первазивно несёт четыре запрещённые
PFM7-категории** (process-run residue, review-status, admission-blocker, handoff) — ремонт вычистил
лишь один заголовочный блок «Ремонт…» и пару локальных меток, оставив нарратив рассеянным по шапке,
§1, §2, Паттерну 2, §7 (SE-13/14 «добавлен 2026-07-14»), §8, §10 (HC-4 «названный критиком C-3»), §11
и Conformance. **D5 остаётся 3.** Более того, сам ремонт R2-2 заявил в `web-verification` «label
ремонта снят одновременно (PFM7-правка того же прохода)» для §8 — но §8 стр.673 всё ещё несёт
change-narrative «было «первоисточник термина», стало «ранняя каноническая работа»»: даже точечная
PFM7-со-правка оказалась неполной.

**Статус: `repairBeforeDPFUse`** (одна координата ниже пола — D5=3), **без изменения рода состояния
vs r1**. Единственный gate-блокер r1 перенесён в r2 нетронутым. **Гейт Фазы 6 НЕ пройден.** Пакет
по-прежнему в **одну дешёвую правку** (вычистить процессный нарратив) от `admissibleForDeclaredDPFUse`
— но эта правка так и не сделана.

---

## 0.1. Независимая перепроверка web-якорей по URL (anti-sycophancy, live WebFetch 2026-07-14)

| Якорь | URL | Что заявлено в DPF/web-verification | Вердикт моего спот-чека (live) |
|---|---|---|---|
| PEP 779 (B4/S11, SE-5, Паттерн 2/7) | peps.python.org/pep-0779 | 3.14 = officially supported non-default; default = отдельный Phase III, горизонт 2028+ | **подтверждён дословно** — «Phase II would make the free-threaded build officially supported but still optional, and phase III would make the free-threaded build the default»; Phase III «left for a future PEP» (не датирован) |
| threadsafety.html (Паттерн 1/7, A4, SE-14) | docs.python.org/3/library/threadsafety.html | free-threaded built-in типы; `if key in d: del d[key]` = NOT atomic (TOCTOU) | **подтверждён дословно** — «documents thread-safety guarantees for built-in types in Python's free-threaded build»; явный блок `# NOT atomic: check-then-act (TOCTOU)` + «To avoid time-of-check to time-of-use (TOCTOU) issues…» |
| urllib3#1252 (HC-4, D8) | github.com/urllib3/urllib3/issues/1252 | PoolManager не thread-safe: pool вытесняется из LRU между check и use — TOCTOU, не data race | **подтверждён дословно** — «A pool is pulled from the cache but within the time it takes for pool._get_conn to be called the PoolManager can potentially evict the ConnectionPool…»; ДРУГОЙ проект/домен реален |

Вывод: **0 галлюцинированных цитат** в моей выборке. Инструментальный слой ремонта (WebFetch/WebSearch)
реален; source-basis-корень, поднятый r1 (D8/D9/D11 3→4), держится независимой проверкой. Это
подтверждается содержательно, не из вежливости.

---

## 1. Что закрыто из прошлого repair-списка (r1), что нет

| # (r1) | Repair-пункт r1 | Целевые коорд. | Статус после ремонта R2-* | Обоснование |
|---|---|---|---|---|
| **R2-1** | **PFM7: вычистить run/mode-C/gate/handoff нарратив из `DPF.md`** | **D5** | **❌ НЕ ЗАКРЫТ (блокер)** | Ремонт вычистил только заголовочный блок «Ремонт 2026-07-14 (круг 1, режим C)» и 2 локальные метки (A4/S8). Остаток — первазивен: шапка стр.27/33, §1 стр.113, §2 стр.148, Паттерн 2 стр.270, §7 SE-10/13/14 стр.640/643/644, §8 стр.673, §10 HC-4 стр.722, §11 стр.755/756/776/780/782, Conformance стр.809/877, финальная строка стр.881. **D5 остаётся 3.** |
| R2-2 | A4/Bishop-Dilger: смягчить «чеканку термина» | D11 (косметика) | **✅ ЗАКРЫТ по существу** | §8 стр.675 теперь «ранняя каноническая работа», без claim «ввела термин»; `sota-research`/`web-verification` синхронизированы. НО (см. R2r-2 ниже) внесено как change-narrative, что само есть PFM7-residue |
| R2-3 | Сверить S8 (GIL-atomicity) по docs.python.org | D11/D7 | **✅ ЗАКРЫТ** | S8 переведён pretrain→verified (Python FAQ URL, дословная сверка списка атомарных/неатомарных операций); trust-cue обновлён обоснованно. S10 (книга за paywall) честно оставлен pretrain |
| R2-4 | D8 reader-role diversity | D8 (no-proposal) | **n/a** | r1 сам пометил no-proposal (reopen при сборке `DPF-DEDICATED-IO-THREAD`); без изменений, ожидаемо |

**Итог:** 2 из 2 НЕ-блокирующих пунктов закрыты; **единственный БЛОКИРУЮЩИЙ (R2-1) не тронут.** Ремонт
сделал более дешёвую работу и обошёл дорогую-по-объёму-но-тривиальную-по-технике чистку носителя. Это
классический whack-a-mole по краям при нетронутом корне формы (E.4.DPF.DA:4.3a).

---

## 2. Значимые концерны r2 (≥3, severity как есть — Паттерн 5)

### R2r-1 (БЛОКИРУЮЩИЙ, перенос R2-1). PFM7: процессный нарратив первазивен в носителе — не уменьшен
Пользовательский `DPF.md` содержит **все четыре** запрещённые PFM7-категории (FPF §66630 + anti-pattern
«Process-state leakage» §66721 + Bias third drift §66687 «review status… copied into user-facing
prose»), рассеянно по всему носителю:

- **process-run residue:** шапка стр.27 «**Режим ресёрча этого прогона (явное решение заказчика):**
  ТОЛЬКО pretrain…»; §2 стр.148 «веб-верификация НЕ выполнена (явное решение заказчика **этого
  прогона**, не забыто, а явно отложено)»; Паттерн 2 стр.270 «Decay-риск… **уточнён ремонтом
  2026-07-14**»; §7 стр.640/643/644 «**уточнено 2026-07-14**», «SE-13 **(добавлен 2026-07-14)**»,
  «SE-14 **(добавлен 2026-07-14)**»; §8 стр.673 «**исправлено по верификации 2026-07-14**: было «X»,
  стало «Y»»; §11 стр.755/756/776/780/782 «✅ **закрыто 2026-07-14**», «✅ **уточнено 2026-07-14**»;
  Carrier note стр.827 «**Дополнение веб-верификацией 2026-07-14:** …эта правка ИСПОЛЬЗОВАЛА
  WebSearch/WebFetch».
- **review-status:** §11 стр.809 (артефакт-строка) «вердикт `seedOnly`/gate не пройден»; финальная
  строка стр.881 «E.4.DPF.DA: **seedOnly**» (одна финальная conformance-строка допустима §66636 — но
  она устарела, см. R2r-3).
- **admission-blocker:** шапка стр.31 «пакет **НЕ может честно назвать себя** `admissibleForDeclaredDPFUse`»;
  §1 стр.113 «guardian… **в этом прогоне не задействован**, статус пакета честно не повышен».
- **handoff:** §10 стр.722 «HC-4 — закрывает конкретный пробел, **названный критиком (C-3)**»;
  Conformance стр.877–879 «Статус пакета **решает только критик** (CC-DPFDA.8…)».

FPF §66636: «A failure in this subpass lowers the affected coordinate even when individual pattern
bodies pass E.21. … do not copy the package-form proof into pattern bodies.» → **D5 = 3.**
Durable-факт «часть источников pretrain-only, не верифицирована» законно живёт как trust-cue в
Carrier note / source-pack; но обрамление «**этого прогона**», «**решение заказчика**», «**уточнено/
добавлено/исправлено ремонтом 2026-07-14**», «**названный критиком C-3**», «**в этом прогоне не
задействован**» — это run/review/handoff-нарратив, который PFM7 запрещает в носителе. Ход ремонта
уже дословно сохранён в `quality-record-2026-07-14.md` и `web-verification-2026-07-14.md`
(no-information-loss соблюдён) — дублировать его в `DPF.md` не нужно и нельзя.

*Repair (тривиально по технике, БЛОКИРУЮЩЕЕ):* см. §6 правка №1.

### R2r-2 (значимый, НЕ блокирующий). Заявленная PFM7-со-правка R2-2 оказалась неполной
`web-verification-2026-07-14.md` (секция R2-2) утверждает: «`DPF.md` Паттерн 1 принцип + §8 «Источник
термина» (**label ремонта снят одновременно, PFM7-правка того же прохода**)». Спот-чек носителя: §8
стр.671–677 всё ещё несёт **полный change-narrative** «**исправлено по верификации 2026-07-14**: было
«первоисточник термина / термин восходит к», стало «ранняя каноническая работа»». Содержательная
правка (смягчение) внесена — но её PFM7-обрамление НЕ снято, вопреки заявлению ремонта. Это
подтверждает, что чистка формы велась точечно и незавершённо, а не как отдельный целевой проход.
*Repair:* включается в правку №1 (§6) — вычистить change-narrative «было X, стало Y», оставить только
durable-формулировку «ранняя каноническая работа по TOCTOU (Bishop & Dilger, Computing Systems 1996)».

### R2r-3 (значимый, НЕ блокирующий). Финальная conformance-строка устарела (`seedOnly`), занижает
Носитель стр.881 говорит «E.4.DPF.DA: **seedOnly**», хотя r1 уже переоценил род состояния до
`repairBeforeDPFUse` (source-basis больше не seed-grade — независимо подтверждено моим спот-чеком §0.1).
Строка **занижает** (seed vs repair-before), не завышает — поэтому не создаёт ложного доверия и НЕ
является дополнительным gate-риском. Но при правке №1 она обязана быть приведена к точному роду.
*Repair:* при чистке носителя заменить финальную строку на актуальный род `repairBeforeDPFUse` (или,
после чистки D5→4 — на `admissibleForDeclaredDPFUse`, если критик r3 подтвердит).

### R2r-4 (значимый, НЕ блокирующий, перенос R2-4). D8 гетерогенность TOCTOU-центрична
HC-4 закрыл главный дефект (worked-evidence вне одного файла, cross-project). Остаётся: TOCTOU-класс
доминирует в 3 из кейсов (HC-4 + Паттерн 1 + threadsafety-пример), reader-role-вариация (dev/guardian)
в кейсах не показана, HC-3 (`DPF-DEDICATED-IO-THREAD`) principle-grounded pending. Достаточно для пола
4, не для 5. *No-proposal* (проверено: HC-1/HC-2/HC-4 форсят разные структурные меры — счётчик+drain /
non-blocking acquire / LRU-eviction; heterogeneity реальна). Reopen при сборке `DPF-DEDICATED-IO-THREAD`.

---

## 3. Подпроход формы PFM1–PFM11 (E.4.DPF.DA:4.3a, §66618–66634)

| PFM | Проверка | Дисп. | Обоснование (после ремонта R2-*) |
|-----|----------|-------|-----------|
| PFM1 Front-door order | ToC/preface до паттернов | **pass** | Структурный отчёт + Оглавление до §4; вход по симптому |
| PFM2 Pattern-language primacy | паттерны — главный язык | **pass** | §4 (7 паттернов) первые; BridgeMatrix/тяжёлые карты в references |
| PFM3 Map discoverability | карты достижимы | **pass** | §5/§6/§7 из ToC; references-ссылки живые |
| PFM4 Dependency direction | Core не зависит от DPF | **pass** | только grounded_in/uses к FPF; обратной зависимости нет |
| PFM5 Pub/access-carrier boundary | носитель не становится admission-status/process-state «by being visible» (§66628) | **fail** | носитель несёт admission-status (стр.31/113), review-status (стр.809/881), process-run (шапка/§7/§8/§11), handoff (стр.722/877) как контент — ровно то, что §66628 запрещает. Без изменений vs r1 |
| PFM6 Public naming | доменное имя, без process-slang | **pass** | заголовок предметный; `status:active`+`maturity:seed`+`edition:0.1` — легитимный field-split, не slang в идентичности |
| PFM7 Development-state absence | нет run/review/admission/handoff residue (§66630) | **fail** | R2r-1: 4 запрещённые категории первазивно → D5 (вторично D9/D10) |
| PFM8 Cross-DPF relation discipline | ссылки типизированы, blocked reading | **pass** | `DPF-DEDICATED-IO-THREAD` как peer (пустой, не слит); HC-4 urllib3 — external worked-case, не DPF-reference |
| PFM9 Normal-pattern maturity | E.8+E.21, не скелет | **pass** | 7 паттернов полностью развёрнуты (E.8), worked-slice из реального кода дословно; seed допускает pattern-maturity |
| PFM10 Access-currentness | skill/MCP edition-refs | **n.a.** | нет собственного skill/MCP access-carrier (доступ через общий dpf-authoring) |
| PFM11 Structure-account | structure-account в шапке | **pass с оговоркой** | присутствует (для-кого/передний-план/огрублено/денора/возврат); та же оговорка r1 — structure-account перемешан с process-run-нарративом (PFM7) |

**Итог подпрохода:** PFM5 **fail** + PFM7 **fail** (один корень — process/status residue в носителе) →
тянут **D5** (вторично касаются D9/D10, scored primarily at D5, чтобы не double-count). PFM9 pass (тела
сильны) — но §66636: провал формы понижает координату независимо от качества тел. Остальные pass/n.a.
Диспозиции идентичны r1 — ремонт не изменил ни одну из двух failing PFM.

---

## 4. Таблица координат D1–D11 (E.4.DPF.DA:4.2/4.3, §66588–66614) — пол = 4 (reliance-bearing)

| Координата | Знач. | ShortRationale (почему не выше И не ниже) | EvidenceLocus | Repair / no-proposal |
|-----------|:---:|---|---|---|
| **D1** DomainScopeAndUse | **4** | Bounded context/reader/first-use/non-use crisp (не asyncio/multiprocessing/distributed/AMQP-proto). Не 5: полной replayability across cases нет. Не 3: scope полностью восстановим, non-use образцова | §1; scope.md | no-proposal (проверено: 4 пункта + сильная non-use) |
| **D2** DidacticEntry | **4** | ToC+структурный отчёт+вход-по-симптому+worked-код → adoption дёшев. Не 5: assets/ пуст (AI-review card TBD), нет skill-entry. Не 3: первый результат без FPF-знаний достижим | Структурный отчёт; Оглавление; §4 | no-proposal; опц. AI-review card (отложена) |
| **D3** ScalableFormality | **4** | Стадии plain→typed refs→Фаза 6→evidence-upgrade route. Не 5: часть assurance-route (полная верификация 21 источника) не пройдена. Не 3: переход без переписывания | §11; references/*; critic-review* | no-proposal |
| **D4** CoreDependency | **4** | Зависит от FPF Core, domain внутри DPF, локальные термины Core не переопределяют, обратной зависимости нет (CC-DPFDA.6b). Не 5: нет Core-amendment-кандидатов (не требуются). Не 3: граница чистая | frontmatter; §9; PFM4 | no-proposal |
| **D5** PackageFormLayering | **3** | PFM1–4 pass, тела сильны — НО **PFM5+PFM7 fail**: admission-status/review-status/handoff/process-run residue первазивно в носителе (шапка стр.27/31/33, §1 стр.113, §2 стр.148, Паттерн 2 стр.270, §7 стр.640/643/644, §8 стр.673, §10 стр.722, §11, Conformance стр.877, финальная стр.881). Не 4: процессное состояние протекло в carrier, дефект первазивный, ремонтом НЕ уменьшен. Не 2: слоение по файлам в основном соблюдено, references отделены | стр.27/31/113/148/270/640/643/644/673/722/877/881; PFM5/7; R2r-1 | **repair (блокер):** §6 правка №1 → D5→4 |
| **D6** DomainLexicon | **4** | §8: 10 терминов kind/определение/«не является»; provisional помечены; A4-источник (Bishop&Dilger) добавлен. Не 5: «guarded suspension» RU-калька не решена, glossary не заполнен (файла нет). Не 3: термины settled | §8; F.18 | no-proposal (glossary-перенос — отдельный шаг без поручения) |
| **D7** PracticeUtility | **4** | Паттерны решают узнаваемые задачи + SoTA-ходы + анти-паттерны + worked cases из РЕАЛЬНОГО кода; S8 теперь verified (усиливает Паттерн 2). Не 5: S10 (книга) ещё pretrain. Не 3: явно не taxonomy-only, CC-DPF.9 содержателен | §4; §6; §7; спот-чек кода | no-proposal |
| **D8** HeterogeneousCase | **4** | HC-4 (urllib3#1252, **мной independently verified**) — worked-evidence в стороннем проекте/домене, закрывает корень C-3. HC-1/2/4 форсят разные структурные меры. Не 5: reader-role diversity тонкая, TOCTOU-центрична, HC-3 pending (R2r-4). Не 3: разнородность реальна | §10 HC-1/2/4; §0.1; R2r-4 | no-proposal (reopen при сборке DPF-DEDICATED-IO-THREAD) |
| **D9** EditionState | **4** | Оба корня r1 устранены и держатся: source-currentness verified с датами/URL (PEP 779/threadsafety — мной перепроверено §0.1), `status:stage-0`→maturity/edition, `fpf_edition` live-grep-сверен. Не 5: полная верификация 21 источника не пройдена; PFM7-residue частично касается D9, но scored primarily at D5 (не double-count). Не 3: edition/currentness/decay explicit и частично verified | frontmatter; §2 Currentness; §11; web-verification; §0.1 | no-proposal (PFM7-остаток чинится через D5-repair) |
| **D10** ImprovementRefresh | **4** | 8 refresh-триггеров (часть с ✅-резолюцией) + 6 provenance-вопросов (4 закрыты) + smallest-repair routes. Не 5: часть routes (полная верификация) не пройдена; ✅-метки касаются PFM7 (scored at D5). Не 3: reopen-условия конкретны | §11 Refresh/Open assumptions | no-proposal |
| **D11** DomainSoTAAlignment | **4** | 3 причины r1 адресованы и держатся: несущие anchor'ы verified (мой спот-чек 3 — 0 битых), A4→Bishop&Dilger 1996 crisp, memory-model покрыта Паттерном 7 с official docs. S8 теперь verified (R2-3). Источники дисциплинируют контент (BridgeMatrix явные потери, не bibliography — CC-DPFDA.5). Не 5: S10 pretrain, AI2 корректно остаётся hypothesis. Не 3: source-basis не seed-grade | §7 SE-1..14; web-verification; §0.1 | no-proposal для пола (опц.: сверить S10 при доступе к книге) |

**Координаты ниже пола 4:** **D5=3** (единственная). D8/D9/D11 подтверждены на 4 моим независимым
спот-чеком (не унаследованы). Средним баллом сильных паттернов (E.21) НЕ подменяется (CC-DPFDA.4
удержан, §66616/§66698): тела сильны, но PFM5/PFM7-провал формы держит D5 ниже пола независимо от
качества тел (§66636).

---

## 5. Вердикт CC-DPF.1–9 (E.4.DPF:7, §66421, построчно)

Проверено содержательно (не наличие заголовка — anti-pattern «checklist promoted»); статус — по D1–D11.

- **CC-DPF.1** Context declared — **PASS** (§1; зеркалит scope.md).
- **CC-DPF.2** Source pack present — **PASS** (source-pack.md: 21+5=26 источников, adopted/rejected+причина, claim-status, currentness; часть verified).
- **CC-DPF.3** Architecture decision present — **PASS** (структурный отчёт + non-use §1 + §9 Relations).
- **CC-DPF.4** Names prepared — **PASS** (§8, 10 терминов + A4-источник; provisional помечены).
- **CC-DPF.5** Carriers admitted — **PASS** (Carrier note: pretrain + verified web + FPF live-grep + Read кода; admission честен).
- **CC-DPF.6** Patterns drafted through E.8 — **PASS** (**7** паттернов сверх пола ≥4, полная форма E.8; Паттерн 7 с verified-источниками).
- **CC-DPF.7** Quality & refresh routes present — **PASS** (§11: критерии + 8 триггеров + 6 вопросов, 4 закрыты).
- **CC-DPF.8** Структурный отчёт в шапке — **PASS** (для-кого/передний-план/огрублено/денора/возврат; оговорка — перемешан с process-нарративом, PFM7/PFM11).
- **CC-DPF.9** Примат решения задач — **PASS** (§4/§6/§7: задачи домена, 12 блокируемых провалов, 14 SoTA-ходов; не ontology-only).

**CC-DPF.1–9: все PASS.** НО (Паттерн 4 / anti-pattern №4, §66707): присутствие секций ≠ адекватность.
Статус — по D1–D11 (**D5=3**).

---

## 6. Статус пакета (E.4.DPF.DA:4.5, §66658 — ровно один)

### `repairBeforeDPFUse`

**Обоснование (§66663):** «One or more coordinates are below floor for the stated use» — D5=3 < пол 4.
Род состояния **не изменился vs r1**: корневой блокер r1 (C-4 unverified source-basis) остаётся
устранён (независимо подтверждено §0.1), единственный оставшийся дефект (D5, PFM5/PFM7) — та же дешёвая
форменная правка, что r1 назвал блокирующей и которую ремонт R2-* **обошёл**. Пакет содержательно
reliance-ready по 10 из 11 координат; блокирует только PFM7-residue в носителе.

> Почему НЕ `seedOnly`: source-basis больше не seed-grade (провенанс verified, мой спот-чек чист).
> Почему НЕ `admissibleForDeclaredDPFUse`: D5 ниже пола — гейт требует ВСЕХ координат ≥ пола.
> Почему НЕ `refreshNeeded`/`holdFor*`: ни source/Core-edition drift, ни PFAD/Core-amendment-вопрос не
> стоят — вопрос чисто в чистке носителя.

### Наименьшие правки (по возрастанию цены)

1. **(тривиально по технике, БЛОКИРУЮЩЕЕ)** Вычистить из `DPF.md` ВЕСЬ process/run/mode-C/review-status/
   admission-blocker/gate/handoff нарратив — конкретно:
   - шапка стр.27–34: убрать «Режим ресёрча **этого прогона** (явное решение заказчика)…», «пакет НЕ
     может честно назвать себя admissible» → оставить одну durable-строку о режиме источников как
     trust-cue («часть источников — pretrain-only, не веб-верифицирована; провенанс —
     `references/source-pack.md`») + один pointer на `references/critic-review*.md` +
     `web-verification-2026-07-14.md`;
   - §1 стр.113: убрать «в этом прогоне не задействован, статус честно не повышен» → durable «Фаза 6 —
     `references/critic-review*.md`»;
   - §2 стр.148: убрать «явное решение заказчика этого прогона, не забыто…» → durable trust-cue;
   - Паттерн 2 стр.270: убрать «уточнён **ремонтом 2026-07-14**» → оставить сам факт статуса PEP 779
     (durable) с датой-источником;
   - §7 стр.640/643/644: снять метки «уточнено 2026-07-14», «(добавлен 2026-07-14)» у SE-10/13/14
     (verified-даты источников оставить как evidence-anchor — это durable, метки-«добавлен ремонтом» —
     нет);
   - §8 стр.671–677 (R2r-2): убрать change-narrative «исправлено по верификации… было X, стало Y» →
     оставить durable «ранняя каноническая работа по TOCTOU, Bishop & Dilger, Computing Systems 1996»;
   - §10 стр.722: убрать «названный критиком (C-3)» → durable объяснение денора без review-ссылки;
   - §11: заменить «✅ закрыто/уточнено 2026-07-14»-нарратив на durable refresh-триггеры без
     round-narrative; ход ремонта уже в `quality-record`/`web-verification`;
   - Carrier note стр.827: убрать «эта **правка** ИСПОЛЬЗОВАЛА WebSearch…» → durable «источники verified
     2026-07-14, протокол — `web-verification-2026-07-14.md`»;
   - Conformance стр.875–879: убрать «Статус пакета решает только критик»-handoff → одна финальная
     conformance-строка.
   → чинит PFM5/PFM7, поднимает **D5→4 → admissible**.
2. **(входит в №1)** Финальную строку `E.4.DPF.DA: seedOnly` (стр.881, устарела, R2r-3) привести к
   актуальному роду `repairBeforeDPFUse`; после чистки D5→4 критик r3 подтверждает
   `admissibleForDeclaredDPFUse`.
3. **(опц., не блокирует)** Сверить S10 (Python Cookbook 3rd) при доступе к книге ИЛИ понизить его роль
   до «corroborating, не несущий» (Паттерн 2 держится на verified S8+S9). Не требуется для пола.

**После правки №1 пакет становится `admissibleForDeclaredDPFUse`** — все 11 координат ≥ 4. Правки №2
входят в №1; №3 — улучшение сверх пола.

---

## 7. Гейт Фазы 6 (r2)

- CC-DPF.1–9: **PASS** (все 9).
- Статус пакета: **`repairBeforeDPFUse`** (НЕ `admissibleForDeclaredDPFUse`; D5=3).
- **GATE НЕ ПРОЙДЕН** (гейт требует CC-DPF.1–9 PASS **И** admissible). Строка
  `admissibleForDeclaredDPFUse` в `DPF.md` **НЕ дописывается**; frontmatter (`maturity:seed`,
  `edition:0.1`) НЕ повышается — статус не заслужен по D5. Финальная строка носителя (`seedOnly`)
  занижает род (должна стать `repairBeforeDPFUse`), но не завышает — повышение до admissible возможно
  ТОЛЬКО после правки №1 и переоценки D5 критиком r3.

**Признание работы ремонта (Паттерн 6, knowledge distribution — не пустое ревью):** ремонт R2-* закрыл
2/2 не-блокирующих пункта содержательно и с verified-evidence (S8 поднят pretrain→verified — реальный
апгрейд; A4-wording смягчён корректно). Source-basis держится независимой проверкой. Это названо как
есть. **Но:** ремонт обошёл единственный gate-блокер (R2-1/PFM7), выбрав более дешёвые по объёму
пункты — поэтому статус r2 идентичен r1 (`repairBeforeDPFUse`), и гейт по-прежнему закрыт. Anti-
sycophancy: тот факт, что «сделали работу по списку», НЕ повышает статус, пока блокирующая координата
ниже пола (§66636/CC-DPFDA.4).

**Следующий шаг:** curator выполняет правку №1 (чистка носителя — техника тривиальна, объём —
перечислен построчно в §6); critic r3 переоценивает D5 и, при чистом носителе, присваивает
`admissibleForDeclaredDPFUse` + дописывает conformance-строку и правит frontmatter.

Ревью зафиксировано как inspectable-артефакт (Паттерн 6). Следующая роль читает §1 (что закрыто/нет),
§6 (наименьшие правки построчно) и §0.1 (независимо перепроверенные якоря) как карту. Историю прошлых
ревью (`critic-review.md`, `critic-review-2026-07-14-r1.md`) не редактировал.
