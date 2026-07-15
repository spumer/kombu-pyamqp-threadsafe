# Карта компетенций проекта kombu-pyamqp-threadsafe

Обновлена: 2026-07-14 (авторинг: dpf-authoring-pipeline; затем режим ремонта с веб-верификацией
источников — два круга «ремонт-критик» на пакет плюс финальная точечная правка формы с переоценкой).

| DPF | Название | Вид | Владелец | CC-DPF.1–9 | Статус пакета (E.4.DPF.DA) |
|---|---|---|---|---|---|
| [DPF-DEDICATED-IO-THREAD](DPF-DEDICATED-IO-THREAD/DPF.md) | Выделенный IO-поток в многопоточном сетевом клиенте | Domain Principle Framework | architect | PASS (9/9) | `admissibleForDeclaredDPFUse` (critic, 2026-07-14, r2) |
| [DPF-CONCURRENT-PROGRAMMING](DPF-CONCURRENT-PROGRAMMING/DPF.md) | Конкурентное программирование: гонки, инварианты, синхронизация | Domain Principle Framework | architect | PASS (9/9) | `admissibleForDeclaredDPFUse` (critic, 2026-07-14, r3) |

Оба пакета — опорные: все 11 координат E.4.DPF.DA на поле 4 или выше, ключевые источники
веб-верифицированы (протоколы — `<DPF-ID>/references/web-verification-2026-07-14.md`), история
оценок — `<DPF-ID>/references/critic-review*.md`.

## Бэклог улучшений (сверх пола, не блокирует опору)

### DPF-DEDICATED-IO-THREAD
1. Phase-1/2 бэкфилл для источников S16–S23 (CorpusLedger и тезисы-антитезисы NQD для паттернов 7–8
   «Bounded Write Backpressure» и «Start-Timing & Lifecycle Ownership») — держит D7/D8/D11 на 4, к 5 не
   пускает.
2. Исполнить приёмочные кейсы как факт (worked-evidence вместо principle-grounded, где помечено).

### DPF-CONCURRENT-PROGRAMMING
1. Разбавить TOCTOU-центричность приёмочных кейсов (D8); пересмотреть HC-3 — сосед
   `DPF-DEDICATED-IO-THREAD` теперь собран и опорный, экстраполяцию можно заменить проверкой.
2. Сверить S10 (Python Cookbook, 3rd ed.) при доступе к книге или понизить роль до corroborating.
3. Остаток источников S1/S4/S7/S10/S12/S15 — pretrain-only (честно размечены trust-cue), верификация
   по возможности.

## Пересмотр
`review_due` обоих пакетов — 2026-09-29; триггеры — в §11 каждого DPF.md (для
DPF-CONCURRENT-PROGRAMMING ключевой — статус free-threaded CPython, PEP 703/779).
