# kombu-pyamqp-threadsafe Benchmarks

Комплексный набор бенчмарков для оценки производительности и надежности библиотеки `kombu-pyamqp-threadsafe`.

## Что это?

`kombu-pyamqp-threadsafe` — потокобезопасная реализация транспорта pyamqp для kombu. Эта документация содержит:

- **Методологию бенчмаркинга** — как и что мы измеряем
- **Результаты тестов** — актуальные показатели производительности
- **Руководство по воспроизведению** — как запустить бенчмарки самостоятельно

## Ключевые метрики

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Key metrics overview",
  "width": 400,
  "height": 200,
  "data": {
    "values": [
      {"metric": "Peak Throughput", "value": 22547, "unit": "msg/s"},
      {"metric": "TCP RST Recovery", "value": 0.48, "unit": "ms"},
      {"metric": "Network Partition Recovery", "value": 9.55, "unit": "ms"},
      {"metric": "Max Concurrent Consumers", "value": 900, "unit": "threads"}
    ]
  },
  "mark": "bar",
  "encoding": {
    "x": {"field": "metric", "type": "nominal", "title": null, "axis": {"labelAngle": -45}},
    "y": {"field": "value", "type": "quantitative", "title": "Value"},
    "color": {"field": "metric", "type": "nominal", "legend": null}
  }
}
```

## Категории бенчмарков

| Категория | Описание | Ключевая метрика |
|-----------|----------|------------------|
| [Throughput](benchmarks/throughput.md) | Пропускная способность публикации сообщений | msg/s |
| [Scalability](benchmarks/scalability.md) | Масштабируемость с ростом числа консьюмеров | consumers → throughput |
| [Recovery](benchmarks/recovery.md) | Время восстановления после сбоев | ms to recovery |
| [Stability](benchmarks/stability.md) | Отсутствие дедлоков и потерь данных | 0 errors |

## Быстрый старт

```bash
# Запуск RabbitMQ и Toxiproxy
docker compose -f docker-compose.test.yml up -d

# Запуск бенчмарков
python scripts/run_benchmarks.py

# Генерация отчета
python scripts/run_benchmarks.py --report
```

## Архитектура тестов

```
tests/benchmarks/
├── conftest.py              # Фикстуры pytest
├── bench_throughput.py      # Тесты пропускной способности
├── bench_realistic.py       # Реалистичные сценарии
├── bench_recovery_latency.py # Тесты восстановления
├── bench_race_conditions.py # Chaos-тестирование
└── bench_comprehensive.py   # Комплексные тесты
```

## Инструменты

- **pytest** — фреймворк тестирования
- **Toxiproxy** — симуляция сетевых сбоев
- **RabbitMQ** — AMQP брокер
- **matplotlib** — визуализация результатов
