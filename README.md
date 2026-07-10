# HDFS Log Anomaly Detection

Исследовательский ML-проект и web-приложение для поиска аномалий в HDFS-логах. Проект
охватывает EDA, Drain3-парсинг, табличные baseline-модели, LSTM, FastAPI inference service и
Streamlit-интерфейс.

## Демо

Публичный frontend на production-сервере открывается через домен, настроенный в Caddy:

```text
https://<demo-domain>
```

```text
email: demo@example.com
password: demopwd123456!
```

## Возможности

- подготовка и исследование HDFS_v1;
- преобразование raw logs в event templates через Drain3;
- обучение и оценка Logistic Regression, Isolation Forest и Random Forest;
- one-step и many-to-many LSTM для предсказания следующих событий;
- сравнение top-k и NLL anomaly scoring;
- inference по raw HDFS log lines;
- регистрация, JWT-аутентификация и управление профилем;
- личная и общая история запросов со статистикой;
- административное управление ролями и статусами;
- воспроизводимые эксперименты через YAML-конфиги;
- локальный Docker Compose и production-деплой через Ansible.

Основной стек: Python 3.12-3.14, PyTorch, scikit-learn, Drain3, FastAPI, Streamlit,
SQLAlchemy 2 async, PostgreSQL, Alembic, Docker Compose и uv.

## Исследовательская постановка

Логи группируются по `block_id` и преобразуются в последовательности `EventId`. Табличные
baseline-модели используют признаки целого блока. LSTM работают со sliding windows и ближе к
сценарию, где события поступают последовательно.

```text
raw HDFS logs
    → Drain3 event templates
    → event sequences per block_id
    → sliding windows
    → next-event prediction
    → block anomaly score
    → validation threshold
```

Для top-k scoring ошибкой считается переход, в котором истинный `EventId` не входит в top-k
предсказаний. Для NLL scoring используется `-log P(true_event)`. Проверены стратегии
`topk_last`, `topk_all`, `topk_last3`, `nll_mean`, `nll_p95` и `nll_max`.

## Результаты

Лучший sequence-based подход — many-to-many LSTM с `nll_max`: аномалию лучше определяет самый
неожиданный переход внутри последовательности, а не средняя ошибка по всему блоку.

| Подход | Модель / scoring | F1 | Precision | Recall | FPR | AP |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | full-block tabular | 0.991 | 0.984 | 0.999 | 0.0005 | 0.993 |
| Isolation Forest | full-block tabular | 0.328 | 0.247 | 0.486 | 0.0446 | 0.155 |
| Random Forest | full-block tabular | 0.999 | 0.999 | 0.999 | 0.0000 | 1.000 |
| One-step LSTM | top-k miss | 0.706 | 0.746 | 0.670 | 0.0305 | 0.671 |
| Many-to-many LSTM | baseline + `nll_max` | 0.887 | 0.963 | 0.823 | 0.0043 | 0.951 |
| Many-to-many LSTM | best architecture + `nll_max` | 0.911 | 0.966 | 0.863 | 0.0041 | 0.975 |

Табличные supervised-модели показывают верхнюю границу качества, но видят весь блок сразу.
Many-to-many LSTM сохраняет production-like последовательную постановку и заметно снижает FPR
относительно one-step baseline.

Подробнее: [reports/README.md](reports/README.md).

## Архитектура приложения

FastAPI разделён на HTTP-слой, сервисы, репозитории, SQLAlchemy-модели и inference-компоненты.
Streamlit работает как отдельный API-клиент. Оба приложения используют разные
Docker images:

```text
browser
   │
   ▼
Streamlit frontend ── HTTP/JWT ──▶ FastAPI ── SQLAlchemy ──▶ PostgreSQL
                                        │
                                        └──▶ Drain3 + LSTM artifacts
```

В локальном и production Compose API и PostgreSQL находятся во внутренней сети. Публичным
сервисом остаётся только frontend. API и frontend собираются в разные Docker images; модели и
runtime-файлы в images не включаются.

## Данные

Используется `HDFS_v1` из [LogPai LogHub](https://github.com/logpai/loghub). Данные не входят в
репозиторий; ожидаемая структура описана в [data/README.md](data/README.md).

| Характеристика | Значение |
|---|---:|
| Raw log lines | 11,175,629 |
| Block-level samples | 575,061 |
| Normal blocks | 558,223 |
| Anomaly blocks | 16,838 |
| Anomaly ratio | 2.93% |
| Event templates | 29 |
| Median sequence length | 19 |
| Max sequence length | 298 |

## Локальный запуск

Checkpoint, Drain transformer и threshold из [configs/api.yaml](configs/api.yaml) должны
присутствовать в `artifacts/` и `reports/`.

```bash
cp .env.example .env
```

Замените placeholder-значения. Пароль в `DATABASE_URL` должен соответствовать
`POSTGRES_PASSWORD`. Если он содержит зарезервированные URI-символы, его часть внутри URL
необходимо percent-encode; значение `POSTGRES_PASSWORD` остаётся исходным.

Bootstrap admin и demo users управляются группами переменных `BOOTSTRAP_ADMIN_*`, `DEMO_*`.
В production значения задаются через Ansible Vault или GitHub Secrets.

Первый запуск:

```bash
docker compose up --build -d postgres
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m hdfs_anomaly.app.scripts.seed_data
docker compose up -d api frontend
```

При следующих запусках, если миграции и seed не изменялись:

```bash
docker compose up --build -d
```

Streamlit доступен по адресу `http://127.0.0.1:8501`. PostgreSQL публикуется на 
порту `POSTGRES_PORT` и хранит данные в volume `hdfs_anomaly_data`. 
API не публикуется на хост и доступен контейнерам Compose-сети по адресу `http://api:8000`.

Остановка:

```bash
docker compose down
```

Примеры normal/anomaly logs для Streamlit находятся в `examples/`.

## API

Без JWT доступны `/health`, регистрация и login. Остальные маршруты требуют
`Authorization: Bearer <token>`. Новый профиль получает статус `INACTIVE`; 
активировать его может admin.

| Method | Route | Назначение |
|---|---|---|
| `GET` | `/health` | Состояние сервиса и модели |
| `POST` | `/api/v1/registration` | Регистрация |
| `POST` | `/api/v1/auth/login` | Получение JWT |
| `GET/DELETE` | `/api/v1/profile` | Просмотр или удаление своего профиля |
| `PATCH` | `/api/v1/profile/email` | Смена email |
| `PATCH` | `/api/v1/profile/password` | Смена пароля |
| `GET` | `/api/v1/model/info` | Метаданные модели; admin |
| `POST` | `/api/v1/model/predict` | Inference по raw logs |
| `GET/DELETE` | `/api/v1/history` | Личная история |
| `GET` | `/api/v1/history/stats` | Личная статистика |
| `GET/DELETE` | `/api/v1/history/all` | Общая история; admin |
| `GET` | `/api/v1/history/stats/all` | Общая статистика; admin |
| `GET` | `/api/v1/admin/profiles` | Поиск профилей; admin |
| `PATCH` | `/api/v1/admin/profiles/{id}/status` | Изменение статуса; admin |
| `PATCH` | `/api/v1/admin/profiles/{id}/role` | Изменение роли; admin |

Health endpoint и Swagger UI внутри Compose-сети:

```text
http://api:8000/health
http://api:8000/docs
```

## Эксперименты

```bash
# Табличные baseline
uv run python scripts/train_tabular_baseline.py --config configs/tabular_baselines.yaml
uv run python scripts/evaluate_tabular_baselines.py --config configs/tabular_baselines.yaml

# Подготовка LSTM-датасетов
uv run python scripts/prepare_lstm_data.py --config configs/lstm_one_step_data.yaml
uv run python scripts/prepare_lstm_data.py --config configs/lstm_many_to_many_data.yaml

# One-step LSTM
uv run python scripts/train_lstm_one_step.py --config configs/lstm_one_step.yaml
uv run python scripts/evaluate_lstm_one_step.py --config configs/lstm_one_step.yaml

# Many-to-many LSTM
uv run python scripts/train_lstm_many_to_many.py --config configs/lstm_many_to_many.yaml
uv run python scripts/evaluate_lstm_many_to_many.py --config configs/lstm_many_to_many.yaml
```

Остальные варианты архитектур находятся в `configs/`, анализ экспериментов — в `notebooks/`,
сохранённые метрики и графики — в `reports/`.

## Разработка

Установка всех зависимостей:

```bash
uv sync --all-extras --all-groups
```

Основные директории:

```text
src/hdfs_anomaly/app/api/          HTTP endpoints и зависимости
src/hdfs_anomaly/app/models/       SQLAlchemy-модели
src/hdfs_anomaly/app/repositories/ запросы к БД
src/hdfs_anomaly/app/services/     бизнес-логика
src/hdfs_anomaly/app/model/        загрузка модели и inference
src/hdfs_anomaly/frontend/         Streamlit-интерфейс
src/hdfs_anomaly/parsing/          Drain3-парсинг
src/hdfs_anomaly/sequences/        split и windowing
src/hdfs_anomaly/models/           ML/LSTM-модели
alembic/                           миграции
deploy/ansible/                    production-деплой
```

Создание и применение миграции:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic upgrade head
```

Автогенерированные миграции нужно проверять вручную перед применением.

## Тесты и проверки

Статические проверки:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
```

CI выполняет эти проверки для push и pull request.

## Деплой

GitHub Actions при push в `main` собирает API и frontend images, публикует их в 
GHCR и запускает Ansible playbook. Production публикует через общую сеть Caddy 
только Streamlit; API и PostgreSQL остаются во внутренней сети. Runtime-файлы 
синхронизируются из Selectel S3.

Настройка GitHub Variables, Secrets, Vault, ручной запуск и эксплуатационные 
команды описаны в [deploy/ansible/README.md](deploy/ansible/README.md).

## References

- [LogHub / HDFS dataset](https://github.com/logpai/loghub)
- [DeepLog](https://dl.acm.org/doi/10.1145/3133956.3134015)
- [LogBERT](https://arxiv.org/abs/2103.04475)
- [LogGPT](https://arxiv.org/abs/2309.14482)
- [Log-based Anomaly Detection with Deep Learning: How Far Are We?](https://arxiv.org/abs/2202.04301)
