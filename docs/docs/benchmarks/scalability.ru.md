# Scalability Benchmarks

Измерение способности системы справляться с большим количеством concurrent consumers.

## Метрики

| Метрика | Описание | Единица |
|---------|----------|---------|
| `produce_throughput` | Скорость публикации сообщений | msg/s |
| `consume_throughput` | Скорость потребления сообщений | msg/s |
| `latency_p50/p99` | End-to-end задержка (от publish до consume) | ms |
| `message_loss_pct` | Процент потерянных сообщений | % |
| `consumer_startup_sec` | Время запуска всех консьюмеров | sec |

## Тесты

### test_massive_consumers_stress

Ключевой тест масштабируемости. Проверяет работу с экстремальным числом concurrent consumers.

```python
@pytest.mark.parametrize("n_consumers,n_messages", [
    (100, 1000),   # Moderate stress
    (500, 2000),   # High stress
    (900, 3000),   # Extreme stress
])
def test_massive_consumers_stress(...)
```

**Методология:**

1. Создается connection с pool размером `n_consumers + 10`
2. Запускается `n_consumers` consumer threads
3. Все consumers синхронизируются через `Barrier`
4. После готовности всех consumers — публикация сообщений
5. Измерение времени потребления каждого сообщения

**Паттерн consumer:**

```python
def consumer(cons_id: int) -> None:
    with pool.acquire() as ch:
        simple_queue = connection.SimpleQueue(queue_name, channel=ch)
        try:
            consumers_ready.wait()  # Синхронизация
            while not stop_consumers.is_set():
                msg = simple_queue.get(timeout=0.5)
                # Process message...
                msg.ack()
        finally:
            simple_queue.close()
```

---

### test_concurrent_produce_consume

Реалистичный сценарий одновременной работы producers и consumers.

```python
@pytest.mark.parametrize("n_producers,n_consumers,n_messages", [
    (5, 5, 500),    # Balanced workload
    (10, 3, 300),   # Producer-heavy
])
def test_concurrent_produce_consume(...)
```

**Особенности:**

- Producers и consumers работают одновременно
- Симуляция обработки сообщения (`time.sleep(5-20ms)`)
- Отслеживание уникальности сообщений (дедупликация)

---

### test_burst_traffic

Тестирование обработки burst-нагрузки (всплесков трафика).

```python
# Traffic pattern: (messages, delay_ms)
traffic = [
    (50, 20),    # Normal: ~50/s
    (200, 2),    # Spike: ~500/s
    (50, 20),    # Normal
    (300, 0),    # Heavy spike: instant
    (50, 20),    # Normal
]
```

**Что проверяет:**

- Способность справляться с резкими всплесками нагрузки
- Восстановление после пиков
- Queue buffering под нагрузкой

## Результаты

### Scalability по количеству consumers

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Consumer scalability",
  "width": 500,
  "height": 300,
  "data": {
    "values": [
      {"consumers": 100, "throughput": 2142, "latency_p50": 4.84, "latency_p99": 13.05},
      {"consumers": 500, "throughput": 906, "latency_p50": 19.93, "latency_p99": 315.09},
      {"consumers": 900, "throughput": 341, "latency_p50": 36.36, "latency_p99": 326.45}
    ]
  },
  "layer": [
    {
      "mark": {"type": "line", "color": "#7c3aed", "point": true},
      "encoding": {
        "x": {"field": "consumers", "type": "ordinal", "title": "Consumer Count"},
        "y": {"field": "throughput", "type": "quantitative", "title": "Throughput (msg/s)"}
      }
    }
  ]
}
```

### Таблица результатов

| Consumers | Messages | Throughput | Startup | P50 | P99 | Loss |
|-----------|----------|------------|---------|-----|-----|------|
| 100 | 1,000 | 2,142 msg/s | 0.08s | 4.84ms | 13.05ms | 0% |
| 500 | 2,000 | 906 msg/s | 0.36s | 19.93ms | 315ms | 0% |
| 900 | 3,000 | 341 msg/s | 0.73s | 36.36ms | 326ms | 0% |

### Latency Distribution

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Latency by consumer count",
  "width": 500,
  "height": 300,
  "data": {
    "values": [
      {"consumers": "100", "percentile": "P50", "latency": 4.84},
      {"consumers": "100", "percentile": "P99", "latency": 13.05},
      {"consumers": "500", "percentile": "P50", "latency": 19.93},
      {"consumers": "500", "percentile": "P99", "latency": 315.09},
      {"consumers": "900", "percentile": "P50", "latency": 36.36},
      {"consumers": "900", "percentile": "P99", "latency": 326.45}
    ]
  },
  "mark": "bar",
  "encoding": {
    "x": {"field": "consumers", "type": "nominal", "title": "Consumers"},
    "y": {"field": "latency", "type": "quantitative", "title": "Latency (ms)"},
    "color": {"field": "percentile", "type": "nominal"},
    "xOffset": {"field": "percentile"}
  }
}
```

## Анализ

### Линейность масштабирования

$$
\text{Scaling Efficiency} = \frac{\text{Throughput}_{900} / \text{Throughput}_{100}}{900 / 100}
$$

$$
\text{Efficiency} = \frac{341 / 2142}{9} = \frac{0.159}{9} = 0.018 = 1.8\%
$$

!!! info "Sublinear scaling"
    Эффективность 1.8% указывает на существенную деградацию при масштабировании.
    Это ожидаемо для shared-nothing архитектуры с одним connection.

### Bottlenecks

1. **Single Connection** — все consumers используют один TCP connection
2. **Transport Lock** — все операции сериализуются через `_transport_lock`
3. **SimpleQueue Overhead** — каждый consumer поддерживает свою очередь

### Рекомендации

!!! tip "Масштабирование в production"
    - Для > 100 consumers используйте несколько connections
    - Каждый connection — отдельный pool с 50-100 consumers
    - Рассмотрите sharding очередей по consumers

## Воспроизведение

```bash
# Все scalability тесты
pytest tests/benchmarks/bench_realistic.py::TestRealisticWorkloads -v

# Только massive consumers
pytest tests/benchmarks/bench_realistic.py::TestRealisticWorkloads::test_massive_consumers_stress -v

# Конкретная конфигурация
pytest "tests/benchmarks/bench_realistic.py::TestRealisticWorkloads::test_massive_consumers_stress[900-3000]" -v
```
