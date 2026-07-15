# Critic Review — DPF-CONCURRENT-PROGRAMMING (Круг 2: повторная проверка после ремонта r1, режим C)

> Роль: `DPF-ADVERSARIAL-REVIEW` (owner guardian), Режим B — критика собранного пакета,
> переоценка по E.4.DPF.DA после ремонта круга 1.
> Вход: `DPF.md` (890 строк) + `references/{scope,sota-research,theses-antitheses,source-pack,
> critic-review,quality-record-2026-07-14,web-verification-2026-07-14}.md` +
> сверка worked-evidence с `src/kombu_pyamqp_threadsafe/__init__.py`.
> FPF читан живьём: E.4.DPF §66066–66504, E.4.DPF.DA §66506–66757 (шкала §66575, координаты
> D1–D11 §66588–66607, форма-строка §66608, PFM1–PFM11 §66618–66634, evidence-basis §66638,
> статусы §66658–66668) — Grep+Read по `~/.claude/knowledge/fpf/FPF-Spec.md`, не по памяти.
> Дата прогона: **2026-07-14**, круг 2 (после ремонта r1 куратора).
> **Role-separation-gate (Паттерн 1):** этот критик — отдельный агент/сессия от сборки Фаз 0–5
> И от ремонта r1 (`DPF-KNOWLEDGE-CURATION`, quality-record-2026-07-14.md); нарушения нет.
> **Anti-sycophancy (Паттерн 5):** ремонт сделан по прошлому repair-списку этого же критика — это
> НЕ основание завышать. Проверено содержательно; 6 web-якорей перепроверены по URL (см. §0.1).

---

## 0. Итог одной строкой

Ремонт r1 **сделал настоящую работу** и закрыл **4 из 5** пунктов repair-списка: A4/TOCTOU получил
crisp-первоисточник (verified), HC-4 вынес worked-evidence в СТОРОННИЙ проект (verified), Паттерн 7
закрыл memory-visibility-пробел под free-threaded (verified official docs), веб-верификация подняла
несущие anchor'ы из pretrain-only до verified (0 галлюцинированных цитат в спот-чеке 6 якорей). Это
поднимает **D8, D9, D11 с 3 до 4** — корень прошлого статуса (`seedOnly` = «unverified source-basis по
природе») **устранён**. НО пункт repair-списка №1 (**PFM7**) закрыт лишь наполовину: frontmatter
`status:stage-0` убран — а run-narrative не вынесен, а **разросся** (шапка «Ремонт 2026-07-14 круг 1
режим C… вердикт seedOnly, gate не пройден», per-section метки «добавлен ремонтом 2026-07-14»,
§11/Conformance round-narrative). Четыре из запрещённых PFM7-категорий (review-status, admission-blocker,
handoff, process-run residue) присутствуют в пользовательском носителе первазивно. **D5 остаётся 3.**

**Статус: `repairBeforeDPFUse`** (одна координата ниже пола — D5). Это **сдвиг рода состояния** vs
круга 1: пакет больше НЕ seed-grade по source-basis (провенанс верифицирован), он в **одну дешёвую
правку** (вычистить процессный нарратив) от `admissibleForDeclaredDPFUse`. **Гейт Фазы 6 НЕ пройден.**

---

## 0.1. Перепроверка web-якорей ремонта по URL (anti-sycophancy, выборка 6 из ~16)

| Якорь | URL | Что заявлено в web-verification / DPF | Вердикт спот-чека |
|---|---|---|---|
| PEP 779 (B4/S11) | peps.python.org/pep-0779 | 3.14 = officially supported non-default; default (Phase III) отложен, горизонт 2028+ | **подтверждён дословно** — Phase II = supported non-default в 3.14; Phase III (default) явно отдельный, «revolve around community support», не датирован |
| threadsafety.html (Паттерн 7 / A4) | docs.python.org/3/library/threadsafety.html | документирует free-threaded built-in типы; `if key in d: del d[key]` = NOT atomic (TOCTOU) | **подтверждён дословно** — та же формулировка, «When the GIL is enabled, most operations are implicitly serialized»; check-then-act пример явно помечен TOCTOU |
| urllib3#1252 (HC-4) | github.com/urllib3/urllib3/issues/1252 | PoolManager не thread-safe: pool вытесняется из LRU между получением и использованием — TOCTOU, не data race | **подтверждён** — issue именно об этом (check pool из кэша → evict → act на невалидном pool); ДРУГОЙ проект/домен реально |
| Bishop & Dilger 1996 (A4) | en.wikipedia.org/wiki/Time-of-check_to_time-of-use | первоисточник термина TOCTOU/TOCTTOU | **источник реален и точно атрибутирован** (Computing Systems, 1996, pp.131–152); **нюанс:** Wikipedia держит его в «Further reading», НЕ приписывает ему явно чеканку термина — см. концерн R2-2 |
| S17 Lu et al. ASPLOS 2008 | (dl.acm.org, косвенно) | 4 условия/эмпирика классов багов | ранее спот-чекнут кодом; атрибуция консистентна, не переверифицировал URL заново (вне разумного объёма) |
| Код worked-evidence | `__init__.py` | Паттерн 7 (`transport` 907–913, `default_channel` 948–970), HC-1/HC-2, change_owner, DrainGuard | **все процитированные строки/комментарии совпали дословно** — 0 стоп-находок (см. §1 «Положительное») |

Вывод спот-чека: **0 галлюцинированных цитат**, инструментальный слой ремонта (WebSearch/WebFetch,
live-grep FPF, Read кода) реален. Один нюанс атрибуции (A4-Wikipedia) — не стоп-находка (источник
genuine, provenance-gap закрыт), но формулировка чуть сильнее носителя.

---

## 1. Что закрыто из прошлого repair-списка, что нет

| # | Repair-пункт (круг 1) | Целевые коорд. | Статус после r1 | Обоснование |
|---|---|---|---|---|
| 1 | PFM7: `status:stage-0`→maturity/edition; run-narrative вынести | D5/D9 | **⚠️ ЧАСТИЧНО** | frontmatter починен (`status:active`+`maturity:seed`+`edition:0.1`); НО run-narrative НЕ вынесен — вынесены старые фрагменты «Фаза 6 не выполнена» в quality-record, взамен добавлен НОВЫЙ нарратив «Ремонт r1 режим C… gate не пройден… решает критик Круг 2» по всему носителю. Whack-a-mole: остаток не уменьшен → **D5 остаётся 3** |
| 2 | A4/TOCTOU → первоисточник | D11 | **✅ ЗАКРЫТ** | Bishop & Dilger 1996, verified (Semantic Scholar + Wikipedia); crisp «источник+дата» есть → falsifiability-gate/A.10 удовлетворён |
| 3 | worked-кейс из другого домена | D8 | **✅ ЗАКРЫТ** | HC-4 urllib3#1252 — сторонний проект, verified WebFetch; впервые worked-evidence вне `__init__.py` |
| 4 | memory-visibility под free-threaded зафиксировать | D11/D8 | **✅ ЗАКРЫТ (сверх ожидания)** | не «пометка пробела», а полный Паттерн 7 (E.8) с verified official-docs источниками; закрывает C-2 содержательно |
| 5 | веб-верификация несущих anchor'ов | D11/D9 | **✅ СУЩЕСТВЕННО ЗАКРЫТ** | приоритетные (A4/B4/S19/AI) + 10 научных первоисточников verified, 0 битых; S1/S8/S10/park честно оставлены pretrain — bounded, не скрыто |

**Итог:** 4/5 закрыто. Единственный незакрытый — №1 (PFM7), и именно он теперь единственный
gate-блокер. Корневой концерн круга 1 (C-4, unverified source-basis) — **устранён**, поэтому статус
меняет РОД: `seedOnly` → `repairBeforeDPFUse` (не «seed по природе», а «одна форменная правка до пола»).

---

## 2. Значимые концерны круга 2 (≥3, severity как есть — Паттерн 5)

### R2-1 (БЛОКИРУЮЩИЙ). PFM7: процессный нарратив разросся в носителе — C-5 закрыт наполовину
Пользовательский `DPF.md` содержит **четыре** из запрещённых PFM7-категорий, первазивно:
- **process-run residue:** шапка стр.33–38 «Ремонт 2026-07-14 (круг 1, режим C)…»; метки «(добавлен
  ремонтом 2026-07-14)» в заголовке Паттерна 7, §5-таблице, §6 ошибка 12, §8, §10 HC-4; блокquote под
  Паттерном 7 «Добавлен в этом ремонте… закрывает C-2… понижал D11/D8».
- **review-status:** «вердикт seedOnly, gate не пройден: D5/D8/D9/D11 ниже пола 4» (шапка, §11,
  Conformance, финальная строка).
- **admission-blocker:** «статус пакета по-прежнему решает только критик (Круг 2)».
- **handoff:** «итоговое повышение статуса решает критик, Круг 2» (финальная строка).

Метод (E.4.DPF.DA:4.3a PFM7 + DPF-AUTHORING error №5) допускает в носителе durable-контент +
**одну** финальную conformance-строку со статусом; здесь — многоабзацная шапка + per-section метки +
Conformance-нарратив. E.4.DPF.DA:4.3a: «A failure in this subpass lowers the affected coordinate even
when individual pattern bodies pass E.21.» → **D5 = 3**. Ирония: пакет `DPF-ADVERSARIAL-REVIEW` ловил
ровно этот класс (HC-2/HC-4: `status:stage-0`→maturity) как блокирующий; здесь residue шире frontmatter.
*Repair (тривиально, дёшево):* вычистить из `DPF.md` весь repair-round/mode-C/gate-status/handoff-нарратив
(шапка, per-section метки, §11 «Что изменилось этим ремонтом», Conformance run-narrative). Оставить:
durable-контент паттернов + один pointer «оценка адекватности — `references/critic-review*.md`; режим
источников — pretrain+частичная веб-верификация, `references/web-verification-2026-07-14.md`» + одну
финальную conformance-строку. Ход ремонта уже дословно в `quality-record-2026-07-14.md` — дублировать в
носителе не нужно (no information loss соблюдён). → D5→4 → admissible.

### R2-2 (значимый, НЕ блокирующий). A4/Bishop-Dilger: атрибуция genuine, «чеканка термина» — чуть сильнее носителя
`web-verification-2026-07-14.md` пишет, что Wikipedia «цитирует Bishop & Dilger 1996 как одну из первых
детальных работ, вводящих TOCTOU/TOCTTOU-номенклатуру». Спот-чек URL: Wikipedia держит работу в
**«Further reading»**, НЕ приписывает ей явно чеканку термина. Источник реален, атрибуция (авторы/venue/
год/страницы) точна, provenance-gap A4 **закрыт** (source+date есть → D11 не блокируется). Но
формулировка «вводящих номенклатуру» опирается на носитель слабее заявленного.
*Repair (косметика):* смягчить в `sota-research.md`/`web-verification` до «ранняя каноническая детальная
работа по TOCTOU в file-access (Computing Systems 1996)», без claim «ввела термин», либо привязать
чеканку к отдельному источнику (McPhee 1974 TOCTTOU, если верифицируем). Не влияет на статус.

### R2-3 (значимый, НЕ блокирующий). Несущие GIL-atomicity источники S8/S10 остаются pretrain-only
Паттерн 2 (GIL-граница) и типовая ошибка 1 (составные операции) опираются на S8 (Python core docs) и
S10 (Python Cookbook 3rd) — оба всё ещё `pretrain recall`. Веб-верификация покрыла S9 (Beazley, verified),
который корроборирует тот же SE-4 → Паттерн 2 не висит на одном unverified anchor, **D11 держит 4**. Но
первичные doc-источники GIL-атомарности не сверены напрямую, хотя они тривиально верифицируемы (та же
`docs.python.org`, что уже открывалась для Паттерна 7).
*Repair (дёшево, refresh-route):* при следующем круге сверить S8/S10 по `docs.python.org` — уже в
периметре открытых вкладок ремонта; назван как остаток в §11, не скрыт.

### R2-4 (значимый, НЕ блокирующий). D8: cross-project закрыт, reader-role diversity — тонкая
HC-4 закрывает главный дефект (worked-evidence вне одного файла) → **D8→4**. Но гетерогенность всё ещё
преимущественно architect-facing и TOCTOU-центрична (TOCTOU в HC-4 И Паттерне 1 И threadsafety-примере —
один класс в трёх из кейсов); dev/guardian reader-role-вариации в кейсах не показаны; HC-3
(`DPF-DEDICATED-IO-THREAD`) остаётся principle-grounded pending. Достаточно для пола 4, не для 5.
*No-proposal* (проверено: HC-1/HC-2/HC-4 форсят разные структурные меры — счётчик+drain / non-blocking
acquire / LRU-eviction; heterogeneity реальна, не номинальна). Reopen при сборке `DPF-DEDICATED-IO-THREAD`.

---

## 3. Подпроход формы PFM1–PFM11 (E.4.DPF.DA:4.3a)

| PFM | Проверка | Дисп. | Обоснование (изменения после r1) |
|-----|----------|-------|-----------|
| PFM1 Front-door order | ToC/preface до паттернов | **pass** | Структурный отчёт + Оглавление до §4; вход по симптому |
| PFM2 Pattern-language primacy | паттерны — главный язык | **pass** | §4 (7 паттернов) первые; тяжёлые карты/BridgeMatrix в references |
| PFM3 Map discoverability | карты достижимы | **pass** | §5/§6/§7 из ToC; references-ссылки живые |
| PFM4 Dependency direction | Core не зависит от DPF | **pass** | только grounded_in/uses к FPF; обратной зависимости нет |
| PFM5 Pub/access boundary | носитель ≠ провенанс/статус | **fail (усилился vs круг 1)** | frontmatter починен, НО носитель СТАЛ нести admission-status/review-status/handoff как контент (шапка+Conformance) — carrier стал «admission status/process state by being visible» (ровно то, что PFM5 запрещает) |
| PFM6 Public naming | доменное имя, без process-slang | **pass** | заголовок предметный; `status:active`+`maturity:seed` — легитимный field-split (lifecycle vs зрелость), не slang в идентичности |
| PFM7 Development-state absence | нет run/review/handoff residue | **fail** | R2-1: 4 запрещённые категории первазивно → D5/D9 |
| PFM8 Cross-DPF relation discipline | ссылки типизированы, blocked reading | **pass** | `DPF-DEDICATED-IO-THREAD` как peer, пустой, явно не слит; HC-4 urllib3 — external worked-case, не DPF-reference |
| PFM9 Normal-pattern maturity | E.8+E.21, не скелет | **pass** | 7 паттернов полностью развёрнуты; Паттерн 7 (новый) — полная форма E.8 с verified-источниками и code-worked-slice; seed допускает pattern-maturity |
| PFM10 Access-currentness | skill/MCP edition-refs | **n.a.** | нет собственного skill/MCP access-carrier (доступ через общий dpf-authoring) |
| PFM11 Structure-account | structure-account в шапке | **pass с оговоркой** | присутствует (для-кого/передний-план/огрублено/денора/возврат); оговорка — тот же structure-account перемешан с process-run-нарративом (см. PFM7) |

**Итог подпрохода:** PFM5 **fail** + PFM7 **fail** (тот же корень — process/status residue в носителе) →
тянут **D5** (и вторично D9). PFM9 pass (тела сильны) — но 4.3a: провал формы понижает координату
независимо от качества тел. Остальные pass/n.a.

---

## 4. Таблица координат D1–D11 (E.4.DPF.DA:4.2/4.3) — пол = 4 (reliance-bearing)

| Координата | Знач. | ShortRationale (почему не выше И не ниже) | EvidenceLocus | Repair / no-proposal |
|-----------|:---:|---|---|---|
| **D1** DomainScopeAndUse | **4** | Bounded context/reader/first-use/non-use — crisp (не asyncio/multiprocessing/distributed/AMQP-proto). Не 5: полной replayability across cases нет, HC-4 приближает, но обобщение всё ещё не «replayable». Не 3: scope полностью восстановим, non-use образцова | §1; scope.md | no-proposal (проверено: 4 пункта + сильная non-use) |
| **D2** DidacticEntry | **4** | ToC+структурный отчёт+вход-по-симптому+worked-код → adoption дёшев. Не 5: assets/ пуст (AI-review чек-карта TBD), нет skill-entry. Не 3: первый результат без FPF-знаний достижим | Структурный отчёт; Оглавление; §4 | no-proposal; опц. AI-review card (отложена) |
| **D3** ScalableFormality | **4** | Стадии: plain-паттерны→typed references→Фаза 6 выполнена→evidence-upgrade route. Не 5: часть assurance-route (полная верификация 21 источника) не пройдена. Не 3: переход без переписывания | §11; references/*; critic-review | no-proposal |
| **D4** CoreDependency | **4** | Зависит от FPF Core, domain внутри DPF, локальные термины Core не переопределяют, обратной зависимости нет. Не 5: нет Core-amendment-кандидатов (не требуются). Не 3: граница чистая | frontmatter; §9; PFM4 | no-proposal |
| **D5** PackageFormLayering | **3** | PFM1–4 pass, тела сильны — НО PFM5+PFM7 fail: admission-status/review-status/handoff/process-run residue первазивно в носителе (шапка, per-section метки, §11, Conformance). Не 4: процессное состояние протекло в carrier, форменный дефект НЕ локальный (первазивный). Не 2: слоение по файлам в основном соблюдено, references отделены | шапка стр.33–38; §11; Conformance; PFM5/7; R2-1 | **repair:** вычистить run/mode-C/gate/handoff-нарратив из `DPF.md`; оставить durable-контент + 1 pointer + 1 conformance-строку (ход — уже в quality-record) → D5→4 |
| **D6** DomainLexicon | **4** | §8: 10 терминов kind/определение/«не является»; provisional помечены; A4-источник добавлен. Не 5: «guarded suspension» RU-калька не решена, glossary не заполнен (файла нет). Не 3: термины settled | §8; F.18 | no-proposal (glossary-перенос — отдельный шаг без поручения) |
| **D7** PracticeUtility | **4** | Паттерны решают узнаваемые задачи + SoTA-ходы + анти-паттерны + worked cases из РЕАЛЬНОГО кода (verified дословно); Паттерн 7 добавил free-threaded-ход. Не 5: часть провенанса ещё pretrain (S8/S10). Не 3: явно не taxonomy-only, CC-DPF.9 содержателен | §4; §6; §7; спот-чек кода | no-proposal |
| **D8** HeterogeneousCase | **4** ↑ | Было 3. HC-4 (urllib3#1252, verified) — worked-evidence в СТОРОННЕМ проекте/домене, закрывает корень C-3. HC-1/2/4 форсят разные структурные меры. Не 5: reader-role diversity тонкая, TOCTOU-центрична, HC-3 pending (R2-4). Не 3: разнородность реальна, не номинальна | §10 HC-1/2/4; R2-4 | no-proposal (reopen при сборке DPF-DEDICATED-IO-THREAD) |
| **D9** EditionState | **4** ↑ | Было 3. Оба корня круга 1 устранены: (а) source-currentness теперь verified с датами/URL (B4/PEP779, S19, A4); (б) `status:stage-0`→maturity/edition. `fpf_edition` live-grep-сверен. Не 5: полная верификация 21 источника не пройдена, PFM7-residue частично касается (scored primarily at D5, чтобы не double-count). Не 3: edition/currentness/decay explicit и частично verified | frontmatter; §2 Currentness; §11; web-verification | no-proposal (PFM7-остаток чинится через D5-repair) |
| **D10** ImprovementRefresh | **4** | 8 refresh-триггеров (часть с ✅-резолюцией) + 6 provenance-вопросов (4 закрыты) + smallest-repair routes. Не 5: часть routes (полная верификация) не пройдена. Не 3: reopen-условия конкретны | §11 Refresh/Open assumptions | no-proposal |
| **D11** DomainSoTAAlignment | **4** ↑ | Было 3. Все 3 причины круга 1 адресованы: (1) несущие anchor'ы verified (спот-чек 6 — 0 битых); (2) A4/TOCTOU→Bishop&Dilger 1996 crisp-источник; (3) memory-model под free-threaded покрыта Паттерном 7 с official docs. Источники дисциплинируют контент (BridgeMatrix явные потери, не bibliography). Не 5: S8/S10 pretrain (R2-3), AI2 остаётся hypothesis (корректно не повышен), A4-«чеканка»-нюанс (R2-2). Не 3: source-basis больше НЕ seed-grade | §7 SE-1..14; web-verification; §0.1 | no-proposal для пола (опц.: сверить S8/S10, смягчить A4-формулировку) |

**Координаты ниже пола 4:** **D5=3** (единственная). D8/D9/D11 подняты ремонтом с 3→4.
Средним баллом сильных паттернов (E.21) НЕ подменяется (CC-DPFDA.4 удержан): тела сильны, но
PFM5/PFM7-провал формы держит D5 ниже пола независимо от качества тел.

---

## 5. Вердикт CC-DPF.1–9 (E.4.DPF:7, построчно)

Проверено содержательно (не наличие заголовка — анти-паттерн №4); статус — по D1–D11.

- **CC-DPF.1** Context declared — **PASS** (§1; зеркалит scope.md).
- **CC-DPF.2** Source pack present — **PASS** (source-pack.md: 21+5=26 источников, adopted/rejected+причина, claim-status, currentness; часть verified).
- **CC-DPF.3** Architecture decision present — **PASS** (структурный отчёт + non-use §1 + §9 Relations).
- **CC-DPF.4** Names prepared — **PASS** (§8, 10 терминов + A4-источник; provisional помечены).
- **CC-DPF.5** Carriers admitted — **PASS** (Carrier note: pretrain + verified web + FPF live-grep + Read кода; admission честен).
- **CC-DPF.6** Patterns drafted through E.8 — **PASS** (**7** паттернов сверх пола ≥4, полная форма E.8; Паттерн 7 добавлен с verified-источниками).
- **CC-DPF.7** Quality & refresh routes present — **PASS** (§11: критерии + 8 триггеров + 6 вопросов, 4 закрыты).
- **CC-DPF.8** Структурный отчёт в шапке — **PASS** (для-кого/передний-план/огрублено/денора/возврат; оговорка — перемешан с process-нарративом, см. PFM7).
- **CC-DPF.9** Примат решения задач — **PASS** (§4/§6/§7: задачи домена, 12 блокируемых провалов, 14 SoTA-ходов; не ontology-only).

**CC-DPF.1–9: все PASS.** НО (Паттерн 4 / анти-паттерн №4): присутствие секций ≠ адекватность.
Статус — по D1–D11 (D5=3).

---

## 6. Статус пакета (E.4.DPF.DA:4.5 — ровно один)

### `repairBeforeDPFUse`

**Обоснование.** Одна координата ниже пола 4 (D5, PFM5/PFM7 — процессный нарратив в носителе).
E.4.DPF.DA:4.5: `repairBeforeDPFUse` = «one or more coordinates below floor for the stated use».
Это **сдвиг рода состояния vs круга 1** (`seedOnly`): корневой блокер круга 1 (C-4, mode-wide
unverified source-basis, «seed-grade по природе, не устраним косметикой») **устранён** ремонтом —
несущие anchor'ы verified, A4 привязан, memory-model покрыта, HC-4 вынес worked-evidence в сторонний
проект. Оставшийся дефект (D5) — **НЕ фундаментальный seed-limit, а дешёвая форменная правка**
(вычистить run-narrative). Поэтому `repairBeforeDPFUse`, не `seedOnly`: пакет содержательно
reliance-ready по 10 из 11 координат, блокирует только PFM7-residue.

> Различение `seedOnly` vs `repairBeforeDPFUse`: круг 1 верно назвал `seedOnly`, т.к. корень был
> unverified-provenance (не косметика). После r1 корень закрыт; остаток — точечная форменная правка →
> `repairBeforeDPFUse` точнее называет род (пакет в одну правку от admissible, не seed по природе).

### Наименьшие правки (по возрастанию цены)

1. **(тривиально, БЛОКИРУЮЩЕЕ)** Вычистить из `DPF.md` process/run/mode-C/review-status/gate/handoff
   нарратив: шапка стр.33–38, per-section метки «(добавлен ремонтом 2026-07-14)», §11 «Что изменилось
   этим ремонтом», Conformance run-narrative. Оставить durable-контент паттернов + **один** pointer на
   `references/critic-review*.md` (адекватность) и `web-verification-2026-07-14.md` (режим источников) +
   **одну** финальную conformance-строку. Ход ремонта уже дословно в `quality-record-2026-07-14.md` —
   не терять, но и не дублировать в носителе. → чинит PFM5/PFM7, поднимает **D5→4 → admissible**.
2. **(косметика, не блокирует)** Смягчить A4-«ввела номенклатуру» до «ранняя каноническая работа по
   TOCTOU» ИЛИ привязать чеканку к отдельному источнику (R2-2). → чистит D11-формулировку.
3. **(дёшево, refresh-route)** Сверить S8/S10 (GIL-atomicity) по `docs.python.org` — в периметре уже
   открытых вкладок ремонта (R2-3). → усиливает D11/D7, не требуется для пола.

**После правки №1 пакет становится `admissibleForDeclaredDPFUse`** — все 11 координат ≥ 4. Правки
№2/№3 — улучшения сверх пола, не блокеры.

---

## 7. Гейт Фазы 6 (круг 2)

- CC-DPF.1–9: **PASS** (все 9).
- Статус пакета: **`repairBeforeDPFUse`** (НЕ `admissibleForDeclaredDPFUse`; D5=3).
- **GATE НЕ ПРОЙДЕН** (гейт требует CC-DPF.1–9 PASS **И** admissible). Строка
  `admissibleForDeclaredDPFUse` в `DPF.md` **НЕ дописывается**, frontmatter НЕ повышается — статус не
  заслужен по D5. Существующая честная строка (`seedOnly`) требует обновления до `repairBeforeDPFUse`
  куратором при следующей правке (носитель сейчас говорит `seedOnly` — это занижает, но не завышает;
  повышение до `repairBeforeDPFUse`/`admissible` — по факту правки №1).

**Признание работы ремонта (Паттерн 6, knowledge distribution — не пустое ревью):** r1 закрыл 4/5
пунктов содержательно и с verified-evidence; source-basis больше не seed-grade. Это реальный прогресс,
названный как есть. Единственный оставшийся блокер (PFM7-residue) — тривиально устраним; критик Круга 3
(после правки №1) должен переоценить D5 и, при чистом носителе, присвоить `admissibleForDeclaredDPFUse`.

Ревью зафиксировано как inspectable-артефакт. Следующая роль (curator-правка №1 → critic Круг 3)
читает §1 (что закрыто) и §6 (наименьшие правки) как карту.
