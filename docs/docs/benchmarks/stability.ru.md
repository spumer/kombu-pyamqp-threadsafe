# Stability Benchmarks

Chaos-тестирование для обнаружения race conditions, дедлоков и регрессий.

## Инварианты

Каждый тест проверяет набор инвариантов, которые **никогда** не должны нарушаться:

| Инвариант | Описание | Что означает нарушение |
|-----------|----------|------------------------|
| `deadlocks = 0` | Все потоки завершаются в timeout | Взаимная блокировка потоков |
| `lost_frames = 0` | Все AMQP фреймы доставлены | Потеря данных |
| `double_releases = 0` | Канал освобождается один раз | Pool corruption |
| `keyerror_none = 0` | Нет `KeyError: None` | KeyError регрессия |

## Тесты

### test_chaos_no_deadlock

Базовый chaos test — случайные операции без внешних сбоев.

```python
@pytest.mark.parametrize("n_threads,n_iterations", [
    (10, 100),    # Quick smoke test
    (50, 100),    # Medium load
])
def test_chaos_no_deadlock(...)
```

**Операции:**

```python
OPERATIONS = ['drain', 'connected', 'acquire_release', 'publish']

def random_operation(connection, queue_name):
    op = random.choice(OPERATIONS)

    if op == 'drain':
        connection._connection.drain_events(timeout=0.001)
    elif op == 'connected':
        _ = connection.connected
    elif op == 'acquire_release':
        ch = connection.default_channel_pool.acquire()
        time.sleep(random.uniform(0, 0.001))
        ch.release()
    elif op == 'publish':
        ch = connection.default_channel_pool.acquire()
        producer = kombu.Producer(ch)
        producer.publish(b"test", routing_key=queue_name)
        ch.release()
```

**Проверяет:**

- Thread safety всех основных операций
- Корректность pool management
- Отсутствие deadlocks при concurrent доступе

---

### test_chaos_with_connection_kills

Chaos test с периодическими разрывами соединения.

```python
@pytest.mark.parametrize("n_threads,n_iterations,kill_interval", [
    (20, 50, 10),   # Kill every 10 iterations
    (50, 30, 5),    # More frequent kills
])
def test_chaos_with_connection_kills(...)
```

**Архитектура:**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Worker 1   │     │  Worker 2   │     │  Worker N   │
│ random ops  │     │ random ops  │     │ random ops  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Connection │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Killer    │ ← Периодически разрывает соединение
                    │   Thread    │
                    └─────────────┘
```

**Проверяет:**

- Recovery behavior под нагрузкой
- Корректность состояния после множественных разрывов
- Отсутствие resource leaks

---

### test_high_contention_stress

Стресс-тест с высокой конкуренцией за ресурсы.

```python
@pytest.mark.parametrize("n_threads", [100, 500])
def test_high_contention_stress(...)
```

**Особенности:**

- Все потоки стартуют одновременно (`Barrier`)
- Минимальные задержки между операциями
- Максимальная конкуренция за locks

---

### test_repeated_recovery_stress

1000 итераций kill/recovery цикла.

```python
@pytest.mark.parametrize("n_iterations", [1000])
def test_repeated_recovery_stress(...)
```

**Проверяет:**

- Отсутствие memory leaks после многократных recovery
- Стабильность времени recovery
- Отсутствие накопления ошибок

## Результаты

### Chaos Tests Summary

| Тест | Threads | Duration | Iterations | Deadlocks | Errors |
|------|---------|----------|------------|-----------|--------|
| chaos_no_deadlock | 50 | 0.16s | 5,000 | 0 | 0 |
| chaos_with_kills (n=50) | 50 | 3.07s | 127,449 | 0 | 0 |
| chaos_with_kills (n=20) | 20 | 3.05s | 105,274 | 0 | 0 |
| high_contention | 500 | 0.39s | 5,000 | 0 | 0 |

### Operation Distribution (chaos_no_deadlock)

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Operation distribution in chaos test",
  "width": 400,
  "height": 200,
  "data": {
    "values": [
      {"operation": "drain", "count": 1206},
      {"operation": "connected", "count": 1281},
      {"operation": "acquire_release", "count": 1309},
      {"operation": "publish", "count": 1204}
    ]
  },
  "mark": "arc",
  "encoding": {
    "theta": {"field": "count", "type": "quantitative"},
    "color": {"field": "operation", "type": "nominal"}
  }
}
```

### Repeated Recovery Stats

| Метрика | Значение |
|---------|----------|
| Iterations | 1,000 |
| Recovery P50 | 0.01 ms |
| Recovery P99 | 0.02 ms |
| KeyError: None | 0 |

## KeyError: None Regression Check

!!! danger "Critical Invariant"
    `KeyError: None` — ключевой индикатор регрессии.

    **До фикса:** При race condition в `drain_events()` возникала ситуация,
    когда `channel_id = None` добавлялся в словарь pending events.

    **После фикса:** Selective exception propagation гарантирует корректную
    обработку исключений в `drain_events()`.

```python
# Проверка в каждом тесте
assert checker.keyerror_none == 0, "Regression: KeyError: None"
```

## RaceInvariantChecker

Вспомогательный класс для отслеживания инвариантов:

```python
@dataclass
class RaceInvariantChecker:
    deadlocks: int = 0
    lost_frames: int = 0
    double_releases: int = 0
    keyerror_none: int = 0
    unexpected_exceptions: list = field(default_factory=list)

    def is_healthy(self) -> bool:
        return (
            self.deadlocks == 0 and
            self.lost_frames == 0 and
            self.double_releases == 0 and
            self.keyerror_none == 0 and
            len(self.unexpected_exceptions) == 0
        )

    def check_no_deadlock(self, threads, timeout) -> bool:
        for t in threads:
            t.join(timeout=timeout)
        alive = [t for t in threads if t.is_alive()]
        self.deadlocks = len(alive)
        return self.deadlocks == 0
```

## Воспроизведение

```bash
# Все stability тесты
pytest tests/benchmarks/bench_race_conditions.py -v

# Быстрый smoke test
pytest tests/benchmarks/bench_race_conditions.py::TestRaceConditions::test_chaos_no_deadlock -v

# Стресс-тесты (медленно!)
pytest tests/benchmarks/bench_race_conditions.py -v -m stress
```

## Best Practices

!!! tip "Написание chaos tests"
    1. **Randomize operations** — используйте `random.choice()`
    2. **Track invariants** — проверяйте инварианты после каждой итерации
    3. **Use barriers** — синхронизируйте старт потоков
    4. **Set timeouts** — всегда задавайте timeout для join()
    5. **Check is_alive()** — детектируйте deadlocks через timeout
