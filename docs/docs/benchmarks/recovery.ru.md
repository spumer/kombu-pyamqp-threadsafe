# Recovery Benchmarks

Измерение скорости обнаружения сбоев и восстановления после них с использованием Toxiproxy.

## Метрики

| Метрика | Описание | Единица |
|---------|----------|---------|
| `error_detection_latency` | Время от инъекции сбоя до первого обнаружения | ms |
| `error_propagation_latency` | Время до обнаружения сбоя всеми потоками | ms |
| `full_recovery_latency` | Время до полного восстановления всех потоков | ms |

## Типы сбоев

### TCP RST (reset_peer)

Симулирует немедленное закрытие соединения со стороны сервера.

```python
toxic_reset_peer(rabbitmq_proxy, timeout_ms=0)
```

**Реальные сценарии:**

- Crash процесса RabbitMQ
- OOM kill
- Hardware failure
- Network device reset

---

### Network Partition (timeout)

Симулирует полный разрыв сетевого соединения.

```python
toxic_timeout(rabbitmq_proxy, timeout_ms=100)
```

**Реальные сценарии:**

- Отключение сетевого кабеля
- Firewall блокировка
- Network partition в distributed системах
- Cloud provider network issues

---

### Degraded Network + Failure

Симулирует медленную сеть, которая затем полностью отказывает.

```python
toxic_latency(rabbitmq_proxy, 200, jitter_ms=100)  # 200ms latency
# ... some time passes ...
toxic_reset_peer(rabbitmq_proxy, timeout_ms=0)      # then failure
```

**Реальные сценарии:**

- Постепенная деградация сети перед отказом
- Overloaded network equipment
- DDoS перед crash

## Тесты

### test_recovery_after_reset_peer

Измеряет время восстановления после TCP RST.

```python
@pytest.mark.parametrize("n_threads", [10, 50])
def test_recovery_after_reset_peer(...)
```

**Методология:**

1. Все потоки выполняют `drain_events()` в цикле
2. Инъекция TCP RST через Toxiproxy
3. Измерение времени обнаружения ошибки каждым потоком
4. Удаление toxic
5. Попытка восстановления (`ensure_connection()`)
6. Измерение времени успешного восстановления

---

### test_recovery_after_network_partition

Измеряет время восстановления после network partition.

```python
@pytest.mark.parametrize("n_threads", [10, 50])
def test_recovery_after_network_partition(...)
```

**Отличие от TCP RST:**

- TCP RST — немедленное уведомление
- Network partition — обнаружение через timeout

---

### test_recovery_with_latency_before_failure

Тестирует восстановление когда сеть была медленной перед сбоем.

```python
def test_recovery_with_latency_before_failure(...)
```

## Результаты

### Recovery Time Comparison

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Recovery time by failure type",
  "width": 500,
  "height": 300,
  "data": {
    "values": [
      {"type": "TCP RST", "metric": "Detection", "time": 0.48},
      {"type": "TCP RST", "metric": "Propagation", "time": 513.47},
      {"type": "TCP RST", "metric": "Full Recovery", "time": 515.63},
      {"type": "Network Partition", "metric": "Detection", "time": 105.31},
      {"type": "Network Partition", "metric": "Propagation", "time": 105.83},
      {"type": "Network Partition", "metric": "Full Recovery", "time": 1530.35},
      {"type": "Degraded + RST", "metric": "Full Recovery", "time": 517.09}
    ]
  },
  "mark": "bar",
  "encoding": {
    "x": {"field": "type", "type": "nominal", "title": "Failure Type"},
    "y": {"field": "time", "type": "quantitative", "title": "Time (ms)"},
    "color": {"field": "metric", "type": "nominal", "title": "Phase"},
    "xOffset": {"field": "metric"}
  }
}
```

### Детальные результаты

#### TCP RST Recovery (50 threads)

| Метрика | Значение |
|---------|----------|
| Error Detection | -0.67 ms* |
| Error Propagation | 513.47 ms |
| Full Recovery | 515.63 ms |
| Threads Detected | 11/50 |
| Threads Recovered | 50/50 |

!!! note "Отрицательное время детекции"
    Отрицательное значение означает, что некоторые потоки обнаружили
    ошибку до формальной фиксации времени инъекции (race condition в измерении).

#### Network Partition Recovery (50 threads)

| Метрика | Значение |
|---------|----------|
| Error Detection | 105.31 ms |
| Error Propagation | 105.83 ms |
| Full Recovery | 1530.35 ms |
| Threads Detected | 50/50 |
| Threads Recovered | 50/50 |

## Анализ

### Почему Network Partition дольше?

```
TCP RST:
  Client ←──[RST]── Server
  └─ Immediate notification

Network Partition:
  Client ──────X──── Server
  └─ Must wait for timeout (default ~100ms in test)
```

### Propagation vs Detection

- **Detection** — первый поток видит ошибку
- **Propagation** — все потоки видят ошибку

Быстрый propagation важен для:

- Coordinated failover
- Circuit breaker activation
- Health check responses

### Target Metrics

| Метрика | Target | Результат |
|---------|--------|-----------|
| TCP RST Detection | < 10ms | ✅ 0.48ms |
| Network Partition Detection | < 200ms | ✅ 105ms |
| Full Recovery | < 5s | ✅ 1.5s |

## Воспроизведение

!!! warning "Требования"
    Для recovery тестов необходим Toxiproxy:
    ```bash
    docker compose -f docker-compose.test.yml up -d
    ```

```bash
# Все recovery тесты
pytest tests/benchmarks/bench_recovery_latency.py -v

# Только TCP RST
pytest tests/benchmarks/bench_recovery_latency.py::TestRecoveryLatency::test_recovery_after_reset_peer -v

# Network resilience summary
pytest tests/benchmarks/bench_comprehensive.py::TestNetworkResilienceBenchmarks -v
```

## Toxiproxy Configuration

Proxy настроен в `docker-compose.test.yml`:

```yaml
toxiproxy:
  image: ghcr.io/shopify/toxiproxy:latest
  ports:
    - "8474:8474"   # Toxiproxy API
    - "25672:25672" # RabbitMQ proxy
```

Создание proxy через API:

```bash
curl -X POST http://localhost:8474/proxies \
  -d '{"name": "rabbitmq", "listen": "0.0.0.0:25672", "upstream": "rabbitmq:5672"}'
```
