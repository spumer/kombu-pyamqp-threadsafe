# Воспроизведение бенчмарков

Пошаговое руководство по запуску бенчмарков и генерации отчетов.

## Требования

### Системные требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| CPU | 4 cores | 8+ cores |
| RAM | 4 GB | 8+ GB |
| Python | 3.10+ | 3.11+ |
| Docker | 20.10+ | Latest |

### Установка зависимостей

```bash
# Клонирование репозитория
git clone https://github.com/spumer/kombu-pyamqp-threadsafe.git
cd kombu-pyamqp-threadsafe

# Установка зависимостей через Poetry
poetry install --with test,dev

# Или через pip
pip install -e ".[test]"
```

## Запуск инфраструктуры

### Docker Compose

```bash
# Запуск RabbitMQ и Toxiproxy
docker compose -f docker-compose.test.yml up -d

# Проверка статуса
docker compose -f docker-compose.test.yml ps
```

**Сервисы:**

| Сервис | Порт | Описание |
|--------|------|----------|
| RabbitMQ | 5672 | AMQP брокер |
| RabbitMQ Management | 15672 | Web UI |
| Toxiproxy | 8474 | API для управления |
| Toxiproxy Proxy | 25672 | Проксированный RabbitMQ |

### Настройка Toxiproxy

Toxiproxy настраивается автоматически через фикстуры pytest, но можно настроить вручную:

```bash
# Создание proxy для RabbitMQ
curl -X POST http://localhost:8474/proxies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rabbitmq",
    "listen": "0.0.0.0:25672",
    "upstream": "rabbitmq:5672"
  }'

# Проверка proxy
curl http://localhost:8474/proxies
```

## Запуск бенчмарков

### Полный запуск

```bash
# Все бенчмарки с генерацией отчета
python scripts/run_benchmarks.py
```

**Что происходит:**

1. Захват environment (Python version, git commit, platform)
2. Очистка старых результатов
3. Запуск pytest с benchmark маркерами
4. Сбор результатов из JSON файлов
5. Генерация Markdown отчета
6. Сохранение в history

### Быстрый запуск

```bash
# Только быстрые тесты (без stress и slow)
python scripts/run_benchmarks.py --quick
```

### Сравнение с предыдущим запуском

```bash
# Сравнение результатов
python scripts/run_benchmarks.py --compare
```

### Только генерация отчета

```bash
# Использовать существующие результаты
python scripts/run_benchmarks.py --report
```

## Запуск отдельных тестов

### По категориям

```bash
# Throughput тесты
pytest tests/benchmarks/bench_throughput.py -v

# Scalability тесты
pytest tests/benchmarks/bench_realistic.py -v

# Recovery тесты (требует Toxiproxy)
pytest tests/benchmarks/bench_recovery_latency.py -v

# Stability тесты
pytest tests/benchmarks/bench_race_conditions.py -v
```

### По маркерам

```bash
# Все benchmark тесты
pytest -m benchmark -v

# Stress тесты (медленные)
pytest -m stress -v

# Исключить медленные
pytest -m "not slow" -v
```

### Конкретный тест

```bash
# Один параметризованный тест
pytest "tests/benchmarks/bench_realistic.py::TestRealisticWorkloads::test_massive_consumers_stress[900-3000]" -v
```

## Структура результатов

```
reports/
├── .test-output/              # Raw JSON results
│   ├── publish_throughput_*.json
│   ├── massive_consumers_*.json
│   └── ...
└── benchmarks/
    ├── LATEST_REPORT.md       # Последний отчет
    ├── benchmark_history.json # История запусков
    ├── run_*.json             # Архивные результаты
    └── junit.xml              # pytest JUnit report
```

## Environment Fingerprint

Каждый запуск получает уникальный fingerprint на основе:

- Git commit hash
- Git dirty status (uncommitted changes)
- Python version
- Platform

```python
def fingerprint(self) -> str:
    key = f"{self.git_commit}:{self.git_dirty}:{self.python_version}:{self.platform}"
    return hashlib.md5(key.encode()).hexdigest()[:8]
```

!!! tip "Воспроизводимость"
    Для точного воспроизведения результатов убедитесь что:

    1. Git commit совпадает
    2. Нет uncommitted changes
    3. Python version совпадает
    4. Docker images актуальны

## Troubleshooting

### RabbitMQ не запускается

```bash
# Проверить логи
docker compose -f docker-compose.test.yml logs rabbitmq

# Перезапустить
docker compose -f docker-compose.test.yml restart rabbitmq
```

### Toxiproxy не доступен

```bash
# Проверить что proxy создан
curl http://localhost:8474/proxies

# Создать вручную если нужно
curl -X POST http://localhost:8474/proxies \
  -d '{"name": "rabbitmq", "listen": "0.0.0.0:25672", "upstream": "rabbitmq:5672"}'
```

### Тесты зависают

!!! warning "Timeout"
    Все тесты имеют timeout. Если тест завис — это баг.

```bash
# Запуск с verbose output для отладки
pytest tests/benchmarks/... -v -s --tb=long
```

### Недостаточно ресурсов

```bash
# Уменьшить нагрузку
pytest -m "not stress" -v

# Или запустить с меньшим параллелизмом
pytest --numprocesses=1 -v
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Benchmarks

on:
  push:
    branches: [master]
  pull_request:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    services:
      rabbitmq:
        image: rabbitmq:3-management
        ports:
          - 5672:5672
      toxiproxy:
        image: ghcr.io/shopify/toxiproxy:latest
        ports:
          - 8474:8474
          - 25672:25672

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[test]"

      - name: Setup Toxiproxy
        run: |
          curl -X POST http://localhost:8474/proxies \
            -d '{"name": "rabbitmq", "listen": "0.0.0.0:25672", "upstream": "localhost:5672"}'

      - name: Run benchmarks
        run: python scripts/run_benchmarks.py --quick

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-report
          path: reports/benchmarks/LATEST_REPORT.md
```

## Генерация документации

### MkDocs

```bash
# Установка зависимостей
pip install mkdocs-material mkdocs-charts-plugin

# Локальный сервер
cd docs && mkdocs serve

# Сборка статики
cd docs && mkdocs build
```

Документация будет доступна на http://localhost:8000
