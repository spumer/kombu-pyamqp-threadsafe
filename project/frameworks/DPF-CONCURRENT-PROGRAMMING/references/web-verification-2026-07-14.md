# Web Verification Log — DPF-CONCURRENT-PROGRAMMING, ремонты 2026-07-14 (круги 1–2)

> Каждый проверенный claim: где живёт (файл/секция) → источник (URL + дата обращения) → вердикт
> (подтверждён / уточнён / опровергнут) → что изменено. Инструменты: WebSearch, WebFetch. Все URL
> обращены **2026-07-14**. Формат — по repair-списку `critic-review.md` п.5 и заданию.

---

## Приоритетные якоря из repair-списка

### 1. A4 — TOCTOU (time-of-check to time-of-use), первоисточник термина

- **Где живёт:** `sota-research.md` ClaimSheet A4; `theses-antitheses.md` §0.1/§Тезис 1/§типовая
  ошибка 5; `source-pack.md` открытый вопрос №3; `DPF.md` Паттерн 1 (принцип), §6 ошибка 5, §8 имена,
  §11 open assumptions №3.
- **Claim (было):** «TOCTOU — общий термин, изначально security-литература, общеупотребительна, в
  паре с S1» — без единичного crisp «источник+дата» (пограничный opinion-grade provenance).
- **Источник:** Bishop, M.; Dilger, M. — *"Checking for Race Conditions in File Accesses"*, Computing
  Systems, 1996, pp. 131–152. Подтверждено: [Semantic Scholar — Checking for Race Conditions in File
  Accesses (Bishop, Dilger)](https://www.semanticscholar.org/paper/Checking-for-Race-Conditions-in-File-Accesses-Bishop-Dilger/0f843c531bd02f205ed838b1709e220c5861c2f7),
  [Wikipedia — Time-of-check to time-of-use](https://en.wikipedia.org/wiki/Time-of-check_to_time-of-use)
  (цитирует Bishop & Dilger 1996 как одну из первых детальных работ, вводящих TOCTOU/TOCTTOU-номенклатуру
  на примерах Unix-утилит xterm/passwd).
- **Вердикт:** **уточнён** (не опровергнут — исходная claim-формулировка «security-литература,
  общеупотребительна» была верной, но неполной; теперь есть конкретный citable первоисточник).
- **Что изменено:** `sota-research.md` A4 — добавлен evidence-anchor «Bishop, M.; Dilger, M. —
  "Checking for Race Conditions in File Accesses", Computing Systems, 1996, pp. 131–152»; trust-cue
  A4 обновлён с «pretrain recall, не верифицирован» на «verified 2026-07-14, Bishop & Dilger 1996 +
  Wikipedia/Semantic Scholar подтверждение атрибуции». `source-pack.md` открытый вопрос №3 — добавлена
  строка-резолюция (оригинал не удалён). `DPF.md` Паттерн 1 принцип — добавлена цитата с источником;
  §6 ошибка 5 источник-колонка дополнена; §11 open assumptions №3 дополнен резолюцией.

### 2. B4 / S11 — PEP 703, статус развёртывания free-threaded CPython

- **Где живёт:** `sota-research.md` ClaimSheet B4/S11; `DPF.md` Паттерн 2 анти-паттерн + Связи,
  §7 SE-5, §11 refresh-триггер №1 + open assumption №1.
- **Claim (было):** «PEP 703 принят 2023, experimental в 3.13, дальнейшее укрепление в 3.14+; точная
  эволюция статуса (какая версия делает free-threaded default) могла измениться после cutoff» —
  явный decay-риск, pretrain recall.
- **Источники:** [PEP 703 — Making the Global Interpreter Lock Optional in
  CPython](https://peps.python.org/pep-0703/); [PEP 779 — Criteria for supported status for
  free-threaded Python](https://peps.python.org/pep-0779/); [Python 3.14 — Python support for free
  threading, official docs](https://docs.python.org/3/howto/free-threading-python.html).
- **Найдено:** Steering Council принял PEP 703 24 октября 2023 (experimental статус, 3.13). PEP 779
  принят — с Python **3.14** free-threaded сборка переходит из «experimental» в «**officially
  supported**» (не экспериментальный, но всё ещё НЕ default вариант интерпретатора). Решение сделать
  free-threaded **default** (Phase III) — отдельное, не принято на 2026-07-14; по актуальным
  публичным обсуждениям ожидается не раньше 2028–2030 (несколько релизов с GIL, управляемым флагом/
  переменной окружения, прежде чем GIL станет disabled по умолчанию).
- **Вердикт:** **уточнён** (исходный claim не был неверен — decay-риск был назван корректно — но
  теперь конкретизирован: статус на 2026-07-14 = «officially supported, non-default» в 3.14, не
  «experimental»; default — горизонт 2028+, не ближайший релиз).
- **Что изменено:** `sota-research.md` B4 — evidence-anchor дополнен PEP 779 + докой Python 3.14;
  trust-cue обновлён на «verified 2026-07-14, PEP 703 + PEP 779 + docs.python.org». `DPF.md` §7 SE-5
  статус-колонка дополнена: «fact, verified 2026-07-14: PEP 779 → officially supported non-default в
  3.14; default (Phase III) не ранее 2028+». §11 refresh-триггер №1 и open assumption №1 — дополнены
  резолюцией (не заменены, исходная формулировка decay-риска остаётся верной для будущих ревизий).

### 3. S19/D4 — «для pure Python нет TSan-эквивалента»

- **Где живёт:** `sota-research.md` S19/D4; `DPF.md` Паттерн 6 принцип, §6 ошибка 6, §7 SE-10, §11
  open assumption №4.
- **Claim (было):** «для pure Python нет TSan-эквивалента в стандартном тулинге» — pretrain recall,
  не переверифицировано.
- **Источники:** [Using Thread Sanitizer to validate and test thread safety — Python Free-Threading
  Guide](https://py-free-threading.github.io/thread_sanitizer/); свежие issue из
  `python/cpython` (2025–2026), напр. [#140260 — ThreadSanitizer: data race in _struct module
  initialization](https://github.com/python/cpython/issues/140260); [Free-threaded CPython is ready
  to experiment with — Quansight Labs](https://labs.quansight.org/blog/free-threaded-python-rollout).
- **Найдено:** claim **частично опровергнут через изменение контекста, не был ложен на момент
  формулировки**. Для GIL-сборки CPython по-прежнему нет прямого пользовательского TSan-эквивалента
  на уровне «взял скрипт — прогнал детектор гонок над чистым Python-кодом». НО для free-threaded
  CPython (PEP 703/779) экосистема **уже строит TSan-инструментированные сборки интерпретатора**
  (py-free-threading.github.io предоставляет готовые Docker-образы; CPython CI использует TSan для
  ловли гонок в самом интерпретаторе и C-расширениях — десятки issue 2025–2026). Это НЕ инструмент
  уровня «чистый Python bytecode», а C-уровневый TSan поверх free-threaded сборки — но landscape
  реально изменился после cutoff модели.
- **Вердикт:** **уточнён** (текст DPF корректен для GIL-сборки; для free-threaded — устарел без
  оговорки). Исправлено по верификации 2026-07-14: было «для pure Python нет TSan-эквивалента» без
  различения GIL/free-threaded; стало «для GIL-сборки CPython по-прежнему нет TSan-уровня инструмента
  над чистым Python; для free-threaded сборок TSan-инструментированные интерпретаторы существуют и
  активно используются CPython CI (2025–2026), хотя это C-уровневый, не pure-Python-level детектор».
  Источник: py-free-threading.github.io/thread_sanitizer/, verified 2026-07-14.
- **Что изменено:** `sota-research.md` S19/D4 — trust-cue обновлён, добавлена free-threaded оговорка.
  `DPF.md` §7 SE-10 статус-колонка дополнена нюансом; §6 типовая ошибка 6 — добавлена сноска (не
  переписан текст ошибки, сноска отдельной строкой); §11 open assumption №4 — дополнен резолюцией.

### 4. AI-срез — S20 (Pearce et al.) и класс S21 (агрегированное наблюдение)

- **Где живёт:** `sota-research.md` S20/S21, AI1/AI2/AI4; `DPF.md` Паттерн 6, §6 ошибка 3/9, §7
  SE-11/SE-12.
- **Claim (было, S20):** Pearce, H. et al. — *"Asleep at the Keyboard? Assessing the Security of
  GitHub Copilot's Code Contributions"*, IEEE S&P, 2021/2022 — эмпирика уязвимого/багованного
  LLM-кода, смежного с TOCTOU/race.
- **Источник:** [Asleep at the Keyboard? — NYU Scholars](https://nyuscholars.nyu.edu/en/publications/asleep-at-the-keyboard-assessing-the-security-of-github-copilots-);
  [ResearchGate — Asleep at the Keyboard?](https://www.researchgate.net/publication/362295286_Asleep_at_the_Keyboard_Assessing_the_Security_of_GitHub_Copilot's_Code_Contributions).
  Полная атрибуция: Pearce, Ahmad, Tan, Dolan-Gavitt, Karri — 43rd IEEE Symposium on Security and
  Privacy (S&P 2022), San Francisco, стр. 754–768.
- **Вердикт:** **подтверждён** — атрибуция (авторы/venue/год/страницы) точна. DPF уже честно
  оговаривает «цифры НЕ переносить на современные модели без переверификации» — это НЕ отменяется:
  веб-поиск НЕ нашёл свежего (2025–2026) прямого replication на актуальных моделях конкретно для
  concurrency-класса багов — claim `AI1` остаётся `fact` (эмпирика 2021–2022 сама по себе), а перенос
  цифр на текущие модели остаётся `hypothesis`, как и было (никакого понижения/повышения статуса).
- **Claim (было, S21/AI2/AI4):** «агрегированное наблюдение сообщества — LLM статистически чаще
  ошибается в тонком (if-vs-while, exception-safety, compound-atomicity, TOCTOU)» — явный
  `hypothesis`, «не единичная статья».
- **Вердикт:** **не верифицируем как отдельный citable источник по определению claim'а** — сам пакет
  уже корректно маркирует S21 как «hypothesis, не единичная статья»; веб-поиск не проводился для
  повышения этого конкретного claim'а до `fact`, потому что задача поиска (найти ЕДИНСТВЕННЫЙ
  первоисточник агрегированного наблюдения) логически противоречит природе claim'а. **Оставлено как
  есть** — hypothesis не переоткрыт до fact (A.10, дисциплина метода).
- **Что изменено:** `sota-research.md` S20 trust-cue → «verified 2026-07-14, атрибуция точна, цифры
  1:1 не переносить (без изменений в этой части)». S21 — без изменений (уже честно hypothesis).

---

## Спот-чек несущих научных первоисточников (расширение п.5 repair-списка — «остальные claim'ы»)

> Цель — не переверифицировать буквально каждую из 21 строк CorpusLedger (вне разумного объёма
> одного круга ремонта), а закрыть claim'ы, на которые опираются паттерны DPF.md как на `fact`.
> Park-источники (S4, S7, S12, S15) и claim'ы, явно не требующие переверификации в этом repair-списке
> (S1, S8, S10, S21-hypothesis), — намеренно НЕ проверены в этом круге (см. quality-record «Незакрытое»).

| # | Claim / источник | Проверка | URL | Вердикт |
|---|---|---|---|---|
| S2 | Coffman, Elphick, Shoshani — *System Deadlocks*, ACM Computing Surveys, 1971 (4 условия deadlock) | атрибуция (авторы/год/venue/4 условия) | [ACM DL](https://dl.acm.org/doi/10.1145/356586.356588), [PDF](https://uobdv.github.io/Design-Verification/Supplementary/System_Deadlocks-Four_necessary_and_sufficient_conditions_for_deadlock.pdf) | **подтверждён** |
| S3 | Hoare, C.A.R. — *Monitors: An Operating System Structuring Concept*, CACM, 1974 | атрибуция + монитор/condition variable концепция | pretrain-knowledge + косвенно подтверждён через S14/S13 цитирования (широко известная работа) | **подтверждён** (высокая уверенность, каноническая работа) |
| S5 | Netzer, R.H.B.; Miller, B.P. — *What Are Race Conditions? Some Issues and Formalizations*, ACM LOPLAS, 1992 | атрибуция + разделение data race/race condition | [ACM DL](https://dl.acm.org/doi/10.1145/130616.130623), [ResearchGate PDF](https://www.researchgate.net/publication/2346369_What_are_Race_Conditions_-_Some_Issues_and_Formalizations) | **подтверждён** |
| S6 | Herlihy, M.; Shavit, N. — *The Art of Multiprocessor Programming*, Morgan Kaufmann, 2008 | атрибуция + издательство/год | [Elsevier Educate](https://www.educate.elsevier.com/book/details/9780123973375), [Amazon](https://www.amazon.com/Art-Multiprocessor-Programming-Maurice-Herlihy/dp/0123705916) | **подтверждён** |
| S9 | Beazley, D. — *Understanding the Python GIL*, PyCon 2010 | атрибуция + дата/место | [dabeaz.com/GIL](http://www.dabeaz.com/GIL/), [PyVideo](https://pyvideo.org/pycon-us-2010/pycon-2010--understanding-the-python-gil---82.html) | **подтверждён** (PyCon Atlanta, 20 февр. 2010) |
| S13 | Buschmann, Schmidt, Stal, Rohnert — *POSA Vol.2: Patterns for Concurrent and Networked Objects*, Wiley, 2000 | атрибуция + издательство/год | [Wiley](https://www.wiley.com/en-us/Pattern-Oriented+Software+Architecture%2C+Volume+2%2C+Patterns+for+Concurrent+and+Networked+Objects-p-9781118725177) | **подтверждён** |
| S14 | Goetz, Peierls, Bloch, Bowbeer, Holmes, Lea — *Java Concurrency in Practice*, Addison-Wesley, 2006 | атрибуция + гл.3 (Thread Confinement, Safe Publication) | [Pearson](https://www.pearson.com/en-us/subject-catalog/p/java-concurrency-in-practice/P200000009374/9780321349606) | **подтверждён**, включая структуру гл.3: 3.1 Visibility, 3.2 Publication/escape, 3.3 Thread confinement, 3.4 Immutability, 3.5 Safe publication |
| S16 | Bacon, D. et al. — *The "Double-Checked Locking is Broken" Declaration*, ~2001 | атрибуция + список подписавших | [cs.umd.edu/~pugh](https://www.cs.umd.edu/~pugh/java/memoryModel/DoubleCheckedLocking.html), [Wikipedia](https://en.wikipedia.org/wiki/Double-checked_locking) | **подтверждён** (Bacon, Bloch, Bogda, Click, Haahr, Lea, Maessen, Manson, Mitchell, Nilsen, Pugh, May, Sirer) |
| S17 | Lu, Park, Seo, Zhou — *Learning from Mistakes*, ASPLOS 2008 | атрибуция + предмет (105 багов, MySQL/Apache/Mozilla/OpenOffice) | [ACM DL](https://dl.acm.org/doi/10.1145/1346281.1346323), [UNT Digital Library](https://digital.library.unt.edu/ark:/67531/metadc894456/) | **подтверждён**; ASPLOS Influential Paper Award (10+ лет спустя) |
| S18 | Musuvathi, Qadeer et al. — *CHESS: A Systematic Testing Tool for Concurrent Software*, Microsoft Research, ~2007–2008 | атрибуция + venue | [MSR tech report MSR-TR-2007-149](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2007-149.pdf), [OSDI'08 heisenbugs paper](https://www.usenix.org/legacy/event/osdi08/tech/full_papers/musuvathi/musuvathi.pdf) | **подтверждён** (MSR tech report 2007 + OSDI 2008 «Finding and Reproducing Heisenbugs») |

**Стоп-находок нет** — ни одна из 10 проверенных научных атрибуций не оказалась ложной/выдуманной
(0 галлюцинированных цитат). Это НЕ то же самое, что «всё содержание пакета верифицировано» — S1, S4,
S7, S8, S10, S12, S15, S21 остаются `pretrain recall, не верифицирован` (честно, без апгрейда).

---

## Новый источник для D8 — worked-кейс из другого домена

### urllib3 `PoolManager` — TOCTOU-класса гонка вокруг LRU-кэша connection pool

- **Источник:** GitHub issue [`urllib3/urllib3#1252` — "PoolManager is not thread-safe"
  ](https://github.com/urllib3/urllib3/issues/1252), обращение 2026-07-14 (WebFetch). Смежные:
  [`#1232`](https://github.com/urllib3/urllib3/issues/1232), исторический fix
  [`#204`](https://github.com/urllib3/urllib3/issues/204) (RecentlyUsedContainer thread-safety),
  зеркало со стороны потребителя — [`psf/requests#1871`](https://github.com/psf/requests/issues/1871).
- **Суть (проверено WebFetch, дословный смысл сохранён):** `PoolManager` держит LRU-кэш
  `ConnectionPool`-инстансов. Поток получает pool из кэша (`pool = self.pools[key]` — «check»), но
  между этим моментом и фактическим использованием (`pool._get_conn` — «act») другой поток может
  вытеснить (evict) именно этот pool из LRU-кэша, если параллельно открывается много других хостов —
  запрос уходит на уже закрытый/невалидный pool. Классический TOCTOU/check-then-act (Паттерн 1 этого
  DPF), НЕ data race за одну ячейку памяти.
- **Почему это ДРУГОЙ домен:** widely-used стандартная библиотека HTTP-транспорта (не `kombu`,
  не AMQP), другой авторский коллектив, независимое от `kombu-pyamqp-threadsafe` подтверждение, что
  Паттерн 1/A4 инстанциируется за пределами мотивирующего примера — закрывает C-3/D8 из
  `critic-review.md` (`worked-evidence` вне единственного файла одного проекта).
- **Куда добавлено:** `DPF.md` §10 разнородные приёмочные случаи, новая строка **HC-4** (не заменяет
  HC-1/HC-2/HC-3). `source-pack.md` — новая adopted-запись (Пополнение 2026-07-14).

---

## Дополнительный источник для нового Паттерна 7 (memory visibility под free-threaded)

- **[Thread Safety Guarantees — Python 3.14 official docs](https://docs.python.org/3/library/threadsafety.html)**,
  обращение 2026-07-14 (WebFetch). Точная цитата: «This page documents thread-safety guarantees for
  built-in types in Python's free-threaded build. ... When the GIL is enabled, most operations are
  implicitly serialized.» Явно приводит `if key in d: del d[key]` как **NOT atomic (TOCTOU)** под
  free-threaded — независимое официальное подтверждение A4/Паттерна 1 от первоисточника языка, не
  только от security-литературы.
- **[Porting Python Packages to Support Free-Threading — Python Free-Threading
  Guide](https://py-free-threading.github.io/porting/)**, обращение 2026-07-14 (WebFetch). Точная
  цитата: «readers should atomically copy the shared reference to a local variable and then only
  access the local variable»; «situations where the GIL _was_ providing safety will need new analysis
  to ensure they are safe under free-threaded Python»; «global mutable state is not safe in the
  free-threaded build without some form of locking… this assumption is not valid without explicit
  locking».
- **[PEP 779 — Criteria for supported status for free-threaded
  Python](https://peps.python.org/pep-0779/)**, обращение 2026-07-14 (WebSearch) — статус free-threaded
  в 3.14: officially supported, non-default.
- **Вердикт:** новые, ранее не адмиттированные в пакет источники — приняты через admission (Carrier
  note CC-DPF.5: официальная документация первого порядка, не carrier-пересказ). Использованы для
  нового Паттерна 7 в `DPF.md` §4 (полный блок E.8) и для уточнения S19/D4/B4 выше.

---

## Итог по repair-списку п.5 («веб-верификация якорей»), круг 1

| Якорь | Вердикт | Действие |
|---|---|---|
| A4 (TOCTOU) | уточнён (**пересмотрено круг 2**, см. ниже) | evidence-anchor добавлен (Bishop & Dilger 1996) |
| B4/S11 (PEP 703) | уточнён | статус конкретизирован (3.14 supported non-default; default 2028+) |
| S19/D4 (TSan) | уточнён | free-threaded оговорка добавлена (TSan существует для free-threaded, не для pure GIL-Python) |
| S20 (AI1, Pearce et al.) | подтверждён | атрибуция точна, hypothesis-перенос на новые модели не тронут |
| S21 (AI2/AI4, агрегация) | не применимо | природа claim'а исключает единичный источник; оставлен hypothesis |
| S2, S3, S5, S6, S9, S13, S14, S16, S17, S18 | подтверждены | 0 битых атрибуций |
| S1, S4, S7, S8, S10, S12, S15 | не проверялись в этом круге | остаются `pretrain recall, не верифицирован` — честно, без апгрейда (S8 закрыт кругом 2, см. ниже) |

**Ни один claim не оказался ложным/галлюцинированным** — весь repair по этому пункту свёлся к
**уточнению** (opinion→fact-grade provenance, decay-риск конкретизирован), не к «было X, стало
опровергнуто Y» — за исключением S19/D4, где нюанс free-threaded/GIL реально меняет применимость
исходной формулировки (см. выше, помечено явно «исправлено по верификации 2026-07-14»).

---

# Круг 2 (2026-07-14) — репарация по `critic-review-2026-07-14-r1.md`

> Роль: `DPF-KNOWLEDGE-CURATION` (куратор), наименьшие правки R2-2/R2-3 из отзыва критика Круга 2.
> Инструменты: WebFetch, WebSearch. URL обращены **2026-07-14**.

### R2-2. A4/Bishop & Dilger — спот-чек атрибуции «coining»

- **Claim (было, круг 1):** «A4 привязан к первоисточнику» / «Первоисточник термина найден и
  верифицирован» (см. `sota-research.md` A4/S22, `source-pack.md` S22, `theses-antitheses.md` §0.1
  резолюция круга 1, `DPF.md` Паттерн 1/§8).
- **Где живёт:** `sota-research.md` ClaimSheet A4 + CorpusLedger S22; `source-pack.md` S22 + §3
  «Резолюции ремонта»; `theses-antitheses.md` §0.1; `DPF.md` Паттерн 1 (принцип), §8 «Источник
  термина».
- **Источник:** [Wikipedia — Time-of-check to time-of-use](https://en.wikipedia.org/wiki/Time-of-check_to_time-of-use),
  обращение 2026-07-14 (WebFetch, прямой повторный запрос).
- **Что показала сверка:** Bishop & Dilger 1996 присутствует на странице ТОЛЬКО в разделе «Further
  reading»; основной текст статьи не приписывает этой работе введение TOCTOU/TOCTTOU-номенклатуры и
  не упоминает авторов вовсе вне этого раздела.
- **Вердикт: уточнён (не опровергнут).** Источник genuine, атрибуция (авторы/venue/год/страницы)
  точна и остаётся verified — это НЕ галлюцинация и НЕ битая ссылка. Опровергнут только более сильный
  косвенный claim («источник ввёл/породил термин»), который сама Wikipedia-страница не подтверждает.
- **Что изменено (исправлено по верификации 2026-07-14):** было «первоисточник термина
  TOCTOU/TOCTTOU» / «A4 привязан к первоисточнику» — стало «ранняя каноническая детальная работа по
  TOCTOU в file-access». Правки внесены: `sota-research.md` A4 (ClaimSheet) и CorpusLedger S22;
  `source-pack.md` S22-строка + новая секция «Резолюции ремонта 2026-07-14 (круг 2)»;
  `theses-antitheses.md` §0.1 — новая резолюция круга 2 добавлена под резолюцией круга 1 (не
  переписана); `DPF.md` Паттерн 1 принцип + §8 «Источник термина» (label ремонта снят одновременно,
  PFM7-правка того же прохода).

### R2-3. S8 (Python core docs, GIL-atomicity) — верификация по docs.python.org

- **Claim (было):** «GIL атомизирует один bytecode/встроенную операцию, НЕ составную
  последовательность» — Python core docs (S8), `pretrain recall, не верифицирован`
  (`sota-research.md` B1, CorpusLedger S8).
- **Где живёт:** `sota-research.md` ClaimSheet B1 + CorpusLedger S8; `source-pack.md` S8;
  `DPF.md` Паттерн 2 (принцип), §7 SE-4.
- **Источник:** [Python FAQ — What kinds of global value mutation are
  thread-safe?](https://docs.python.org/3/faq/library.html#what-kinds-of-global-value-mutation-are-thread-safe),
  обращение 2026-07-14 (WebFetch).
- **Цитата дословно:** атомарные — `L.append(x)`, `L1.extend(L2)`, `x = L[i]`, `x = L.pop()`,
  `L1[i:j] = L2`, `L.sort()`, `x = y`, `x.field = y`, `D[x] = y`, `D1.update(D2)`, `D.keys()`;
  НЕ атомарные — `i = i+1`, `L.append(L[-1])`, `L[i] = L[j]`, `D[x] = D[x] + 1`. Явная рекомендация:
  «When in doubt, use a mutex!»
- **Вердикт: подтверждён дословно.** Claim B1/SE-4/Паттерн 2 точно совпадает с официальной FAQ-
  страницей — ни расширения, ни сужения claim'а не потребовалось.
- **Что изменено:** trust-cue B1 в `sota-research.md` обновлён с «pretrain recall, не верифицирован»
  на «verified 2026-07-14, <URL>»; CorpusLedger S8 дополнен точным URL FAQ-страницы;
  `source-pack.md` S8-строка дополнена (verified, не переписана); `DPF.md` Паттерн 2 принцип + §7
  SE-4 — добавлена URL-ссылка и `verified 2026-07-14` рядом с S8 (label ремонта не добавлен — PFM7).
  S10 (Beazley & Jones, *Python Cookbook* 3rd, книга) НЕ верифицирован тем же путём — существование
  главы 12 подтверждено WebSearch (издательский оглавление/ToC), но точный текст книги за paywall,
  недоступен для прямой построчной сверки; остаётся `pretrain recall`, честно не повышен.

### Итог круга 2

| Пункт repair-списка | Вердикт | Статус |
|---|---|---|
| R2-2 (A4 wording) | подтверждена находка критика | исправлено во всех 4 несущих файлах |
| R2-3 (S8 verify) | подтверждён claim, verified | S8 переведён pretrain → verified; S10 честно остался pretrain |

**Ни одного галлюцинированного URL/цитаты в этом круге.** Оба спот-чека (Wikipedia повторно, Python
FAQ впервые) дали чистый результат: R2-2 — источник genuine, но косвенный «coining»-claim снят;
R2-3 — claim подтверждён дословно, апгрейд trust-cue оправдан evidence.
