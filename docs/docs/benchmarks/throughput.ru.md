# Throughput Benchmarks

Измерение пропускной способности публикации сообщений под различной нагрузкой.

## Метрики

| Метрика | Описание | Единица |
|---------|----------|---------|
| `messages_per_second` | Количество успешно опубликованных сообщений в секунду | msg/s |
| `latency_p50` | Медианное время публикации одного сообщения | ms |
| `latency_p95` | 95-й перцентиль задержки | ms |
| `latency_p99` | 99-й перцентиль задержки (хвост распределения) | ms |
| `errors` | Количество ошибок публикации | count |

## Тесты

### test_publish_throughput

Базовый тест пропускной способности. Каждый поток публикует `msg_per_thread` сообщений.

```python
@pytest.mark.parametrize("n_threads,msg_per_thread", [
    (10, 100),   # Quick smoke test: 1K messages
    (100, 100),  # Base case: 10K messages
])
def test_publish_throughput(...)
```

**Методология:**

1. Создается `n_threads` потоков
2. Каждый поток получает канал из пула
3. Все потоки синхронизируются через `Barrier`
4. Одновременный старт публикации
5. Измерение времени каждой публикации

**Ключевые аспекты:**

- Размер сообщения: 100 байт
- Сообщения публикуются без подтверждения (fire-and-forget)
- Канал возвращается в пул после завершения

---

### test_publish_throughput_stress

Стресс-тест с большим количеством потоков.

```python
@pytest.mark.parametrize("n_threads,msg_per_thread", [
    (300, 50),   # Medium: 15K messages
    (900, 10),   # Stress: 9K messages
])
def test_publish_throughput_stress(...)
```

!!! warning "Target"
    При 900 потоках throughput должен оставаться > 1000 msg/s

**Особенности:**

- Использует `Event` вместо `Barrier` для синхронизации (Barrier не поддерживает > 500 участников)
- Больший размер пула каналов
- Мягкая проверка (warning, не fail)

---

### test_channel_acquire_release_throughput

Тестирует накладные расходы на операции с пулом каналов.

```python
@pytest.mark.parametrize("n_threads,n_iterations", [
    (100, 100),   # Base case
    (500, 50),    # Higher contention
])
def test_channel_acquire_release_throughput(...)
```

**Что измеряет:**

- Скорость `acquire()` / `release()` без реальных AMQP операций
- Накладные расходы на синхронизацию потоков
- Эффективность внутренних блокировок

## Результаты

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Throughput by thread count",
  "width": 500,
  "height": 300,
  "data": {
    "values": [
      {"threads": 10, "throughput": 14986, "latency_p99": 3.27},
      {"threads": 100, "throughput": 19157, "latency_p99": 12.88},
      {"threads": 300, "throughput": 10653, "latency_p99": 739.37},
      {"threads": 900, "throughput": 988, "latency_p99": 8525.54}
    ]
  },
  "layer": [
    {
      "mark": {"type": "bar", "color": "#7c3aed"},
      "encoding": {
        "x": {"field": "threads", "type": "ordinal", "title": "Thread Count"},
        "y": {"field": "throughput", "type": "quantitative", "title": "Messages/sec"}
      }
    }
  ]
}
```

### Throughput по конфигурациям

| Threads | Messages | Duration | Throughput | P50 | P99 |
|---------|----------|----------|------------|-----|-----|
| 10 | 1,000 | 0.07s | 14,986 msg/s | 0.44ms | 3.27ms |
| 100 | 10,000 | 0.52s | 19,157 msg/s | 3.35ms | 12.88ms |
| 300 | 15,000 | 1.41s | 10,653 msg/s | 3.80ms | 739ms |
| 900 | 9,000 | 9.11s | 988 msg/s | 8.22ms | 8.5s |

### Channel Pool Performance

| Threads | Operations | Throughput | P50 | P99 |
|---------|------------|------------|-----|-----|
| 100 | 10,000 | 325,309 ops/s | 0.00ms | 0.00ms |
| 500 | 25,000 | 260,867 ops/s | 0.00ms | 47.08ms |

## Интерпретация

### Почему throughput падает при 900 потоках?

1. **Lock contention** — все потоки конкурируют за один `_transport_lock`
2. **Context switching** — ОС тратит время на переключение между потоками
3. **TCP buffer saturation** — TCP буферы заполняются быстрее, чем данные отправляются
4. **RabbitMQ backpressure** — брокер не успевает принимать сообщения

### Рекомендации

!!! tip "Оптимальное количество потоков"
    Для максимального throughput используйте 50-200 потоков.
    При необходимости масштабирования — увеличивайте число процессов,
    а не потоков в одном процессе.

## Воспроизведение

```bash
# Только throughput тесты
pytest tests/benchmarks/bench_throughput.py -v

# Конкретный тест
pytest tests/benchmarks/bench_throughput.py::TestThroughput::test_publish_throughput -v
```
